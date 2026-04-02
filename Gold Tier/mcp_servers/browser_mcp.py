"""Browser MCP server for social posting via Playwright.

Tools:
    - browser_post_social

Platforms:
    - facebook
    - instagram
    - twitter / x

Modes:
    - draft
    - publish

Required environment variables for publish mode:
    FACEBOOK_EMAIL
    FACEBOOK_PASSWORD
    INSTAGRAM_USERNAME
    INSTAGRAM_PASSWORD
    TWITTER_USERNAME
    TWITTER_PASSWORD

Optional environment variables for X publish:
    TWITTER_EMAIL
    TWITTER_HANDLE
    TWITTER_PROFILE_URL

Optional environment variables:
    BROWSER_MCP_HEADLESS=true|false
    BROWSER_MCP_LOG_LEVEL=INFO
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

from env_utils import load_project_dotenv

LOGGER = logging.getLogger("browser_mcp")
MAX_POST_CHARS = 3000

load_project_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)

mcp = FastMCP(
    "browser_mcp",
    instructions=(
        "Create draft or publish Facebook, Instagram, and X/Twitter social posts. "
        "Use draft mode unless explicit approval exists."
    ),
)


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _validate_platform(platform: str) -> str:
    value = (platform or "").strip().lower()
    if value == "x":
        value = "twitter"
    if value not in {"facebook", "instagram", "twitter"}:
        raise ValueError("'platform' must be one of 'facebook', 'instagram', or 'twitter'")
    return value


def _validate_mode(mode: str) -> str:
    value = (mode or "").strip().lower()
    if value not in {"draft", "publish"}:
        raise ValueError("'mode' must be either 'draft' or 'publish'")
    return value


def _validate_post_text(post_text: str) -> str:
    text = (post_text or "").strip()
    if not text:
        raise ValueError("'post_text' cannot be empty")
    if len(text) > MAX_POST_CHARS:
        raise ValueError(f"'post_text' exceeds limit ({len(text)} > {MAX_POST_CHARS})")
    return text


def _validate_publish_prerequisites(platform: str, image_path: Optional[str]) -> None:
    if platform == "facebook":
        if not os.getenv("FACEBOOK_EMAIL", "").strip() or not os.getenv("FACEBOOK_PASSWORD", "").strip():
            raise ValueError("publish mode requires FACEBOOK_EMAIL and FACEBOOK_PASSWORD")
        return

    if platform == "instagram":
        if not os.getenv("INSTAGRAM_USERNAME", "").strip() or not os.getenv("INSTAGRAM_PASSWORD", "").strip():
            raise ValueError("publish mode requires INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD")
        if not image_path:
            raise ValueError("Instagram publish mode requires 'image_path'")
        return

    if not os.getenv("TWITTER_USERNAME", "").strip() or not os.getenv("TWITTER_PASSWORD", "").strip():
        raise ValueError("publish mode requires TWITTER_USERNAME and TWITTER_PASSWORD")


def _social_summary_path(platform: str) -> Path:
    root = Path(__file__).resolve().parents[1]
    summary_dir = root / "Social_Summary"
    summary_dir.mkdir(parents=True, exist_ok=True)
    if platform == "twitter":
        return summary_dir / "X_Summary.md"
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    return summary_dir / f"{platform}_{stamp}.md"


def _write_summary(
    *,
    platform: str,
    mode: str,
    status: str,
    post_text: str,
    image_prompt: str,
    image_path: Optional[str],
    post_url: str = "",
    response_summary: Any = None,
    error_message: str = "",
) -> str:
    if isinstance(response_summary, dict):
        response_text = json.dumps(response_summary, ensure_ascii=True)
    else:
        response_text = str(response_summary or "").strip()
    summary_path = _social_summary_path(platform)
    entry = f"""## {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- Platform: `{platform}`
- Mode: `{mode}`
- Status: `{status}`
- Post URL: `{post_url}`
- Image Path: `{image_path or ''}`
- Error: `{error_message}`

### Post Text
{post_text}

### Image Prompt
{image_prompt}

