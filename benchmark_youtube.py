#!/usr/bin/env python3
"""Benchmark YouTube download speeds with different configurations."""

import sys
import time
import logging
from pathlib import Path
import shutil

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.services.youtube_service import download_video

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

def cleanup_test_videos():
    """Clean up test videos directory."""
    test_dir = Path("data/videos/youtube_benchmark")
    if test_dir.exists():
        shutil.rmtree(test_dir)
    test_dir.mkdir(parents=True, exist_ok=True)

def benchmark_download(url, job_id):
    """Download and measure speed."""
    start_time = time.time()
    try:
        filepath, title = download_video(url, job_id, audio_only=False)
        elapsed = time.time() - start_time
        
        if filepath and filepath.exists():
            size_mb = filepath.stat().st_size / (1024 * 1024)
            speed_mbps = size_mb / elapsed
            return {
                "title": title,
                "size_mb": size_mb,
                "time_s": elapsed,
                "speed_mbps": speed_mbps,
                "filepath": filepath,
            }
        else:
            return {"error": f"File not found: {filepath}"}
            
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python benchmark_youtube.py <youtube_url>")
        sys.exit(1)
    
    url = sys.argv[1]
    
    print("\n" + "="*70)
    print("YouTube Download Speed Benchmark with aria2c")
    print("="*70)
    
    cleanup_test_videos()
    
    result = benchmark_download(url, "youtube_benchmark")
    
    if "error" in result:
        print(f"❌ ERROR: {result['error']}")
    else:
        speed = float(result['speed_mbps'])
        print("✅ SUCCESS!")
        print(f"  Video: {result['title']}")
        print(f"  Size: {result['size_mb']:.1f} MB")
        print(f"  Time: {result['time_s']:.1f}s")
        print(f"  Speed: {speed:.1f} MB/s")
        print("\n📊 Performance Summary:")
        print("  Baseline (without aria2c): 4.4 MB/s")
        print(f"  With aria2c: {speed:.1f} MB/s")
        if speed > 4.4:
            improvement = ((speed - 4.4) / 4.4) * 100
            print(f"  ✅ Improvement: +{improvement:.0f}%")
