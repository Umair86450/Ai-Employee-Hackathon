"""Manual-assisted LinkedIn posting helper.

Flow:
1. Load post text/image from an approval file.
2. Open LinkedIn in a real browser window.
3. Allow manual login / checkpoint completion if needed.
4. Pre-fill the post composer and upload the image.
5. Stop before publishing so the user can review and click Post manually.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VAULT = PROJECT_ROOT / "AI_Employee_Vault"
STATE_FILE = PROJECT_ROOT / ".linkedin_storage_state.json"
MAX_POST_CHARS = 3000


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manual-assisted LinkedIn post launcher")
    parser.add_argument(
        "--approval-file",
        default="",
        help="Path to APPROVAL_*.md file. Defaults to latest LinkedIn approval in Pending_Approval or Approved.",
    )
    parser.add_argument(
        "--fresh-login",
        action="store_true",
        help="Ignore saved LinkedIn storage state and force a fresh login flow.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=600,
        help="Max time to wait for manual login/challenge completion (default: 600).",
    )
    return parser.parse_args()


def _latest_approval_file() -> Path:
    candidates = list((VAULT / "Pending_Approval").glob("APPROVAL_*linkedin_post*.md"))
    candidates += list((VAULT / "Approved").glob("APPROVAL_*linkedin_post*.md"))
    if not candidates:
        raise FileNotFoundError("No LinkedIn approval file found in Pending_Approval or Approved.")
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _extract_json_block(text: str) -> dict:
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, flags=re.S)
    if not match:
        raise ValueError("Approval file is missing JSON payload block.")
    return json.loads(match.group(1))


def _load_payload(approval_file: Path) -> dict:
    payload = _extract_json_block(approval_file.read_text(encoding="utf-8"))
    post_text = str(payload.get("post_text", "")).strip()
    if not post_text:
        raise ValueError("Approval payload has empty post_text.")
    if len(post_text) > MAX_POST_CHARS:
        raise ValueError(f"post_text exceeds LinkedIn limit ({len(post_text)} > {MAX_POST_CHARS}).")
    image_path = payload.get("image_path")
    if image_path:
        image_file = Path(str(image_path)).expanduser()
        if not image_file.exists():
            raise FileNotFoundError(f"image_path not found: {image_file}")
    return payload


def _wait_for_login_ready(page, timeout_seconds: int) -> None:
    start = time.time()
    while time.time() - start < timeout_seconds:
        url = page.url
        if "linkedin.com/feed" in url:
            return
        if "linkedin.com/login" in url:
            time.sleep(1)
            continue
        if "/checkpoint/" in url or "/challenge/" in url:
            print("Security checkpoint detected in browser. Complete it manually, then return here.", flush=True)
        time.sleep(2)
    raise TimeoutError("Timed out waiting for LinkedIn login/checkpoint completion.")


def _manual_checkpoint_handoff(page, timeout_seconds: int) -> None:
    print(
        "Complete login/checkpoint in the browser, then press Enter here to continue.",
        flush=True,
    )
    try:
        input()
    except EOFError:
        pass

    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        url = page.url
        if "linkedin.com/feed" in url:
            return
        if "/checkpoint/" in url or "/challenge/" in url:
            time.sleep(1)
            continue
        # Any non-login LinkedIn page is acceptable; the script can navigate to feed next.
        if "linkedin.com" in url and "login" not in url:
            return
        time.sleep(1)
    raise TimeoutError("LinkedIn checkpoint/login still not cleared after manual confirmation.")


def _attach_image_if_possible(page, image_path: str) -> bool:
    local_image = str(Path(image_path).expanduser())
    photo_selectors = [
        "button:has-text('Add a photo')",
        "button[aria-label*='photo' i]",
        "button[aria-label*='media' i]",
        "button:has(svg)",
    ]
    for selector in photo_selectors:
        try:
            button = page.locator(selector).first
            if button.count():
                button.click(timeout=3000)
                page.wait_for_timeout(1000)
                break
        except Exception:
            continue

    file_selectors = [
        "input[type='file']",
        "input[accept*='image']",
    ]
    for selector in file_selectors:
        try:
            file_input = page.locator(selector).first
            file_input.set_input_files(local_image, timeout=5000)
            page.wait_for_timeout(2500)
            return True
        except Exception:
            continue
    return False


def main() -> int:
    args = _parse_args()
    approval_file = Path(args.approval_file).expanduser() if args.approval_file else _latest_approval_file()
    if not approval_file.is_absolute():
        approval_file = (PROJECT_ROOT / approval_file).resolve()
    payload = _load_payload(approval_file)

    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        raise RuntimeError("Playwright is required. Install project dependencies first.") from exc

    print(f"Using approval file: {approval_file}", flush=True)
    print("Launching browser for manual-assisted LinkedIn posting...", flush=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False, slow_mo=150)
        context_kwargs = {}
        if STATE_FILE.exists() and not args.fresh_login:
            context_kwargs["storage_state"] = str(STATE_FILE)
        context = browser.new_context(**context_kwargs)
        page = context.new_page()
        try:
            page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=60000)

            if "login" in page.url or "/checkpoint/" in page.url or "/challenge/" in page.url:
                page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded", timeout=60000)
                try:
                    _wait_for_login_ready(page, min(args.timeout_seconds, 30))
                except TimeoutError:
                    _manual_checkpoint_handoff(page, args.timeout_seconds)

            context.storage_state(path=str(STATE_FILE))
            page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=60000)
            page.click("button:has-text('Start a post')", timeout=30000)
            composer = page.locator("div[role='textbox']").first
            composer.wait_for(timeout=30000)
            composer.fill(payload["post_text"])

            image_path = payload.get("image_path")
            if image_path:
                attached = _attach_image_if_possible(page, image_path)
                if not attached:
                    print(
                        "Automatic image upload did not complete. Upload the image manually in the browser.",
                        flush=True,
                    )
                    print(f"Image file: {Path(image_path).expanduser()}", flush=True)

            print("\nBrowser is ready.", flush=True)
            print("Review the post in the LinkedIn window and click `Post` manually.", flush=True)
            print("Press Enter here after posting to close the browser.", flush=True)
            input()
            return 0
        except PlaywrightTimeoutError as exc:
            print(f"Playwright timeout: {exc}", file=sys.stderr, flush=True)
            return 1
        finally:
            try:
                context.close()
            except Exception:
                pass
            try:
                browser.close()
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
