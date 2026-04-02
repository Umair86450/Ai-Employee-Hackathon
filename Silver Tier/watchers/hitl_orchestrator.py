"""
HITL Orchestrator for Silver Tier.

Flow:
1. Sensitive action requests are written as APPROVAL_*.md in /Pending_Approval.
2. Human reviews and moves approved files to /Approved.
3. Orchestrator watches /Approved and executes the MCP tool.
4. Failed approvals are moved to /Rejected with a logged error.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from watchdog.events import FileSystemEvent, FileSystemEventHandler, FileSystemMovedEvent
from watchdog.observers import Observer


SENSITIVE_ACTIONS = {"email_send", "linkedin_post", "payment"}

ACTION_DEFAULTS: dict[str, dict[str, str]] = {
    "email_send": {"mcp_server": "email_mcp", "mcp_tool": "send_email"},
    "linkedin_post": {"mcp_server": "linkedin_mcp", "mcp_tool": "browser_post_linkedin"},
    "payment": {"mcp_server": "payment_mcp", "mcp_tool": "process_payment"},
}

LOGGER = logging.getLogger("HITLOrchestrator")


def _timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H%M%S")


def _now_human() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text

    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text

    header = text[4:end]
    body = text[end + len("\n---\n") :]
    data: dict[str, str] = {}
    for raw_line in header.splitlines():
        line = raw_line.strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip().strip('"').strip("'")
        data[key.strip()] = value
    return data, body


def _extract_json_block(text: str) -> dict[str, Any]:
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, flags=re.S)
    if not match:
        return {}
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return {}


def _yaml_quote(value: str) -> str:
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def _set_frontmatter_value(text: str, key: str, value: str, *, quoted: bool = False) -> str:
    if not text.startswith("---\n"):
        return text

    end = text.find("\n---\n", 4)
    if end == -1:
        return text

    header = text[4:end]
    body = text[end + len("\n---\n") :]
    rendered = _yaml_quote(value) if quoted else value
    pattern = re.compile(rf"(?m)^{re.escape(key)}:\s*.*$")

    if pattern.search(header):
        header = pattern.sub(f"{key}: {rendered}", header, count=1)
    else:
        header = header.rstrip("\n") + f"\n{key}: {rendered}"

    return f"---\n{header}\n---\n{body}"


class ApprovedEventHandler(FileSystemEventHandler):
    def __init__(self, orchestrator: "HITLOrchestrator"):
        self.orchestrator = orchestrator
        self._processed: set[str] = set()

    def _handle_candidate(self, path: Path) -> None:
        path = path.resolve()
        if path.suffix.lower() != ".md":
            return
        if not path.name.startswith("APPROVAL_"):
            return
        if path.parent != self.orchestrator.approved.resolve():
            return
        key = str(path)
        if key in self._processed:
            return
        self._processed.add(key)
        self.orchestrator.process_approved_file(path)

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._handle_candidate(Path(event.src_path))

    def on_moved(self, event: FileSystemMovedEvent) -> None:
        if event.is_directory:
            return
        self._handle_candidate(Path(event.dest_path))


class HITLOrchestrator:
    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path).resolve()
        self.project_root = self.vault_path.parent
        self.pending_approval = self.vault_path / "Pending_Approval"
        self.approved = self.vault_path / "Approved"
        self.rejected = self.vault_path / "Rejected"
        self.logs = self.vault_path / "Logs"
        self.observer = Observer()
        self.event_handler = ApprovedEventHandler(self)

        for folder in [self.pending_approval, self.approved, self.rejected, self.logs]:
            folder.mkdir(parents=True, exist_ok=True)

    def log_action(self, action_type: str, details: str) -> None:
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.logs / f"{today}.md"
        if not log_file.exists():
            log_file.write_text(f"# Log — {today}\n")
        with log_file.open("a", encoding="utf-8") as handle:
            handle.write(f"\n- `{_now_human()}` | **{action_type}** | {details}")

    def create_approval_request(
        self,
        *,
        action_type: str,
        objective: str,
        details: str,
        mcp_arguments: dict[str, Any] | None = None,
        source_file: str = "",
        mcp_server: str = "",
        mcp_tool: str = "",
    ) -> Path:
        action_type = action_type.strip().lower()
        if action_type not in SENSITIVE_ACTIONS:
            allowed = ", ".join(sorted(SENSITIVE_ACTIONS))
            raise ValueError(f"Unsupported action_type '{action_type}'. Allowed: {allowed}")

        defaults = ACTION_DEFAULTS.get(action_type, {})
        server_name = (mcp_server or defaults.get("mcp_server", "")).strip()
        tool_name = (mcp_tool or defaults.get("mcp_tool", "")).strip()
        request_id = f"{_timestamp()}_{action_type}"
        filename = f"APPROVAL_{request_id}.md"
        path = self.pending_approval / filename
        payload = mcp_arguments or {}

        content = f"""---
