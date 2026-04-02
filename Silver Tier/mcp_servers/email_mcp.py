"""Email MCP server.

Exposes a single MCP tool `send_email` that sends real emails via SMTP
(Gmail-compatible) with optional file attachments.

Run:
    python mcp_servers/email_mcp.py

Required environment variables:
    EMAIL_SMTP_USERNAME
    EMAIL_SMTP_PASSWORD

Optional environment variables:
    EMAIL_SMTP_HOST       (default: smtp.gmail.com)
    EMAIL_SMTP_PORT       (default: 587)
    EMAIL_SMTP_USE_TLS    (default: true)
    EMAIL_FROM            (default: EMAIL_SMTP_USERNAME)
    EMAIL_MCP_LOG_LEVEL   (default: INFO)
"""

from __future__ import annotations

import logging
import mimetypes
import os
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

LOGGER = logging.getLogger("email_mcp")


@dataclass(frozen=True)
class SMTPConfig:
    host: str
    port: int
    username: str
    password: str
    sender: str
    use_tls: bool


class EmailConfigError(ValueError):
    """Raised when required SMTP configuration is missing or invalid."""


class EmailSendError(RuntimeError):
    """Raised when SMTP delivery fails."""


def _str_to_bool(value: str, default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _load_smtp_config() -> SMTPConfig:
    host = os.getenv("EMAIL_SMTP_HOST", "smtp.gmail.com").strip()

    raw_port = os.getenv("EMAIL_SMTP_PORT", "587").strip()
    try:
        port = int(raw_port)
    except ValueError as exc:
        raise EmailConfigError(f"Invalid EMAIL_SMTP_PORT: {raw_port!r}") from exc

    username = os.getenv("EMAIL_SMTP_USERNAME", "").strip()
    password = os.getenv("EMAIL_SMTP_PASSWORD", "").strip()
    sender = os.getenv("EMAIL_FROM", username).strip()
    use_tls = _str_to_bool(os.getenv("EMAIL_SMTP_USE_TLS", "true"), default=True)

    if not username:
        raise EmailConfigError("EMAIL_SMTP_USERNAME is required")
    if not password:
        raise EmailConfigError("EMAIL_SMTP_PASSWORD is required")
    if not sender:
        raise EmailConfigError("EMAIL_FROM or EMAIL_SMTP_USERNAME must be set")

    return SMTPConfig(
        host=host,
        port=port,
        username=username,
        password=password,
        sender=sender,
        use_tls=use_tls,
    )


def _parse_recipients(to: str) -> list[str]:
    recipients = [email.strip() for email in to.split(",") if email.strip()]
    if not recipients:
        raise ValueError("'to' must contain at least one email address")
    return recipients


def _build_message(
    *,
    to: str,
    subject: str,
    body: str,
    sender: str,
    attachment_path: Optional[str] = None,
) -> EmailMessage:
    if not subject.strip():
        raise ValueError("'subject' cannot be empty")
    if not body.strip():
        raise ValueError("'body' cannot be empty")

    recipients = _parse_recipients(to)

    message = EmailMessage()
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    message["Subject"] = subject
    message.set_content(body)

    if attachment_path:
        path = Path(attachment_path).expanduser()
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"Attachment not found: {path}")

        mime_type, encoding = mimetypes.guess_type(path.name)
        if mime_type is None or encoding is not None:
            maintype, subtype = "application", "octet-stream"
        else:
            maintype, subtype = mime_type.split("/", maxsplit=1)

        with path.open("rb") as file_obj:
            message.add_attachment(
                file_obj.read(),
                maintype=maintype,
                subtype=subtype,
                filename=path.name,
            )

    return message


def _send_via_smtp(config: SMTPConfig, message: EmailMessage) -> None:
    try:
        if config.use_tls:
            with smtplib.SMTP(config.host, config.port, timeout=30) as client:
                client.ehlo()
                client.starttls(context=ssl.create_default_context())
                client.ehlo()
                client.login(config.username, config.password)
                client.send_message(message)
        else:
            with smtplib.SMTP_SSL(
                config.host,
                config.port,
                timeout=30,
                context=ssl.create_default_context(),
            ) as client:
                client.login(config.username, config.password)
                client.send_message(message)
    except (smtplib.SMTPException, OSError) as exc:
        raise EmailSendError(f"SMTP send failed: {exc}") from exc


mcp = FastMCP(
    "email",
    instructions=(
        "Send email using SMTP. Configure credentials with environment variables "
        "EMAIL_SMTP_USERNAME and EMAIL_SMTP_PASSWORD."
    ),
)


@mcp.tool()
def send_email(
    to: str,
    subject: str,
    body: str,
    attachment_path: Optional[str] = None,
) -> dict[str, Any]:
    """Send an email with an optional attachment.

    Args:
        to: Recipient email address (or comma-separated addresses).
        subject: Email subject.
        body: Plain text email body.
        attachment_path: Optional path to a file to attach.

    Returns:
        A success payload with recipient and attachment details.
    """

    config = _load_smtp_config()
    message = _build_message(
        to=to,
        subject=subject,
        body=body,
        sender=config.sender,
        attachment_path=attachment_path,
    )

    _send_via_smtp(config, message)

    LOGGER.info(
        "Email sent",
        extra={
            "to": message.get("To", ""),
            "subject": subject,
            "has_attachment": bool(attachment_path),
        },
    )

    return {
        "status": "sent",
        "to": message.get("To", ""),
        "subject": subject,
        "attachment": attachment_path,
    }


if __name__ == "__main__":
    logging.basicConfig(
        level=os.getenv("EMAIL_MCP_LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    mcp.run(transport="stdio")
