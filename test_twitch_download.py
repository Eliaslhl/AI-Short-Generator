#!/usr/bin/env python3
"""
Test script for Twitch video download (local testing before Railway deployment).
Usage: python test_twitch_download.py <twitch_url>
Example: python test_twitch_download.py "https://www.twitch.tv/videos/1234567890"
"""

import sys
import time
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.services.twitch_service import download_video

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_twitch_download.py <twitch_url>")
        print("Example: python test_twitch_download.py 'https://www.twitch.tv/videos/1234567890'")
        sys.exit(1)
    
    twitch_url = sys.argv[1]
    job_id = "test_" + str(int(time.time()))
    
    print(f"🎬 Testing Twitch download: {twitch_url}")
    print(f"   Job ID: {job_id}")
    print()
    
    try:
        start = time.time()
        print("⏳ Downloading...")
        video_path, title = download_video(twitch_url, job_id)
        elapsed = time.time() - start
        
        file_size = video_path.stat().st_size / (1024 * 1024)
        speed = file_size / elapsed if elapsed > 0 else 0
        
        print()
        print("✅ SUCCESS!")
        print(f"   Video: {video_path}")
        print(f"   Title: {title}")
        print(f"   Size: {file_size:.1f} MB")
        print(f"   Time: {elapsed:.1f}s")
        print(f"   Speed: {speed:.1f} MB/s")
        
    except Exception as e:
        print()
        print(f"❌ FAILED: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