request_id: {request_id}
status: pending
created_at: {_now_human()}
action_type: {action_type}
source_file: "{source_file}"
mcp_server: {server_name}
mcp_tool: {tool_name}
---

# Approval Request

## Objective
{objective}

## Details
{details}

## MCP Arguments
```json
{json.dumps(payload, indent=2, ensure_ascii=True)}
```
"""
        path.write_text(content, encoding="utf-8")
        self.log_action(
            "APPROVAL_CREATED",
            f"`{filename}` action_type={action_type} mcp_tool={tool_name or 'unset'}",
        )
        return path

    def _load_mcp_server_config(self, server_name: str) -> dict[str, Any]:
        cfg_path = self.project_root / "mcp.json"
        if not cfg_path.exists():
            raise FileNotFoundError(f"mcp.json not found at {cfg_path}")
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
        servers = data.get("mcpServers", {})
        if server_name not in servers:
            known = ", ".join(sorted(servers.keys())) or "(none)"
            raise KeyError(f"MCP server '{server_name}' not found in mcp.json. Known: {known}")
        return servers[server_name]

    async def _call_mcp_tool_async(
        self, *, server_name: str, tool_name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        server_cfg = self._load_mcp_server_config(server_name)
        command = server_cfg.get("command")
        if not command:
            raise ValueError(f"MCP server '{server_name}' is missing 'command'")
        args = server_cfg.get("args") or []
        env = dict(os.environ)
        env.update({k: str(v) for k, v in (server_cfg.get("env") or {}).items()})

        server_params = StdioServerParameters(
            command=str(command),
            args=[str(arg) for arg in args],
            env=env,
            cwd=str(self.project_root),
        )

        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments=arguments)
                if hasattr(result, "model_dump"):
                    return result.model_dump()
                return {"result": str(result)}

    def _parse_approval_file(self, path: Path) -> dict[str, Any]:
        text = path.read_text(encoding="utf-8")
        frontmatter, body = _split_frontmatter(text)
        mcp_args = _extract_json_block(body)
        return {
            "request_id": frontmatter.get("request_id", path.stem),
            "status": frontmatter.get("status", "pending"),
            "action_type": frontmatter.get("action_type", "").strip().lower(),
            "mcp_server": frontmatter.get("mcp_server", "").strip(),
            "mcp_tool": frontmatter.get("mcp_tool", "").strip(),
            "mcp_arguments": mcp_args,
        }

    def _mark_status(self, path: Path, status: str) -> None:
        text = path.read_text(encoding="utf-8")
        text = _set_frontmatter_value(text, "status", status)
        text = _set_frontmatter_value(text, "updated_at", _now_human(), quoted=True)
        path.write_text(text, encoding="utf-8")

    def _reject_file(self, path: Path, reason: str) -> None:
        if path.exists():
            self._mark_status(path, "rejected")
        target = self.rejected / path.name
        if target.exists():
            target = self.rejected / f"{path.stem}_{_timestamp()}{path.suffix}"
        shutil.move(str(path), str(target))
        with target.open("a", encoding="utf-8") as handle:
            handle.write(f"\n\n## Rejection Reason\n{reason}\n")
        self.log_action("APPROVAL_REJECTED", f"`{target.name}` reason={reason}")

    def process_approved_file(self, path: Path) -> None:
        try:
            data = self._parse_approval_file(path)
            if data["status"].strip().lower() == "executed":
                LOGGER.info("Skipping already executed approval file %s", path.name)
                return

            action_type = data["action_type"]
            if action_type not in SENSITIVE_ACTIONS:
                self._reject_file(path, f"Invalid action_type: '{action_type}'")
                return

            defaults = ACTION_DEFAULTS.get(action_type, {})
            server_name = data["mcp_server"] or defaults.get("mcp_server", "")
            tool_name = data["mcp_tool"] or defaults.get("mcp_tool", "")
            if not server_name or not tool_name:
                self._reject_file(path, "Missing mcp_server or mcp_tool in approval file")
                return

            result = asyncio.run(
                self._call_mcp_tool_async(
                    server_name=server_name,
                    tool_name=tool_name,
                    arguments=data["mcp_arguments"],
                )
            )

            self._mark_status(path, "executed")
            with path.open("a", encoding="utf-8") as handle:
                handle.write(
                    "\n\n## Execution Result\n"
                    f"- Executed At: {_now_human()}\n"
                    f"- MCP Server: {server_name}\n"
                    f"- MCP Tool: {tool_name}\n"
                    "```json\n"
                    f"{json.dumps(result, indent=2, ensure_ascii=True)}\n"
                    "```\n"
                )

            self.log_action(
                "APPROVAL_EXECUTED",
                f"`{path.name}` action_type={action_type} tool={tool_name}",
            )
            LOGGER.info("Executed approved request %s via %s.%s", path.name, server_name, tool_name)
        except Exception as exc:
            LOGGER.error("Failed to process approved file %s: %s", path.name, exc)
            if path.exists() and path.parent == self.approved:
                self._reject_file(path, f"Execution failed: {exc}")

    def process_all_approved_once(self) -> int:
        """Process all APPROVAL_*.md files currently present in /Approved once."""
        count = 0
        for candidate in sorted(self.approved.glob("APPROVAL_*.md")):
            before = self._parse_approval_file(candidate).get("status", "pending").strip().lower()
            self.process_approved_file(candidate)
            after = self._parse_approval_file(candidate).get("status", before).strip().lower()
            if before != "executed" and after == "executed":
                count += 1
        return count

    def run(self) -> None:
        LOGGER.info("Starting HITL orchestrator")
        LOGGER.info("Watching for approvals in: %s", self.approved)

        # Watch vault root so we can detect move events into /Approved.
        self.observer.schedule(self.event_handler, str(self.vault_path), recursive=False)
        self.observer.start()

        # Process any already-approved files on startup.
        self.process_all_approved_once()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            LOGGER.info("Stopping HITL orchestrator")
            self.observer.stop()
        finally:
            self.observer.join()


def main() -> None:
    parser = argparse.ArgumentParser(description="Silver Tier HITL orchestrator")
    parser.add_argument(
        "--vault",
        default="AI_Employee_Vault",
        help="Path to AI_Employee_Vault (default: AI_Employee_Vault)",
    )
    parser.add_argument(
        "--process-once",
        action="store_true",
        help="Process current /Approved APPROVAL_*.md files once and exit",
    )
    args = parser.parse_args()

    vault_path = Path(args.vault)
    if not vault_path.is_absolute():
        vault_path = Path(__file__).parent.parent / vault_path

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    orchestrator = HITLOrchestrator(str(vault_path))
    if args.process_once:
        processed = orchestrator.process_all_approved_once()
        LOGGER.info("Processed approved files (once): %s", processed)
    else:
        orchestrator.run()


if __name__ == "__main__":
    main()
