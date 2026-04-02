"""LinkedIn MCP server.

Tool:
    browser_post_linkedin

Modes:
- draft: Validate and return draft payload (safe, no browser login required).
- publish: Attempt real LinkedIn posting via Playwright (requires credentials).

Environment variables for publish mode:
    LINKEDIN_EMAIL
    LINKEDIN_PASSWORD
Optional:
    LINKEDIN_HEADLESS=true|false  (default: true)
    LINKEDIN_MCP_LOG_LEVEL=INFO
"""

from __future__ import annotations

import logging
import os
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

LOGGER = logging.getLogger("linkedin_mcp")
MAX_POST_CHARS = 3000

# Load project-level .env (supports both KEY=... and export KEY=...).
load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)

mcp = FastMCP(
    "linkedin",
    instructions=(
        "Create draft or publish LinkedIn posts. "
        "Use draft mode for HITL-safe flow; use publish mode only when explicitly approved."
    ),
)


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _validate_post_text(post_text: str) -> str:
    text = (post_text or "").strip()
    if not text:
        raise ValueError("'post_text' cannot be empty")
    if len(text) > MAX_POST_CHARS:
        raise ValueError(
            f"'post_text' exceeds LinkedIn limit ({len(text)} > {MAX_POST_CHARS} chars)"
        )
    return text


def _write_draft_audit(post_text: str, image_prompt: str, image_path: Optional[str]) -> str:
    project_root = Path(__file__).resolve().parents[1]
    vault = project_root / "AI_Employee_Vault"
    logs = vault / "Logs"
    logs.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_file = logs / f"{datetime.now().strftime('%Y-%m-%d')}.md"
    if not log_file.exists():
        log_file.write_text(f"# Log — {datetime.now().strftime('%Y-%m-%d')}\n", encoding="utf-8")

    summary = (
        f"\n- `{ts}` | **LINKEDIN_DRAFT_READY** | chars={len(post_text)} "
        f"| image_prompt={'yes' if bool(image_prompt.strip()) else 'no'} "
        f"| image_path={image_path or ''}"
    )
    with log_file.open("a", encoding="utf-8") as handle:
        handle.write(summary)
    return str(log_file)


async def _publish_via_playwright(
    *,
    post_text: str,
    image_path: Optional[str],
    headless: bool,
) -> dict[str, Any]:
    try:
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError
        from playwright.async_api import async_playwright
    except Exception as exc:  # pragma: no cover - runtime dep guard
        raise RuntimeError(
            "Playwright is required for publish mode. Install deps and browsers first."
        ) from exc

    email = os.getenv("LINKEDIN_EMAIL", "").strip()
    password = os.getenv("LINKEDIN_PASSWORD", "").strip()
    if not email or not password:
        raise ValueError(
            "publish mode requires LINKEDIN_EMAIL and LINKEDIN_PASSWORD environment variables"
        )

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=headless)
        context = await browser.new_context()
        page = await context.new_page()
        try:
            await page.goto(
                "https://www.linkedin.com/login",
                wait_until="domcontentloaded",
                timeout=60000,
            )
            await page.fill('input[name="session_key"]', email)
            await page.fill('input[name="session_password"]', password)
            await page.click('button[type="submit"]')
            await page.wait_for_load_state("networkidle", timeout=60000)

            # If security verification appears, we fail closed for HITL/manual resolution.
            if "/checkpoint/" in page.url or "/challenge/" in page.url:
                raise RuntimeError("LinkedIn security checkpoint detected; manual login required")

            await page.goto(
                "https://www.linkedin.com/feed/",
                wait_until="domcontentloaded",
                timeout=60000,
            )
            await page.click("button:has-text('Start a post')", timeout=30000)
            composer = page.locator("div[role='textbox']").first
            await composer.wait_for(timeout=30000)
            await composer.fill(post_text)

            if image_path:
                local_image = Path(image_path).expanduser()
                if not local_image.exists() or not local_image.is_file():
                    raise FileNotFoundError(f"image_path not found: {local_image}")
                file_input = page.locator("input[type='file']").first
                await file_input.set_input_files(str(local_image))
                await page.wait_for_timeout(1500)

            await page.click("button:has-text('Post')", timeout=30000)
            await page.wait_for_timeout(4000)
            return {
                "status": "posted",
                "url": "https://www.linkedin.com/feed/",
                "chars": len(post_text),
            }
        except PlaywrightTimeoutError as exc:
            raise RuntimeError(f"LinkedIn automation timeout: {exc}") from exc
        finally:
            await context.close()
            await browser.close()


@mcp.tool()
async def browser_post_linkedin(
    mode: str,
    post_text: str,
    image_prompt: str = "",
    image_path: Optional[str] = None,
    requires_hitl: bool = True,
    headless: Optional[bool] = None,
) -> dict[str, Any]:
    """Create draft or publish a LinkedIn post.

    Args:
        mode: "draft" or "publish"
        post_text: LinkedIn post body (max 3000 chars)
        image_prompt: Prompt text for image generation
        image_path: Optional local image path to upload in publish mode
        requires_hitl: If true, publish mode is blocked
        headless: Optional browser headless override for publish mode
    """

    selected_mode = (mode or "").strip().lower()
    if selected_mode not in {"draft", "publish"}:
        raise ValueError("'mode' must be either 'draft' or 'publish'")

    text = _validate_post_text(post_text)

    if selected_mode == "publish" and requires_hitl:
        raise ValueError("publish mode blocked because 'requires_hitl' is true")

    if selected_mode == "draft":
        audit_file = _write_draft_audit(text, image_prompt, image_path)
        return {
            "status": "draft_ready",
            "mode": "draft",
            "chars": len(text),
            "post_text": text,
            "image_prompt": image_prompt,
            "image_path": image_path,
            "audit_log": audit_file,
            "requires_hitl": requires_hitl,
        }

    headless_value = _env_bool("LINKEDIN_HEADLESS", True) if headless is None else bool(headless)
    publish_result = await _publish_via_playwright(
        post_text=text,
        image_path=image_path,
        headless=headless_value,
    )
    publish_result["mode"] = "publish"
    publish_result["requires_hitl"] = requires_hitl
    return publish_result


if __name__ == "__main__":
    logging.basicConfig(
        level=os.getenv("LINKEDIN_MCP_LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    mcp.run(transport="stdio")
