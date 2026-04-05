#!/usr/bin/env python3
"""Test YouTube download using the actual backend youtube_service function with aria2c."""

import sys
import time
import logging
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.services.youtube_service import download_video

# Set up logging to see DEBUG messages
logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')

def test_with_actual_service(url):
    """Download using the actual backend service."""
    
    print("\n" + "="*60)
    print("Testing with ACTUAL backend youtube_service.download_video()")
    print(f"URL: {url}")
    print("="*60 + "\n")
    
    job_id = "test_youtube_service"
    start_time = time.time()
    try:
        filepath, title = download_video(url, job_id, audio_only=False)
        elapsed = time.time() - start_time
        
        if filepath and filepath.exists():
            size_mb = filepath.stat().st_size / (1024 * 1024)
            speed_mbps = size_mb / elapsed
            
            print("✅ SUCCESS!")
            print(f"  File: {filepath.name}")
            print(f"  Title: {title}")
            print(f"  Size: {size_mb:.1f} MB")
            print(f"  Time: {elapsed:.1f}s")
            print(f"  Speed: {speed_mbps:.1f} MB/s")
            
            # Compare with previous baseline
            print("\n📊 Comparison:")
            print("  Previous test (4.4 MB/s): 79.0s for 345.3 MB")
            print(f"  Current test ({speed_mbps:.1f} MB/s): {elapsed:.1f}s for {size_mb:.1f} MB")
            if speed_mbps > 4.4:
                improvement = ((speed_mbps - 4.4) / 4.4) * 100
                print(f"  ✅ Improvement: +{improvement:.1f}%")
            
        else:
            print(f"❌ Download failed or file not found: {filepath}")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_youtube_service.py <youtube_url>")
        sys.exit(1)
    
    url = sys.argv[1]
    test_with_actual_service(url)
