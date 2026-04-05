#!/usr/bin/env python3
"""
Test script for YouTube video download (local testing before Railway deployment).
Usage: python test_youtube_download.py <youtube_url>
Example: python test_youtube_download.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
"""

import sys
import time
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.services.youtube_service import download_video

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_youtube_download.py <youtube_url>")
        print("Example: python test_youtube_download.py 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'")
        sys.exit(1)
    
    youtube_url = sys.argv[1]
    job_id = "test_yt_" + str(int(time.time()))
    
    print(f"🎬 Testing YouTube download: {youtube_url}")
    print(f"   Job ID: {job_id}")
    print()
    
    try:
        start = time.time()
        print("⏳ Downloading...")
        video_path, title = download_video(youtube_url, job_id)
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
