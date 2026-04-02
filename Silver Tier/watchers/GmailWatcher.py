"""
Gmail Watcher - Polls Gmail for unread + important emails.

For each new email, it creates an action file in /Needs_Action:
    EMAIL_{gmail_message_id}.md

If attachments exist, they are downloaded into:
    /Inbox/Attachments/

Usage:
    python watchers/GmailWatcher.py
    python watchers/GmailWatcher.py --vault AI_Employee_Vault
"""

import sys
import base64
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Add parent dir to path so we can import base_watcher
sys.path.insert(0, str(Path(__file__).parent.parent))
from watchers.base_watcher import BaseWatcher


SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def _sanitize_filename(name: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_", ".", " ") else "_" for ch in name)
    cleaned = cleaned.strip().replace(" ", "_")
    return cleaned or "attachment.bin"


def _yaml_quote(value: str) -> str:
    if value is None:
        return '""'
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").strip() + '"'


class GmailWatcher(BaseWatcher):
    """Watches Gmail unread+important messages and creates action files."""

    def __init__(self, vault_path: str, check_interval: int = 120):
        super().__init__(vault_path=vault_path, check_interval=check_interval)
        self.credentials_path = self.vault_path / "credentials.json"
        self.token_path = self.vault_path / "token.json"
        self.attachments_dir = self.inbox / "Attachments"
        self.attachments_dir.mkdir(parents=True, exist_ok=True)

        self.processed_ids = set()
        self._load_existing_processed_ids()

        self.service = self._build_gmail_service()

    def _load_existing_processed_ids(self) -> None:
        """Prime processed_ids from existing EMAIL_*.md files to avoid duplicates on restart."""
        for md_file in self.needs_action.glob("EMAIL_*.md"):
            msg_id = md_file.stem.replace("EMAIL_", "", 1)
            if msg_id:
                self.processed_ids.add(msg_id)
        self.logger.info(f"Loaded {len(self.processed_ids)} processed email IDs from Needs_Action.")

    def _build_gmail_service(self):
        """Authenticate and return Gmail API service client."""
        if not self.credentials_path.exists():
            raise FileNotFoundError(
                f"credentials.json not found at: {self.credentials_path}. "
                "Place Google OAuth credentials in your vault root."
            )

        creds = None
        if self.token_path.exists():
            creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(str(self.credentials_path), SCOPES)
                creds = flow.run_local_server(port=0)

            self.token_path.write_text(creds.to_json())
            self.logger.info(f"Saved Gmail token to {self.token_path}")

        return build("gmail", "v1", credentials=creds)

    @staticmethod
    def _get_header(headers: List[Dict[str, str]], name: str) -> str:
        name_l = name.lower()
        for h in headers:
            if h.get("name", "").lower() == name_l:
                return h.get("value", "")
        return ""

    def _download_attachments(self, message_id: str, payload: Dict[str, Any]) -> List[str]:
        """Download all attachments for message and return relative paths."""
        saved_paths: List[str] = []

        def walk_parts(parts: List[Dict[str, Any]]) -> None:
            for part in parts or []:
                filename = part.get("filename", "")
                body = part.get("body", {}) or {}
                attachment_id = body.get("attachmentId")
                sub_parts = part.get("parts", [])

                if filename and attachment_id:
                    safe_name = _sanitize_filename(filename)
                    out_name = f"{message_id}_{safe_name}"
                    out_path = self.attachments_dir / out_name

                    try:
                        att = (
                            self.service.users()
                            .messages()
                            .attachments()
                            .get(userId="me", messageId=message_id, id=attachment_id)
                            .execute()
                        )
                        data = att.get("data", "")
                        if not data:
                            self.logger.warning(
                                f"Attachment payload empty for message={message_id}, file={filename}"
                            )
                        else:
                            raw = base64.urlsafe_b64decode(data.encode("utf-8"))
                            out_path.write_bytes(raw)
                            rel_path = out_path.relative_to(self.vault_path).as_posix()
                            saved_paths.append(rel_path)
                            self.logger.info(f"Downloaded attachment: {rel_path}")
                    except Exception as exc:
                        self.logger.error(
                            f"Failed attachment download for message={message_id}, file={filename}: {exc}"
                        )

                if sub_parts:
                    walk_parts(sub_parts)

        walk_parts(payload.get("parts", []))
        return saved_paths

    def check_for_updates(self) -> List[Dict[str, Any]]:
        """Fetch unread+important emails and return new unprocessed items."""
        query = "is:unread is:important"
        new_items: List[Dict[str, Any]] = []

        try:
            response = (
                self.service.users()
                .messages()
                .list(userId="me", q=query, maxResults=25)
                .execute()
            )
            messages = response.get("messages", [])

            if not messages:
                self.logger.info("No unread+important emails found.")
                return []

            for msg in messages:
                msg_id = msg.get("id")
                if not msg_id or msg_id in self.processed_ids:
                    continue

                full = (
                    self.service.users()
                    .messages()
                    .get(userId="me", id=msg_id, format="full")
                    .execute()
                )

                payload = full.get("payload", {}) or {}
                headers = payload.get("headers", []) or []
                internal_date = full.get("internalDate")

                if internal_date:
                    received = datetime.fromtimestamp(int(internal_date) / 1000, tz=timezone.utc).isoformat()
                else:
                    received = datetime.now(timezone.utc).isoformat()

                attachments = self._download_attachments(msg_id, payload)

                item = {
                    "id": msg_id,
                    "from": self._get_header(headers, "From"),
                    "subject": self._get_header(headers, "Subject"),
                    "snippet": (full.get("snippet") or "").strip(),
                    "received": received,
                    "attachments": attachments,
                }
                new_items.append(item)
                self.processed_ids.add(msg_id)

            if new_items:
                self.logger.info(f"Detected {len(new_items)} new Gmail item(s).")
            else:
                self.logger.info("No new Gmail items after dedupe.")
            return new_items

        except HttpError as exc:
            self.logger.error(f"Gmail API error: {exc}")
            return []
        except Exception as exc:
            self.logger.error(f"Unexpected Gmail watcher error: {exc}")
            return []

    def create_action_file(self, item: Dict[str, Any]) -> Path:
        """Create EMAIL_{id}.md in /Needs_Action with YAML frontmatter."""
        email_id = item["id"]
        md_path = self.needs_action / f"EMAIL_{email_id}.md"

        attachments = item.get("attachments", [])
        if attachments:
            attachment_yaml = "\n".join([f"  - {_yaml_quote(path)}" for path in attachments])
        else:
            attachment_yaml = "  []"

        content = f"""---
type: email
id: {_yaml_quote(email_id)}
from: {_yaml_quote(item.get("from", ""))}
subject: {_yaml_quote(item.get("subject", ""))}
snippet: {_yaml_quote(item.get("snippet", ""))}
received: {_yaml_quote(item.get("received", ""))}
attachments:
{attachment_yaml}
status: pending
---

## Email Summary
- **From:** {item.get("from", "Unknown")}
- **Subject:** {item.get("subject", "(No Subject)")}
- **Received:** {item.get("received", "Unknown")}

## Snippet
{item.get("snippet", "")}

## Attachments
"""
        if attachments:
            content += "\n".join([f"- `{path}`" for path in attachments]) + "\n"
        else:
            content += "- None\n"

        md_path.write_text(content)

        self.log_action(
            "EMAIL_DETECTED",
            f"`{email_id}` | subject={item.get('subject', '(No Subject)')} | attachments={len(attachments)}",
        )
        self.logger.info(f"Created email action file: {md_path.name}")
        return md_path


def main():
    parser = argparse.ArgumentParser(description="Gmail Watcher for AI Employee")
    parser.add_argument(
        "--vault",
        default="AI_Employee_Vault",
        help="Path to vault (default: AI_Employee_Vault)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=120,
        help="Polling interval in seconds (default: 120)",
    )
    args = parser.parse_args()

    vault_path = Path(args.vault)
    if not vault_path.is_absolute():
        vault_path = Path(__file__).parent.parent / vault_path

    watcher = GmailWatcher(vault_path=str(vault_path), check_interval=args.interval)
    watcher.run()


if __name__ == "__main__":
    main()

