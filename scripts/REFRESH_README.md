Refresh YouTube cookies (Playwright)
===================================

But minimal README for the refresh script.

Setup
-----

1. Create a Python virtualenv and activate it.

2. Install dependencies:

```bash
pip install -r scripts/requirements-playwright.txt
playwright install
```

3. Create a persistent profile directory to keep the logged-in session.

Example (macOS/Linux):

```bash
mkdir -p ~/.local/share/yt_playwright_profile
# open a browser to log in once (headful):
python3 scripts/refresh_youtube_cookies.py --profile ~/.local/share/yt_playwright_profile
```

This will open a browser; log in to YouTube with the account you want to use. After login, rerun the script with the same `--profile` to export cookies.

Usage
-----

Export cookies and run a canary test:

```bash
python3 scripts/refresh_youtube_cookies.py --profile ~/.local/share/yt_playwright_profile --out /tmp/youtube_cookies.txt --canary https://www.youtube.com/watch?v=recHgNtlUjc
```

The script prints only a safe diagnostic line like:

WROTE /tmp/youtube_cookies.txt size=386836 sha256=e634c16f...

Scheduling
----------

Run this from a scheduled job (Railway scheduled task, cron, etc.). Prefer:
- run the refresher from the same network/location as consumers if YouTube ties cookies to IPs,
- run a canary test after refresh and alert if it fails.

Security
--------

- Do NOT log cookie content. This script only prints size and SHA256.
- Store the profile directory and any secrets with strict ACLs.
