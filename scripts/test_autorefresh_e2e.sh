#!/usr/bin/env bash
set -euo pipefail
# Simulate the auto-refresh-and-retry flow for testing purposes.
# This script demonstrates what happens when yt-dlp fails with "Sign in..."
# and the backend auto-refreshes cookies then retries.

REPO_ROOT="$(cd "$(dirname "$0")" && cd .. && pwd)"
cd "$REPO_ROOT"

echo "═══════════════════════════════════════════════════════════════"
echo "Testing Auto-Refresh-and-Retry Flow"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Check prerequisites
if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 not found"
    exit 1
fi

if ! command -v yt-dlp &> /dev/null; then
    echo "ERROR: yt-dlp not found. Install with: pip install yt-dlp"
    exit 1
fi

# Load env if present
if [ -f "scripts/refresh.env" ]; then
    echo "Loading scripts/refresh.env..."
    source scripts/refresh.env
else
    echo "Note: scripts/refresh.env not found. Using defaults."
fi

# Defaults
PROFILE="${YOUTUBE_BROWSER_PROFILE_DIR:-}"
OUT_PATH="${YOUTUBE_AUTO_REFRESH_OUT:-/tmp/yt_cookies_autorefresh.txt}"
CANARY="${YOUTUBE_AUTO_REFRESH_CANARY:-https://www.youtube.com/watch?v=recHgNtlUjc}"
HEADLESS="${YOUTUBE_AUTO_REFRESH_HEADLESS:-true}"

echo ""
echo "Configuration:"
echo "  PROFILE: ${PROFILE:-(none, ephemeral)}"
echo "  OUT_PATH: $OUT_PATH"
echo "  CANARY: $CANARY"
echo "  HEADLESS: $HEADLESS"
echo ""

# Step 1: Validation tests
echo "Step 1: Validation tests"
echo "─────────────────────────────────────────────────────────────────"
python3 scripts/test_autorefresh_logic.py || {
    echo "Validation failed. Cannot proceed."
    exit 1
}
echo ""

# Step 2: Run the refresher
echo "Step 2: Running the refresher"
echo "─────────────────────────────────────────────────────────────────"
REFRESH_ARGS=("--out" "$OUT_PATH")

if [ -n "$PROFILE" ]; then
    REFRESH_ARGS+=("--profile" "$PROFILE")
fi

if [ "$HEADLESS" = "true" ] || [ "$HEADLESS" = "1" ]; then
    REFRESH_ARGS+=("--headless")
fi

# Note: not including canary in the refresher step; we'll test separately
echo "Running: python3 scripts/refresh_youtube_cookies.py ${REFRESH_ARGS[*]}"
echo ""

if ! python3 -u scripts/refresh_youtube_cookies.py "${REFRESH_ARGS[@]}" 2>&1 | tee /tmp/refresh_test_out.log; then
    echo ""
    echo "ERROR: Refresher failed. See /tmp/refresh_test_out.log for details."
    exit 1
fi

echo ""

# Step 3: Parse the WROTE line
echo "Step 3: Verifying WROTE diagnostic line"
echo "─────────────────────────────────────────────────────────────────"
WROTE_LINE=$(grep -m1 '^WROTE ' /tmp/refresh_test_out.log || echo "")
if [ -z "$WROTE_LINE" ]; then
    echo "ERROR: No WROTE line found in refresher output."
    exit 1
fi

echo "Found: $WROTE_LINE"
COOKIES_FILE=$(echo "$WROTE_LINE" | awk '{print $2}')
echo "Cookies file: $COOKIES_FILE"

if [ ! -f "$COOKIES_FILE" ]; then
    echo "ERROR: Cookies file not found at $COOKIES_FILE"
    exit 1
fi

echo ""

# Step 4: Test cookies with yt-dlp (simulating the "retry" step)
echo "Step 4: Testing cookies with yt-dlp (retry step)"
echo "─────────────────────────────────────────────────────────────────"
echo "Testing canary: $CANARY"
echo ""

if yt-dlp --cookies "$COOKIES_FILE" \
          --no-warnings --skip-download --dump-json "$CANARY" 2>&1 | \
    python3 -c "import sys, json; data=json.load(sys.stdin); print(f'✓ Title: {data.get(\"title\", \"N/A\")}'); print(f'  Duration: {data.get(\"duration\", \"N/A\")}s'); print(f'  View count: {data.get(\"view_count\", \"N/A\")}')" 2>/dev/null
then
    echo ""
    echo "✓ Canary test PASSED — cookies work!"
else
    echo ""
    echo "✗ Canary test FAILED — cookies might be invalid or expired."
    exit 1
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "✓ Auto-refresh-and-retry flow is working correctly!"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Next steps:"
echo "  1. Verify logs show: [YTC AUTOREFRESH] refreshed cookies: ..."
echo "  2. Check that the cookies file is readable by the service."
echo "  3. Deploy with YOUTUBE_ENABLE_AUTO_REFRESH=true in production."
echo ""
