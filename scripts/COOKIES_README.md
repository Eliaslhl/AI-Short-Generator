# YouTube Cookie Management & Auto-Refresh

This directory contains tools to manage YouTube cookies for `yt-dlp` in production, with automatic refresh capabilities when cookies expire.

## Overview

The system works as follows:

1. **Cookie Input** (choose one):
   - **Env vars (primary)**: `YOUTUBE_COOKIES_B64` or split `YOUTUBE_COOKIES_B64_PART_1`, `YOUTUBE_COOKIES_B64_PART_2`, etc.
   - **File path**: `YOUTUBE_COOKIES_FILE` pointing to a `cookies.txt` file

2. **Auto-Refresh** (if enabled):
   - When `yt-dlp` fails with "Sign in to confirm you're not a bot", the system automatically:
     - Runs Playwright refresher script to export fresh cookies from a persistent browser profile
     - Retries the download with new cookies
     - No manual intervention needed

3. **Safe Diagnostics**:
   - All debug output is safe: only file size + SHA256, never cookie contents
   - Enables verification without exposing secrets

## Setup Steps

### Step 1: Prepare a Persistent YouTube Browser Profile (Recommended)

This ensures auto-refresh has a valid authenticated session to work with.

```bash
# Create and populate the profile (interactive – you'll log in manually)
python3 scripts/setup_youtube_profile.py \
  --profile ~/.youtube_browser_profile \
  --out ~/.youtube_cookies.txt
```

When the script runs:
1. A browser window opens
2. You manually log in to YouTube
3. The script exports cookies and prints a safe diagnostic:
   ```
   WROTE /path/to/cookies.txt size=386836 sha256=e634c16f...
   ```

### Step 2: (Production) Configure Environment Variables

Set these in your deployment environment (Railway, Docker, etc.):

```bash
# Enable auto-refresh
YOUTUBE_ENABLE_AUTO_REFRESH=true

# Path to the persistent browser profile (must be accessible to the runtime)
YOUTUBE_BROWSER_PROFILE_DIR=/data/youtube_browser_profile

# Where to write refreshed cookies
YOUTUBE_AUTO_REFRESH_OUT=/tmp/youtube_cookies.txt

# Run headless (no browser window)
YOUTUBE_AUTO_REFRESH_HEADLESS=true

# Optional: validate cookies with a known-good video URL
YOUTUBE_AUTO_REFRESH_CANARY=https://www.youtube.com/watch?v=recHgNtlUjc
```

### Step 3: Input Initial Cookies (if not using Playwright profile)

Option A: **Base64-encoded env var** (if profile not available yet):
```bash
# Encode your cookies.txt
cat ~/.youtube_cookies.txt | base64 | pbcopy  # macOS

# Set the env var (paste clipboard)
export YOUTUBE_COOKIES_B64="<pasted_base64_content>"
```

Option B: **File-based** (simpler):
```bash
export YOUTUBE_COOKIES_FILE=/path/to/cookies.txt
```

## Scripts

### `refresh_youtube_cookies.py`
Playwright-based cookie refresher. Exports cookies from a persistent browser profile and writes a Netscape-format `cookies.txt`.

Usage:
```bash
python3 scripts/refresh_youtube_cookies.py \
  --profile ~/.youtube_browser_profile \
  --out /tmp/youtube_cookies.txt \
  --headless \
  --canary https://www.youtube.com/watch?v=recHgNtlUjc  # optional
```

Output: A single safe diagnostic line
```
WROTE /tmp/youtube_cookies.txt size=386836 sha256=e634c16f...
```

### `setup_youtube_profile.py`
Interactive script to create a browser profile with authenticated YouTube session.

Usage:
```bash
python3 scripts/setup_youtube_profile.py \
  --profile ~/.youtube_browser_profile \
  --out ~/.youtube_cookies.txt
```

Follow the prompts to log in to YouTube. Once done, the profile is ready for production.

### `refresh_oneoff.sh`
Convenience wrapper that:
1. Sources environment from `scripts/refresh.env` (optional)
2. Runs the Playwright refresher
3. Optionally runs yt-dlp canary test
4. Outputs safe diagnostics

Usage:
```bash
# Create and edit config (optional)
cp scripts/refresh.env.example scripts/refresh.env
# Edit YOUTUBE_BROWSER_PROFILE_DIR, etc.

# Run the one-off
bash scripts/refresh_oneoff.sh
```

### `reconstruct_youtube_cookies.py`
Utility to reconstruct cookies from environment variables and verify file size + SHA256.

Usage:
```bash
python3 scripts/reconstruct_youtube_cookies.py
```

