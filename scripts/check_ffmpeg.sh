#!/bin/bash
# check_ffmpeg.sh – Verify FFmpeg installation and required encoders
# Used to ensure clip_generator.py dependencies are available

set -e

echo "=== FFmpeg Installation Check ==="
echo ""

# Check if FFmpeg is installed
if ! command -v ffmpeg &> /dev/null; then
    echo "❌ FFmpeg is NOT installed"
    echo ""
    echo "Installation instructions:"
    echo "  macOS (Homebrew): brew install ffmpeg"
    echo "  Ubuntu/Debian:    sudo apt-get install ffmpeg"
    echo "  CentOS/RHEL:      sudo yum install ffmpeg"
    echo "  Windows:          Download from https://ffmpeg.org/download.html"
    exit 1
fi

echo "✅ FFmpeg installed"

# Display version
FFMPEG_VERSION=$(ffmpeg -version 2>&1 | head -n1)
echo "   Version: $FFMPEG_VERSION"
echo ""

# Check for required video encoders
echo "=== Checking Required Video Encoders ==="

REQUIRED_ENCODERS=("libx264" "libvpx-vp9" "aac")
MISSING=0

for encoder in "${REQUIRED_ENCODERS[@]}"; do
    if ffmpeg -encoders 2>/dev/null | grep -q "$encoder"; then
        echo "✅ $encoder available"
    else
        echo "❌ $encoder NOT available"
        MISSING=$((MISSING + 1))
    fi
done

echo ""

if [ $MISSING -eq 0 ]; then
    echo "✅ All required encoders are available"
    echo "   The clip_generator.py service should work correctly."
    exit 0
else
    echo "❌ Missing $MISSING required encoder(s)"
    echo "   Install ffmpeg-full or ensure all dependencies are present:"
    echo "   macOS: brew install ffmpeg --with-options"
    exit 1
fi
