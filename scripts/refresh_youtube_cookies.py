#!/usr/bin/env python3
"""Refresh YouTube cookies using Playwright and write a cookies.txt file compatible with yt-dlp.

This script writes a Netscape-style cookies.txt (accepted by yt-dlp) and prints only
non-secret diagnostics: the output path, file size and SHA256. Optionally it can run
a small "canary" yt-dlp query to validate the cookie works against a known video.

See scripts/REFRESH_README.md for setup and deployment notes.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import time
from typing import List, Optional, Tuple


def write_netscape_cookies(cookies: List[dict], out_path: str, meta_comment: str = "") -> None:
    """Write cookies in Netscape cookies.txt format used by wget/yt-dlp.
    
    Filters out cookies with invalid or negative expiration times to avoid
    yt-dlp warnings about "invalid expires at -1".
    """
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
        
        # Parse and validate expires: skip cookies with negative or invalid expires
        expires_raw = c.get("expires")
        expires = 0
        if expires_raw is not None:
            try:
                expires = int(expires_raw)
                # Skip session cookies (expires=-1) and other invalid values
                if expires < 0:
                    continue
            except (ValueError, TypeError):
                expires = 0
        
        name = c.get("name", "")
        value = c.get("value", "")
        
        # Skip cookies with empty names
        if not name:
            continue
        
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


def run_canary(yt_dlp_path: str, cookies_path: str, url: str) -> Tuple[int, str]:
    cmd = [yt_dlp_path, "--cookies", cookies_path, "--no-warnings", "--skip-download", "--dump-json", url]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except Exception as e:
        return (1, f"canary failed to run: {e}")
    if proc.returncode != 0:
        out = proc.stderr.strip() or proc.stdout.strip()
        return (proc.returncode, out)
    return (0, "OK")


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Refresh YouTube cookies via Playwright.")
    p.add_argument("--out", default="/tmp/youtube_cookies.txt", help="Output cookies.txt path")
    p.add_argument("--profile", help="Path to Playwright persistent profile (preferred)")
    p.add_argument("--headless", action="store_true", help="Run browser headlessly")
    p.add_argument("--canary", help="Optional YouTube URL to test the cookies after writing (yt-dlp will be run)")
    p.add_argument("--yt-dlp", default="yt-dlp", help="Path to yt-dlp executable for canary testing")
    args = p.parse_args(argv)

    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        print("ERROR: Playwright is not installed or cannot be imported. Install with:")
        print("  pip install playwright && playwright install chromium")
        print("Detailed error:", exc)
        return 2

    out_path = args.out

    try:
        print(f"[REFRESH] Starting Playwright with profile: {args.profile}, headless: {args.headless}", flush=True)
        playwright = sync_playwright().start()
    except Exception as exc:
        print("ERROR: Failed to start Playwright:", exc, flush=True)
        return 3

    browser_ctx = None
    try:
        if args.profile:
            headless = bool(args.headless)
            print(f"[REFRESH] Launching persistent context from profile: {args.profile}", flush=True)
            browser_ctx = playwright.chromium.launch_persistent_context(user_data_dir=args.profile, headless=headless)
            page = browser_ctx.new_page()
            print("[REFRESH] Navigating to YouTube...", flush=True)
            page.goto("https://www.youtube.com", timeout=60000)
            print("[REFRESH] Page loaded, waiting for cookies...", flush=True)
            time.sleep(2)
            cookies = browser_ctx.cookies()
            print(f"[REFRESH] Got {len(cookies)} cookies from persistent context", flush=True)
        else:
            print("[REFRESH] Launching fresh browser context", flush=True)
            browser = playwright.chromium.launch(headless=bool(args.headless))
            context = browser.new_context()
            page = context.new_page()
            page.goto("https://www.youtube.com", timeout=60000)
            print("Opened browser; please complete a login in the opened browser window (if headful).")
            print("After login, rerun with --profile pointing to a persistent profile directory.")
            time.sleep(2)
            cookies = context.cookies()
            browser_ctx = context

        # simple heuristic (not used further here) — kept for future logging/alerts
        has_session_cookies = any(c.get("name", "").lower() in ("sapisid", "ssid", "sid", "ytid") for c in cookies)
        
        # Filter and clean cookies before writing
        filtered_cookies = []
        for c in cookies:
            # Skip session cookies with invalid expires
            expires_raw = c.get("expires")
            if expires_raw is not None:
                try:
                    expires_val = int(expires_raw)
                    if expires_val < 0:  # Skip negative expiry (session cookies marked as -1)
                        continue
                except (ValueError, TypeError):
                    pass
            filtered_cookies.append(c)
        
        print(f"[REFRESH] Filtered {len(cookies)} cookies -> {len(filtered_cookies)} valid cookies", flush=True)

        print(f"[REFRESH] Writing cookies to {out_path}", flush=True)
        write_netscape_cookies(filtered_cookies, out_path, meta_comment="exported-by-refresh_youtube_cookies.py")
        sha = sha256_of_file(out_path)
        size = size_of_file(out_path)
        print(f"WROTE {out_path} size={size} sha256={sha}")

        if args.canary:
            code, result = run_canary(args.yt_dlp, out_path, args.canary)
            if code == 0:
                print("CANARY OK")
            else:
                print("CANARY FAIL:", result)

        return 0

    except Exception as e:
        print(f"ERROR: Playwright refresh failed: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return 1

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