Outputs:
```
Reconstructed from YOUTUBE_COOKIES_B64 or PART_* env vars.
size=386836 bytes
sha256=e634c16f...
```

### `run_prod_ytdlp_oneoff.sh`
Test yt-dlp end-to-end with reconstructed cookies (for diagnostics).

Usage:
```bash
bash scripts/run_prod_ytdlp_oneoff.sh "https://www.youtube.com/watch?v=<video_id>"
```

## Auto-Refresh in Action

When a production job encounters "Sign in to confirm you're not a bot":

1. **Detection**: Backend recognizes the error message
2. **Refresh**: Launches `scripts/refresh_youtube_cookies.py` with the configured profile
3. **Parsing**: Extracts safe diagnostic (size + sha256) from output
4. **Retry**: Immediately retries the download with fresh cookies
5. **Result**:
   - Success: Video downloads (no intervention needed)
   - Failure: Error logged with suggestions; user can manually re-run or upload cookies

**Rate-limit**: Only 1 auto-refresh attempt per job per hour (prevents infinite loops).

## Diagnostics & Debugging

### Check if auto-refresh is enabled
```python
import os
print(os.environ.get("YOUTUBE_ENABLE_AUTO_REFRESH"))  # Should be "true" or "1"
print(os.environ.get("YOUTUBE_BROWSER_PROFILE_DIR"))  # Path to profile
```

### Manual refresh test (dev/test only)
```bash
curl -X POST http://localhost:8080/api/debug/refresh-cookies
```

Returns:
```json
{
  "status": "success",
  "diagnostic": "WROTE ... size=... sha256=...",
  "profile_dir": "/path/to/profile",
  "output_path": "/tmp/youtube_cookies.txt"
}
```

### Verify profile has valid cookies
```bash
# Check profile directory exists and has cookies
ls -lh ~/.youtube_browser_profile/

# Check exported cookies file
wc -l ~/.youtube_cookies.txt
head -20 ~/.youtube_cookies.txt
```

## Troubleshooting

### "No cookies found" / Profile not working

**Cause**: Profile directory empty or login expired.

**Fix**:
1. Re-run setup script in headful mode (not headless):
   ```bash
   python3 scripts/setup_youtube_profile.py --profile ~/.youtube_browser_profile --out ~/.youtube_cookies.txt
   ```
2. Manually log in to YouTube when the browser opens
3. Re-export cookies

### "Sign in to confirm..." persists even after refresh

**Cause**: Multiple possibilities:
- New profile doesn't have authentication cookies
- IP address changed (cookies tied to session/IP)
- YouTube session expired or revoked

**Fix**:
1. Verify profile has auth cookies: `grep -i "sapisid\|ssid" ~/.youtube_cookies.txt`
2. Re-login via the setup script
3. Ensure refresher and yt-dlp run from same IP (they do in the same job)

### Playwright errors / Browser crashes

**Cause**: Playwright not installed or browser binaries missing.

**Fix**:
```bash
pip install -r scripts/requirements-playwright.txt
python3 -m playwright install
```

### Docker / Railway: "Profile directory not found"

**Cause**: Profile path not mounted/persistent.

**Fix**:
1. Use a persistent volume in Railway/Docker
2. Copy the profile to the volume before first run
3. Ensure path matches `YOUTUBE_BROWSER_PROFILE_DIR` env var

## Development Notes

### Testing locally

```bash
# Install dependencies
pip install -r scripts/requirements-playwright.txt
python3 -m playwright install

# Create a local profile with auth
python3 scripts/setup_youtube_profile.py --profile /tmp/test_profile

# Test the refresher
python3 scripts/refresh_youtube_cookies.py --profile /tmp/test_profile --out /tmp/test_cookies.txt

# Test yt-dlp with the cookies
yt-dlp --cookies /tmp/test_cookies.txt --skip-download https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

### Production deployment checklist

- [ ] Playwright and browsers installed in image
- [ ] Persistent browser profile mounted or available
- [ ] `YOUTUBE_ENABLE_AUTO_REFRESH=true` set
- [ ] `YOUTUBE_BROWSER_PROFILE_DIR` points to profile path
- [ ] Initial cookies provided (via env or file)
- [ ] Test download succeeds or auto-refresh triggers on first bot-check error
- [ ] Check logs for `[YTC AUTO-REFRESH]` diagnostic when refresh occurs

## References

- [yt-dlp Cookies Documentation](https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp)
- [Playwright Documentation](https://playwright.dev/python/)
- [Netscape Cookie Format](http://curl.haxx.se/rfc/cookie_spec.html)