### Response Summary
{response_text}
"""
    if platform == "twitter" and summary_path.exists():
        existing = summary_path.read_text(encoding="utf-8").rstrip()
        content = f"{existing}\n\n{entry}\n"
    elif platform == "twitter":
        content = "# X Summary\n\n" + entry + "\n"
    else:
        content = "# Social Post Summary\n\n" + entry
    summary_path.write_text(content, encoding="utf-8")
    return str(summary_path)


async def _click_first(page: Any, selectors: list[str], *, timeout: int = 15000) -> None:
    last_exc: Exception | None = None
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            await locator.wait_for(timeout=timeout)
            await locator.click()
            return
        except Exception as exc:  # pragma: no cover
            last_exc = exc
    raise RuntimeError(f"Unable to click any selector: {selectors!r}") from last_exc


async def _fill_first(page: Any, selectors: list[str], value: str, *, timeout: int = 15000) -> None:
    last_exc: Exception | None = None
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            await locator.wait_for(timeout=timeout)
            await locator.fill(value)
            return
        except Exception as exc:  # pragma: no cover
            last_exc = exc
    raise RuntimeError(f"Unable to fill any selector: {selectors!r}") from last_exc


async def _set_image_if_present(page: Any, image_path: Optional[str]) -> None:
    if not image_path:
        return

    local_image = Path(image_path).expanduser()
    if not local_image.exists() or not local_image.is_file():
        raise FileNotFoundError(f"image_path not found: {local_image}")

    file_input = page.locator("input[type='file']").first
    await file_input.set_input_files(str(local_image))
    await page.wait_for_timeout(2500)


async def _dismiss_optional(page: Any, selectors: list[str], *, timeout: int = 3000) -> None:
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            await locator.wait_for(timeout=timeout)
            await locator.click()
            return
        except Exception:
            continue


async def _publish_facebook(page: Any, post_text: str, image_path: Optional[str]) -> dict[str, Any]:
    email = os.getenv("FACEBOOK_EMAIL", "").strip()
    password = os.getenv("FACEBOOK_PASSWORD", "").strip()
    if not email or not password:
        raise ValueError("publish mode requires FACEBOOK_EMAIL and FACEBOOK_PASSWORD")

    await page.goto("https://www.facebook.com/login", wait_until="domcontentloaded", timeout=60000)
    await _fill_first(page, ["#email", "input[name='email']"], email)
    await _fill_first(page, ["#pass", "input[name='pass']"], password)
    await _click_first(page, ["button[name='login']", "button:has-text('Log in')"])
    await page.wait_for_load_state("networkidle", timeout=60000)

    await page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=60000)
    await _dismiss_optional(page, ["button:has-text('Not Now')", "div[aria-label='Close']"])
    await _click_first(
        page,
        [
            "div[aria-label=\"What's on your mind?\"]",
            "span:has-text(\"What's on your mind\")",
            "div[role='button']:has-text(\"What's on your mind\")",
        ],
        timeout=30000,
    )
    await _fill_first(
        page,
        [
            "div[role='dialog'] div[contenteditable='true']",
            "div[role='textbox'][contenteditable='true']",
        ],
        post_text,
        timeout=30000,
    )
    await _set_image_if_present(page, image_path)
    await _click_first(
        page,
        [
            "div[role='dialog'] div[aria-label='Post']",
            "div[role='dialog'] span:has-text('Post')",
            "button:has-text('Post')",
        ],
        timeout=30000,
    )
    await page.wait_for_timeout(5000)
    return {"status": "posted", "url": page.url, "chars": len(post_text)}


async def _publish_instagram(page: Any, post_text: str, image_path: Optional[str]) -> dict[str, Any]:
    username = os.getenv("INSTAGRAM_USERNAME", "").strip()
    password = os.getenv("INSTAGRAM_PASSWORD", "").strip()
    if not username or not password:
        raise ValueError("publish mode requires INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD")
    if not image_path:
        raise ValueError("Instagram publish mode requires 'image_path'")

    await page.goto("https://www.instagram.com/accounts/login/", wait_until="domcontentloaded", timeout=60000)
    await _fill_first(page, ["input[name='username']"], username)
    await _fill_first(page, ["input[name='password']"], password)
    await _click_first(page, ["button[type='submit']", "button:has-text('Log in')"])
    await page.wait_for_load_state("networkidle", timeout=60000)

    await _dismiss_optional(page, ["button:has-text('Not Now')"])
    await _click_first(
        page,
        [
            "svg[aria-label='New post']",
            "a[href='#'] svg[aria-label='New post']",
            "span:has-text('Create')",
        ],
        timeout=30000,
    )
    await _set_image_if_present(page, image_path)
    await _click_first(page, ["button:has-text('Next')"], timeout=30000)
    await _click_first(page, ["button:has-text('Next')"], timeout=30000)
    await _fill_first(page, ["textarea[aria-label='Write a caption…']", "textarea"], post_text, timeout=30000)
    await _click_first(page, ["button:has-text('Share')"], timeout=30000)
    await page.wait_for_timeout(6000)
    return {"status": "posted", "url": page.url, "chars": len(post_text)}


async def _read_locator_text(page: Any, selector: str, *, timeout: int = 3000) -> str:
    try:
        locator = page.locator(selector).first
        await locator.wait_for(timeout=timeout)
        return (await locator.text_content() or "").strip()
    except Exception:
        return ""


async def _extract_twitter_response_summary(page: Any) -> dict[str, str]:
    summary: dict[str, str] = {}
    for key, selector in {
        "replies": "[data-testid='reply']",
        "reposts": "[data-testid='retweet']",
        "likes": "[data-testid='like']",
        "views": "a[href$='/analytics']",
    }.items():
        text = await _read_locator_text(page, selector)
        if text:
            summary[key] = " ".join(text.split())
    return summary


async def _publish_twitter(page: Any, post_text: str, image_path: Optional[str]) -> dict[str, Any]:
    username = os.getenv("TWITTER_USERNAME", "").strip()
    password = os.getenv("TWITTER_PASSWORD", "").strip()
    email = os.getenv("TWITTER_EMAIL", "").strip()
    handle = os.getenv("TWITTER_HANDLE", "").strip().lstrip("@")
    profile_url = os.getenv("TWITTER_PROFILE_URL", "").strip()

    if not username or not password:
        raise ValueError("publish mode requires TWITTER_USERNAME and TWITTER_PASSWORD")

    await page.goto("https://x.com/i/flow/login", wait_until="domcontentloaded", timeout=60000)
    await _fill_first(page, ["input[autocomplete='username']", "input[name='text']"], username, timeout=30000)
    await _click_first(page, ["div[role='button']:has-text('Next')", "button:has-text('Next')"], timeout=30000)
    await page.wait_for_timeout(1500)

    if email:
        try:
            await _fill_first(
                page,
                ["input[data-testid='ocfEnterTextTextInput']", "input[name='text']"],
                email,
                timeout=5000,
            )
            await _click_first(page, ["div[role='button']:has-text('Next')", "button:has-text('Next')"], timeout=10000)
            await page.wait_for_timeout(1000)
        except Exception:
            pass

    await _fill_first(page, ["input[name='password']"], password, timeout=30000)
    await _click_first(
        page,
        ["div[data-testid='LoginForm_Login_Button']", "button:has-text('Log in')", "button:has-text('Log in')"],
        timeout=30000,
    )
    await page.wait_for_load_state("networkidle", timeout=60000)

    if "/account/access" in page.url or "/i/flow/" in page.url:
        raise RuntimeError("X login requires manual verification")

    await page.goto("https://x.com/compose/post", wait_until="domcontentloaded", timeout=60000)
    await _fill_first(
        page,
        [
            "div[data-testid='tweetTextarea_0']",
            "div[role='textbox'][data-testid='tweetTextarea_0']",
            "div[role='textbox']",
        ],
        post_text,
        timeout=30000,
    )
    await _set_image_if_present(page, image_path)
    await _click_first(
        page,
        ["button[data-testid='tweetButton']", "button[data-testid='tweetButtonInline']"],
        timeout=30000,
    )
    await page.wait_for_timeout(5000)

    post_url = ""
    try:
        if profile_url:
            await page.goto(profile_url, wait_until="domcontentloaded", timeout=60000)
        elif handle:
            await page.goto(f"https://x.com/{handle}", wait_until="domcontentloaded", timeout=60000)
        else:
            await page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=60000)
        link = page.locator("article a[href*='/status/']").first
        await link.wait_for(timeout=15000)
        href = await link.get_attribute("href")
        if href:
            post_url = href if href.startswith("http") else f"https://x.com{href}"
            await page.goto(post_url, wait_until="domcontentloaded", timeout=60000)
    except Exception:
        post_url = ""

    response_summary = await _extract_twitter_response_summary(page)
    return {
        "status": "posted",
        "url": post_url,
        "chars": len(post_text),
        "response_summary": response_summary,
    }


async def _publish_via_playwright(
    *,
    platform: str,
    post_text: str,
    image_path: Optional[str],
    headless: bool,
) -> dict[str, Any]:
    try:
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError
        from playwright.async_api import async_playwright
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("Playwright is required for publish mode.") from exc

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=headless)
        context = await browser.new_context()
        page = await context.new_page()
        try:
            if platform == "facebook":
                return await _publish_facebook(page, post_text, image_path)
            if platform == "instagram":
                return await _publish_instagram(page, post_text, image_path)
            return await _publish_twitter(page, post_text, image_path)
        except PlaywrightTimeoutError as exc:  # pragma: no cover
            raise RuntimeError(f"{platform} automation timeout: {exc}") from exc
        finally:
            await context.close()
            await browser.close()


@mcp.tool()
async def browser_post_social(
    platform: str,
    mode: str,
    post_text: str,
    image_prompt: str = "",
    image_path: Optional[str] = None,
    requires_hitl: bool = True,
    headless: Optional[bool] = None,
) -> dict[str, Any]:
    """Create draft or publish a Facebook/Instagram/X post."""

    selected_platform = _validate_platform(platform)
    selected_mode = _validate_mode(mode)
    text = _validate_post_text(post_text)

    if selected_mode == "publish" and requires_hitl:
        raise ValueError("publish mode blocked because 'requires_hitl' is true")

    if selected_mode == "draft":
        summary_path = _write_summary(
            platform=selected_platform,
            mode=selected_mode,
            status="draft_ready",
            post_text=text,
            image_prompt=image_prompt,
            image_path=image_path,
            response_summary="",
        )
        return {
            "status": "draft_ready",
            "platform": selected_platform,
            "mode": selected_mode,
            "chars": len(text),
            "post_text": text,
            "image_prompt": image_prompt,
            "image_path": image_path,
            "summary_path": summary_path,
            "requires_hitl": requires_hitl,
        }

    _validate_publish_prerequisites(selected_platform, image_path)
    headless_value = _env_bool("BROWSER_MCP_HEADLESS", True) if headless is None else bool(headless)
    try:
        publish_result = await _publish_via_playwright(
            platform=selected_platform,
            post_text=text,
            image_path=image_path,
            headless=headless_value,
        )
        summary_path = _write_summary(
            platform=selected_platform,
            mode=selected_mode,
            status="posted",
            post_text=text,
            image_prompt=image_prompt,
            image_path=image_path,
            post_url=str(publish_result.get("url", "")),
            response_summary=publish_result.get("response_summary", ""),
        )
        publish_result.update(
            {
                "platform": selected_platform,
                "mode": selected_mode,
                "summary_path": summary_path,
                "requires_hitl": requires_hitl,
            }
        )
        return publish_result
    except Exception as exc:
        summary_path = _write_summary(
            platform=selected_platform,
            mode=selected_mode,
            status="error",
            post_text=text,
            image_prompt=image_prompt,
            image_path=image_path,
            response_summary="",
            error_message=str(exc),
        )
        raise RuntimeError(f"{selected_platform} publish failed. Summary: {summary_path}. Error: {exc}") from exc


if __name__ == "__main__":
    logging.basicConfig(
        level=os.getenv("BROWSER_MCP_LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    mcp.run(transport="stdio")
