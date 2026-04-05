#!/usr/bin/env python3
"""Test different yt-dlp format specifications for YouTube download speed."""

import subprocess
import sys
import time
from pathlib import Path

def test_youtube_format(url, format_spec, format_name):
    """Download a YouTube video with a specific format and measure speed."""
    
    # Use a test directory
    test_dir = Path("data/tmp/format_test")
    test_dir.mkdir(parents=True, exist_ok=True)
    
    output_template = str(test_dir / "%(title)s.%(ext)s")
    
    cmd = [
        "yt-dlp",
        "--format", format_spec,
        "--merge-output-format", "mp4",
        "--output", output_template,
        "--no-playlist",
        "--socket-timeout", "60",
        "--retries", "3",
        "--no-warnings",
        url,
    ]
    
    print(f"\n{'='*60}")
    print(f"Testing format: {format_name}")
    print(f"Format spec: {format_spec}")
    print(f"Command: {' '.join(cmd[:3])}... --format {format_spec} ...")
    print(f"{'='*60}")
    
    start_time = time.time()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        elapsed = time.time() - start_time
        
        if result.returncode != 0:
            print(f"❌ ERROR: {result.stderr}")
            return None
        
        # Find the downloaded file
        downloaded_files = list(test_dir.glob("*.mp4"))
        if not downloaded_files:
            print("❌ No MP4 file found after download")
            return None
        
        filepath = downloaded_files[-1]  # Get most recent
        size_mb = filepath.stat().st_size / (1024 * 1024)
        speed_mbps = size_mb / elapsed
        
        print("✅ SUCCESS!")
        print(f"  File: {filepath.name}")
        print(f"  Size: {size_mb:.1f} MB")
        print(f"  Time: {elapsed:.1f}s")
        print(f"  Speed: {speed_mbps:.1f} MB/s")
        
        # Clean up
        filepath.unlink()
        
        return {
            "format_name": format_name,
            "format_spec": format_spec,
            "size_mb": size_mb,
            "time_s": elapsed,
            "speed_mbps": speed_mbps,
        }
        
    except subprocess.TimeoutExpired:
        print("❌ TIMEOUT: Download took too long")
        return None
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_youtube_formats.py <youtube_url>")
        sys.exit(1)
    
    url = sys.argv[1]
    
    # Test different format specifications
    formats = [
        ("best[ext=mp4]/best", "Single-stream (non-DASH)"),
        ("bestvideo[height<=1080]+bestaudio/best", "DASH 1080p max"),
        ("bestvideo[height<=720]+bestaudio/best", "DASH 720p max"),
        ("best", "Best (auto format)"),
    ]
    
    results = []
    for format_spec, format_name in formats:
        result = test_youtube_format(url, format_spec, format_name)
        if result:
            results.append(result)
    
    # Summary
    if results:
        print(f"\n{'='*60}")
        print("SUMMARY")
        print(f"{'='*60}")
        for r in results:
            print(f"{r['format_name']:30} | {r['speed_mbps']:6.1f} MB/s | {r['time_s']:6.1f}s")
        
        fastest = max(results, key=lambda x: x['speed_mbps'])
        print(f"\n🏆 Fastest: {fastest['format_name']} ({fastest['speed_mbps']:.1f} MB/s)")

if __name__ == "__main__":
    main()
