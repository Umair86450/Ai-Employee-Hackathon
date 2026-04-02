"""
WhatsApp Watcher - Silver Tier

Monitors unread WhatsApp Web chats via Playwright persistent session and creates
action files for keyword-matched messages.

Usage:
    python watchers/WhatsAppWatcher.py
    python watchers/WhatsAppWatcher.py --vault AI_Employee_Vault
"""

import re
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Add parent dir to path so we can import base_watcher
sys.path.insert(0, str(Path(__file__).parent.parent))
from watchers.base_watcher import BaseWatcher


KEYWORDS = ["urgent", "invoice", "payment", "pricing", "help"]


def _sanitize_filename(name: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in name.strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned or "unknown_contact"


def _yaml_quote(value: str) -> str:
    value = (value or "").replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").strip()
    return f'"{value}"'


class WhatsAppWatcher(BaseWatcher):
    """
    Watches unread chats in WhatsApp Web and creates action files for messages
    containing business-critical keywords.
    """

    def __init__(
        self,
        vault_path: str,
        check_interval: int = 60,
        debug_unread: bool = False,
        require_keywords: bool = False,
    ):
        super().__init__(vault_path=vault_path, check_interval=check_interval)
        self.processed_ids = set()
        self.debug_unread = debug_unread
        self.require_keywords = require_keywords

        self.session_dir = Path(__file__).parent.parent / "whatsapp_session"
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.auth_marker = self.session_dir / ".authenticated"
        self.session_cookie_hints = [
            self.session_dir / "Default" / "Network" / "Cookies",
            self.session_dir / "Default" / "Cookies",
        ]

        self._playwright = None
        self.context = None
        self.page = None

        self._bootstrap_browser()

    def _debug_unread_snapshot(self) -> None:
        if not self.debug_unread:
            return
        selectors = {
            "icon-unread-count": "[data-testid='icon-unread-count']",
            "unread-count": "[data-testid='unread-count']",
            "unread-aria": "[aria-label*='unread message'], [aria-label*='unread messages']",
            "chat-cells": "[data-testid='cell-frame-container']",
            "chat-list": "[data-testid='chat-list']",
            "chat-list-aria": "[aria-label='Chat list']",
            "gridcell": "div[role='gridcell']",
            "qr-canvas": "canvas[aria-label*='Scan'], canvas[aria-label*='scan']",
        }
        for name, selector in selectors.items():
            try:
                count = self.page.locator(selector).count()
            except Exception as exc:
                count = f"err:{exc}"
            self.logger.info(f"[debug-unread] {name}={count}")

    def _has_authenticated_session_hint(self) -> bool:
        if self.auth_marker.exists():
            return True
        return any(path.exists() and path.stat().st_size > 0 for path in self.session_cookie_hints)

    def _bootstrap_browser(self) -> None:
        has_existing_session = self._has_authenticated_session_hint()

        # First-time QR scan requires visible browser; once session is saved,
        # watcher automatically runs headless=True on next launches.
        headless_mode = has_existing_session

        self.logger.info(f"Launching WhatsApp Web (headless={headless_mode})")
        self._playwright = sync_playwright().start()
        launch_kwargs = dict(
            user_data_dir=str(self.session_dir),
            headless=headless_mode,
            viewport={"width": 1366, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
        )
        try:
            # Prefer system Chrome; WhatsApp Web is more stable here vs bundled Chromium.
            self.context = self._playwright.chromium.launch_persistent_context(
                channel="chrome",
                **launch_kwargs,
            )
        except Exception:
            self.context = self._playwright.chromium.launch_persistent_context(**launch_kwargs)
        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
        self.page.goto("https://web.whatsapp.com", wait_until="domcontentloaded")

        self._ensure_whatsapp_ready(headless_mode=headless_mode)

    def _is_logged_in_ui(self) -> bool:
        selectors = [
            "[data-testid='chat-list']",
            "[data-testid='chat-list-search']",
            "[data-testid='cell-frame-container']",
            "div[role='textbox'][aria-label]",
            "[aria-label='Chat list']",
            "[aria-label='Search or start a new chat']",
        ]
        for selector in selectors:
            try:
                if self.page.locator(selector).count() > 0:
                    return True
            except Exception:
                continue
        return False

    def _is_qr_ui(self) -> bool:
        selectors = [
            "canvas[aria-label*='Scan']",
            "canvas[aria-label*='scan']",
            "text=Scan to log in",
            "text=Log in with phone number",
        ]
        for selector in selectors:
            try:
                if self.page.locator(selector).count() > 0:
                    return True
            except Exception:
                continue
        return False

    def _ensure_whatsapp_ready(self, headless_mode: bool) -> None:
        # If we already have persisted auth/session hints, do a short readiness check
        # and continue quickly to avoid forcing QR flow again.
        deadline_seconds = 30 if headless_mode else 600
        deadline = time.time() + deadline_seconds
        qr_logged = False

        while time.time() < deadline:
            if self._is_logged_in_ui():
                self.logger.info("WhatsApp chat UI detected.")
                if not self.auth_marker.exists():
                    self.auth_marker.write_text(datetime.now().isoformat())
                return

            qr_visible = self._is_qr_ui()
            if qr_visible and headless_mode:
                # Session likely expired. Remove marker so next run opens visible login once.
                if self.auth_marker.exists():
                    self.auth_marker.unlink(missing_ok=True)
                raise RuntimeError(
                    "Session appears expired (QR/login screen in headless mode). "
                    "Run once in visible mode to re-link WhatsApp."
                )

            if qr_visible and not qr_logged:
                self.logger.info("QR/login UI detected. Waiting for scan/login completion...")
                qr_logged = True

            self.page.wait_for_timeout(2000)

        if headless_mode:
            self.logger.warning(
                "Could not confirm chat list quickly, but session hint exists. Continuing without QR wait."
            )
            return

        raise PlaywrightTimeoutError(
            f"Timed out waiting for WhatsApp Web login/chat UI after {deadline_seconds}s."
        )

    def _collect_unread_chat_rows(self) -> List:
        rows = []
        seen = set()

        # Query multiple UI variants:
        # - Old: cell-frame-container + unread badges
        # - New: Chat list aria + gridcell rows containing unread aria labels
        row_locators = [
            self.page.locator(
                "div[role='gridcell']:has([data-testid='icon-unread-count']), "
                "div[role='gridcell']:has([data-testid='unread-count'])"
            ),
            self.page.locator(
                "[aria-label='Chat list'] div[role='gridcell']:has([aria-label*='unread message']), "
                "[aria-label='Chat list'] div[role='gridcell']:has([aria-label*='unread messages'])"
            ),
            self.page.locator(
                "[data-testid='cell-frame-container']:has([data-testid='icon-unread-count']), "
                "[data-testid='cell-frame-container']:has([data-testid='unread-count'])"
            ),
        ]

        for locator in row_locators:
            for i in range(locator.count()):
                row = locator.nth(i)
                try:
                    key = row.inner_text(timeout=1500)
                except Exception:
                    key = f"row_{i}"

                if not key.strip():
                    continue

                # Ignore top-level summary rows such as "21 unread messages".
                key_norm = key.strip().lower()
                if "\n" not in key_norm and key_norm.endswith("unread messages"):
                    continue

                if key in seen:
                    continue
                seen.add(key)
                rows.append(row)

        return rows

    def _extract_chat_preview(self, row) -> Dict[str, str]:
        """
        Extract contact name, last message preview, and timestamp from a chat row.
        Selector fallback chain is used because WhatsApp Web UI attributes evolve.
        """
        return row.evaluate(
            """(el) => {
                const pick = (selectors) => {
                    for (const selector of selectors) {
                        const node = el.querySelector(selector);
                        const text = (node?.textContent || '').trim();
                        if (text) return text;
                    }
                    return '';
                };

                const textLines = (el.innerText || '')
                    .split('\\n')
                    .map((s) => s.trim())
                    .filter(Boolean);

                const contact = pick([
                    "[data-testid='cell-frame-title'] span[title]",
                    "span[title]",
                    "div[role='gridcell'] span[dir='auto']",
                    "span[dir='auto']"
                ]) || (textLines[0] || '');

                const message = pick([
                    "[data-testid='last-msg-container'] span[dir='auto']",
                    "[data-testid='msg-meta'] + div span[dir='auto']",
                    "div[dir='ltr'] span[dir='auto']",
                    "span.selectable-text span",
                    "span[dir='auto']"
                ]) || (textLines[2] || textLines[1] || '');

                const timestamp = pick([
                    "[data-testid='msg-meta'] span",
                    "div[data-testid='msg-meta']",
                    "span[aria-label*=':']"
                ]) || (textLines.find((t) => /\\b\\d{1,2}:\\d{2}\\b/.test(t)) || '');

                const unreadCount = pick([
                    "[data-testid='icon-unread-count']",
                    "[data-testid='unread-count']",
                    "[aria-label*='unread message']",
                    "[aria-label*='unread messages']"
                ]);

                return { contact, message, timestamp, unreadCount };
            }"""
        )

    def check_for_updates(self) -> List[Dict[str, str]]:
        """Return unread chat previews for file creation (keyword-tagged, optionally keyword-filtered)."""
        items: List[Dict[str, str]] = []

        try:
            self._debug_unread_snapshot()

            if self._is_qr_ui():
                self.logger.warning("WhatsApp is on QR/login screen; skipping poll cycle.")
                return []

            unread_rows = self._collect_unread_chat_rows()
            if not unread_rows:
                self.logger.info("No unread chats found.")
                return []

            self.logger.info(f"Found {len(unread_rows)} unread chat row(s).")

            for row in unread_rows:
                preview = self._extract_chat_preview(row)
                contact = (preview.get("contact") or "").strip()
                message = (preview.get("message") or "").strip()
                ts = (preview.get("timestamp") or "").strip()
                unread_count = (preview.get("unreadCount") or "").strip()

                if self.debug_unread:
                    self.logger.info(
                        "[debug-unread] preview "
                        f"contact={contact or '<empty>'} "
                        f"timestamp={ts or '<empty>'} "
                        f"unreadCount={unread_count or '<empty>'} "
                        f"message={message[:120] or '<empty>'}"
                    )

                # Filter non-chat pseudo rows (common in gridcell-heavy UI variants).
                if (contact.isdigit() and not message) or (contact.isdigit() and unread_count and contact in unread_count):
                    if self.debug_unread:
                        self.logger.info("[debug-unread] skipped: non-chat numeric row")
                    continue

                signature = f"{contact}|{message}|{ts}"
                if signature in self.processed_ids:
                    if self.debug_unread:
                        self.logger.info(f"[debug-unread] skipped duplicate signature={signature[:120]}")
                    continue
                self.processed_ids.add(signature)

                lowered = message.lower()
                matched = [k for k in KEYWORDS if k in lowered]
                if self.require_keywords and not matched:
                    if self.debug_unread:
                        self.logger.info("[debug-unread] skipped: no keyword match (require_keywords=True)")
                    continue

                item = {
                    "contact": contact or "Unknown Contact",
                    "message": message or "(No preview text)",
                    "timestamp": ts or "Unknown",
                    "unread_count": unread_count or "",
                    "matched_keywords": matched,
                    "priority": "HIGH" if matched else "MEDIUM",
                    "trigger_behavior": "unread+keyword" if matched else "unread_only",
                    "keyword_policy": "required" if self.require_keywords else "tag_only",
                    "detected_at": datetime.now().isoformat(),
                }
                items.append(item)

            if items:
                keyword_hits = sum(1 for i in items if i.get("matched_keywords"))
                self.logger.info(
                    f"{len(items)} unread WhatsApp item(s) queued "
                    f"(keyword_hits={keyword_hits}, keyword_policy={'required' if self.require_keywords else 'tag_only'})."
                )
            else:
                if self.require_keywords:
                    self.logger.info("Unread chats scanned, no keyword-matched items (require_keywords=True).")
                else:
                    self.logger.info("Unread chats scanned, no new items.")

            return items
        except Exception as exc:
            self.logger.error(f"WhatsApp check_for_updates error: {exc}")
            return []

    def create_action_file(self, item: Dict[str, str]) -> Path:
        """Create or append WHATSAPP_{contact}.md in Needs_Action."""
        safe_contact = _sanitize_filename(item["contact"])
        md_path = self.needs_action / f"WHATSAPP_{safe_contact}.md"

        keywords = item.get("matched_keywords", [])
        priority = item.get("priority", "MEDIUM")
        trigger_behavior = item.get("trigger_behavior", "unread_only")
        keyword_policy = item.get("keyword_policy", "tag_only")
        unread_count = item.get("unread_count", "")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if keywords:
            keywords_yaml = "".join([f"  - {_yaml_quote(k)}\n" for k in keywords])
        else:
            keywords_yaml = "  []\n"

        if not md_path.exists():
            content = f"""---
type: whatsapp
contact: {_yaml_quote(item["contact"])}
last_message: {_yaml_quote(item["message"])}
message_time: {_yaml_quote(item["timestamp"])}
unread_count: {_yaml_quote(unread_count)}
priority: {_yaml_quote(priority)}
trigger_behavior: {_yaml_quote(trigger_behavior)}
keyword_policy: {_yaml_quote(keyword_policy)}
matched_keywords:
{keywords_yaml}status: pending
updated_at: {_yaml_quote(item["detected_at"])}
---

## WhatsApp Alert
- **Contact:** {item["contact"]}
- **Message Time:** {item["timestamp"]}
- **Unread Count:** {unread_count if unread_count else "Unknown"}
- **Priority:** {priority}
- **Trigger Behavior:** {trigger_behavior}
- **Keywords:** {", ".join(keywords) if keywords else "None"}

## Latest Message
{item["message"]}

## Activity Log
- `{now}` | Captured unread message | trigger={trigger_behavior} | keywords={", ".join(keywords) if keywords else "None"}
"""
            md_path.write_text(content)
            action = "created"
        else:
            append = (
                f"\n- `{now}` | {item['timestamp']} | {item['message']} "
                f"| trigger={trigger_behavior} | keywords={', '.join(keywords) if keywords else 'None'}"
            )
            with open(md_path, "a") as f:
                f.write(append)
            action = "appended"

        self.log_action(
            "WHATSAPP_ALERT",
            f"{action} `{md_path.name}` for `{item['contact']}` "
            f"(trigger={trigger_behavior}, keywords={','.join(keywords) if keywords else 'none'})",
        )
        self.logger.info(f"{action.title()} action file: {md_path.name}")
        return md_path

    def close(self) -> None:
        if self.context:
            try:
                self.context.close()
            except BaseException as exc:
                self.logger.debug(f"Context already closed: {exc}")
            self.context = None
        if self._playwright:
            try:
                self._playwright.stop()
            except BaseException as exc:
                self.logger.debug(f"Playwright already stopped: {exc}")
            self._playwright = None

    def run(self):
        """Run polling loop with graceful Playwright cleanup."""
        try:
            super().run()
        except KeyboardInterrupt:
            self.logger.info("Stopping WhatsAppWatcher...")
        finally:
            self.close()


def main():
    parser = argparse.ArgumentParser(description="WhatsApp Watcher for AI Employee (Silver Tier)")
    parser.add_argument(
        "--vault",
        default="AI_Employee_Vault",
        help="Path to vault (default: AI_Employee_Vault)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Polling interval in seconds (default: 60)",
    )
    parser.add_argument(
        "--debug-unread",
        action="store_true",
        help="Enable unread selector and preview debug logs",
    )
    parser.add_argument(
        "--require-keywords",
        action="store_true",
        help="Only create items when message contains configured KEYWORDS",
    )
    args = parser.parse_args()

    vault_path = Path(args.vault)
    if not vault_path.is_absolute():
        vault_path = Path(__file__).parent.parent / vault_path

    watcher = WhatsAppWatcher(
        vault_path=str(vault_path),
        check_interval=args.interval,
        debug_unread=args.debug_unread,
        require_keywords=args.require_keywords,
    )
    watcher.run()


if __name__ == "__main__":
    main()
