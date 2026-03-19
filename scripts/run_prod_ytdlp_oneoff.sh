#!/usr/bin/env bash
# Script to run inside a one-off container (Railway / host) to reconstruct
# YouTube cookies from env parts or fallback file, print size+sha256, run yt-dlp,
# and save logs. Safe to run: script never prints cookie contents.

set -eu

OUT_COOKIE=${OUT_COOKIE:-/tmp/youtube_cookies.txt}
YTDLP_BIN=${YTDLP_BIN:-yt-dlp}
JOB_URL=${1:-${YTDLP_URL:-}}
LOGFILE=${LOGFILE:-/tmp/yt-dlp-oneoff.log}

if [ -z "$JOB_URL" ]; then
  echo "Usage: $0 <youtube_url>   (or set YTDLP_URL env)"
  exit 2
fi

echo "Reconstructing cookies to $OUT_COOKIE..."
python3 scripts/reconstruct_youtube_cookies.py --output "$OUT_COOKIE" --fallback secrets/youtube_cookies.b64

if [ ! -f "$OUT_COOKIE" ]; then
  echo "Cookie file not found after reconstruction. Aborting." >&2
  exit 3
fi

size=$(wc -c < "$OUT_COOKIE" || echo 0)
sha=$(sha256sum "$OUT_COOKIE" 2>/dev/null || shasum -a 256 "$OUT_COOKIE")
echo "WROTE $OUT_COOKIE size= $size sha256= ${sha%% *}"

echo "Running yt-dlp for $JOB_URL (logs -> $LOGFILE)"
# Run yt-dlp and capture both stdout and stderr into logfile, but also stream
# a brief tail to the console so the operator sees progress.
(
  set -o pipefail
  $YTDLP_BIN --cookies "$OUT_COOKIE" --no-warnings --dump-json "$JOB_URL" 2>&1 | tee "$LOGFILE"
) || rc=$?

rc=${rc:-0}
echo "yt-dlp exited with code $rc"
echo "Tail of log file ($LOGFILE):"
tail -n 200 "$LOGFILE" || true

if [ "$rc" -ne 0 ]; then
  echo "yt-dlp failed (exit $rc). Check $LOGFILE for details." >&2
  exit $rc
fi

echo "One-off completed successfully."
