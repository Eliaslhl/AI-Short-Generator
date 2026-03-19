#!/usr/bin/env bash
set -euo pipefail
# One-off wrapper: run Playwright refresher then (optionally) run yt-dlp canary
# Usage:
#   source scripts/refresh.env  # optional
#   ./scripts/refresh_oneoff.sh

ROOT_DIR="$(cd "$(dirname "$0")" && cd .. && pwd)"
REFRESH_SCRIPT="$ROOT_DIR/scripts/refresh_youtube_cookies.py"

# Load environment from scripts/refresh.env if present
if [ -f "$ROOT_DIR/scripts/refresh.env" ]; then
  # shellcheck disable=SC1090
  source "$ROOT_DIR/scripts/refresh.env"
fi

OUT_PATH=${YOUTUBE_AUTO_REFRESH_OUT:-"/tmp/youtube_cookies.txt"}
PROFILE=${YOUTUBE_BROWSER_PROFILE_DIR:-""}
HEADLESS=${YOUTUBE_AUTO_REFRESH_HEADLESS:-"true"}
CANARY=${YOUTUBE_AUTO_REFRESH_CANARY:-""}
YT_DLP_PATH=${YT_DLP_PATH:-yt-dlp}

echo "Running refresher..."
ARGS=("--out" "$OUT_PATH")
if [ -n "$PROFILE" ]; then
  ARGS+=("--profile" "$PROFILE")
fi
if [ "${HEADLESS}" = "true" ] || [ "${HEADLESS}" = "1" ]; then
  ARGS+=("--headless")
fi
if [ -n "$CANARY" ]; then
  ARGS+=("--canary" "$CANARY")
fi

# Run refresher with unbuffered stdout so logs appear immediately
python3 -u "$REFRESH_SCRIPT" "${ARGS[@]}" 2>&1 | tee /tmp/refresh_output.log

# Parse the WROTE line
WROTE_LINE=$(grep -m1 '^WROTE ' /tmp/refresh_output.log || true)
if [ -z "$WROTE_LINE" ]; then
  echo "ERROR: refresher did not produce a WROTE line. See /tmp/refresh_output.log"
  exit 2
fi
echo "Found diagnostic: $WROTE_LINE"

# extract path (second token), e.g. WROTE /path size=... sha256=...
COOKIES_PATH=$(echo "$WROTE_LINE" | awk '{print $2}')
if [ ! -f "$COOKIES_PATH" ]; then
  echo "ERROR: cookies file not found at $COOKIES_PATH"
  exit 3
fi

echo "Cookies written to: $COOKIES_PATH"

if [ -n "$CANARY" ]; then
  echo "Running yt-dlp canary against $CANARY using cookies $COOKIES_PATH"
  "$YT_DLP_PATH" --cookies "$COOKIES_PATH" --no-warnings --skip-download --dump-json "$CANARY" 2>&1 | sed -n '$p'
  RC=${PIPESTATUS[0]:-0}
  if [ "$RC" -ne 0 ]; then
    echo "CANARY: yt-dlp returned exit code $RC -- check /tmp/refresh_output.log and yt-dlp output above"
    exit $RC
  else
    echo "CANARY OK"
  fi
fi

echo "Done. Safe diagnostic: $WROTE_LINE"
