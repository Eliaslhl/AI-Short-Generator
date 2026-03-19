#!/usr/bin/env python3
"""
Interactive setup script to create and populate a YouTube browser profile.

This script:
1. Creates a persistent Playwright/Chromium profile directory.
2. Opens a browser window for you to manually log in to YouTube.
3. Exports cookies to a Netscape-format cookies.txt file.
4. Prints the safe diagnostic (size + sha256).

The resulting profile can be reused by the auto-refresh system in production.
Usage:
    python3 scripts/setup_youtube_profile.py --profile /path/to/profile --out /path/to/cookies.txt

Then, set these in production:
    YOUTUBE_BROWSER_PROFILE_DIR=/path/to/profile
    YOUTUBE_AUTO_REFRESH_OUT=/path/to/cookies.txt
    YOUTUBE_ENABLE_AUTO_REFRESH=true
"""

from __future__ import annotations

import argparse
import hashlib
import os
import time
from pathlib import Path
from typing import List


def write_netscape_cookies(cookies: List[dict], out_path: str, meta_comment: str = "") -> None:
    """Write cookies in Netscape cookies.txt format used by wget/yt-dlp."""
    header = [
        "# Netscape HTTP Cookie File",
        f"# Generated: {time.asctime()}",
    ]
    if meta_comment:
        header.append(f"# {meta_comment}")

    lines: List[str] = header + [""]
    for c in cookies:
        # Playwright cookie fields: name, value, domain, path, expires, httpOnly, secure, sameSite
        domain = c.get("domain", "")
        include_subdomains = "TRUE" if domain.startswith(".") or domain.count(".") > 1 else "FALSE"
        path = c.get("path", "/")
        secure = "TRUE" if c.get("secure", False) else "FALSE"
        expires = int(c.get("expires", 0) or 0)
        name = c.get("name", "")
        value = c.get("value", "")
        lines.append("\t".join([domain, include_subdomains, path, secure, str(expires), name, value]))

    content = "\n".join(lines) + "\n"
    with open(out_path, "w", newline="\n") as f:
        f.write(content)


def sha256_of_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def size_of_file(path: str) -> int:
    return os.path.getsize(path)


def main(argv: List[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Interactive setup: create a YouTube browser profile with authenticated session."
    )
    p.add_argument(
        "--profile",
        required=True,
        help="Path to the persistent profile directory to create/use (e.g., ~/.youtube_browser_profile or /data/youtube_profile)",
    )
    p.add_argument(
        "--out",
        default=None,
        help="Path to write the exported cookies.txt file. If not provided, writes to <profile>/../youtube_cookies.txt",
    )
    args = p.parse_args(argv)

    profile_path = args.profile
    out_path = args.out or os.path.join(os.path.dirname(profile_path), "youtube_cookies.txt")

    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        print("ERROR: Playwright is not installed or cannot be imported. Install with:")
        print("  pip install -r scripts/requirements-playwright.txt && playwright install")
        print("Detailed error:", exc)
        return 2

    # Ensure profile directory exists
    Path(profile_path).mkdir(parents=True, exist_ok=True)
    print(f"Profile directory: {profile_path}")

    try:
        playwright = sync_playwright().start()
    except Exception as exc:
        print("ERROR: Failed to start Playwright:", exc)
        return 3

    browser_ctx = None
    try:
        print("\n" + "=" * 70)
        print("STEP 1: Opening YouTube in your browser...")
        print("=" * 70)
        print("A browser window will open. Please:")
        print("  1. Navigate to https://www.youtube.com")
        print("  2. Sign in with your Google/YouTube account")
        print("  3. Complete any 2FA or verification if prompted")
        print("  4. Return here once logged in (this script will continue automatically)")
        print("=" * 70 + "\n")

        # Launch a headful browser with the persistent profile
        browser_ctx = playwright.chromium.launch_persistent_context(user_data_dir=profile_path, headless=False)
        page = browser_ctx.new_page()
        page.goto("https://www.youtube.com", timeout=60000)

        print("Browser opened. Waiting for you to complete login...")
        print("(This will auto-continue after 60 seconds or when you press Enter)")

        # Wait for user to signal completion (or timeout after 60s)
        import threading

        user_ready = threading.Event()

        def wait_for_input():
            input("Press Enter when you've completed login: ")
            user_ready.set()

        input_thread = threading.Thread(target=wait_for_input, daemon=True)
        input_thread.start()
        user_ready.wait(timeout=60)

        print("\nExporting cookies...")
        cookies = browser_ctx.cookies()

        if not cookies:
            print("WARNING: No cookies found. Did you log in to YouTube?")
            return 4

        auth_cookies = [
            c for c in cookies if any(auth_key in c.get("name", "").lower() for auth_key in ("sapisid", "ssid", "sid", "ytid", "apisid"))
        ]
        print(f"Found {len(cookies)} total cookies, including {len(auth_cookies)} authentication cookies.")

        write_netscape_cookies(cookies, out_path, meta_comment="setup-youtube-profile.py (authenticated)")
        sha = sha256_of_file(out_path)
        size = size_of_file(out_path)

        print("\n" + "=" * 70)
        print("SUCCESS!")
        print("=" * 70)
        print(f"WROTE {out_path} size={size} sha256={sha}")
        print(f"\nProfile location: {profile_path}")
        print(f"Cookies file: {out_path}")
        print("\nTo use in production, set these environment variables:")
        print(f"  YOUTUBE_BROWSER_PROFILE_DIR={profile_path}")
        print(f"  YOUTUBE_AUTO_REFRESH_OUT={out_path}")
        print("  YOUTUBE_ENABLE_AUTO_REFRESH=true")
        print("=" * 70 + "\n")

        return 0

    finally:
        try:
            if browser_ctx:
                browser_ctx.close()
        except Exception:
            pass
        try:
            playwright.stop()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
