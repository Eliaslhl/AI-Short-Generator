"""Regenerate WebP thumbnails for existing clips.

Usage:
    python scripts/regen_thumbnails.py [--dir data/clips]

This will scan each job folder under the clips directory and create a
<clipname>.webp thumbnail next to each MP4 if the WebP does not already exist.
"""

import argparse
from pathlib import Path
import subprocess
import sys


def make_thumbnail(mp4_path: Path, webp_path: Path) -> bool:
    try:
        # choose a frame around the middle
        # use the same ffmpeg args as the server helper
        # compression_level 6, q:v 60 as defaults
        cmd = [
            "ffmpeg",
            "-y",
            "-ss",
            "1",
            "-i",
            str(mp4_path),
            "-vframes",
            "1",
            "-vf",
            "scale=360:-1:flags=lanczos",
            "-compression_level",
            "6",
            "-q:v",
            "60",
            str(webp_path),
        ]
        subprocess.run(cmd, check=True)
        print(f"Created: {webp_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to create thumbnail for {mp4_path}: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", default="data/clips", help="Clips root directory")
    args = parser.parse_args()

    root = Path(args.dir)
    if not root.exists():
        print(f"Clips directory not found: {root}")
        sys.exit(1)

    for job_dir in root.iterdir():
        if not job_dir.is_dir():
            continue
        for mp4 in job_dir.glob("*.mp4"):
            webp = mp4.with_suffix(".webp")
            if webp.exists():
                continue
            make_thumbnail(mp4, webp)

    print("Done")
