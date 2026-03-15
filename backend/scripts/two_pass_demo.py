#!/usr/bin/env python3
"""Demo runner for the two-pass transcription prototype.

Usage:
  python3 backend/scripts/two_pass_demo.py [--video /path/to/video]

Prints timing and a few segments from the two-pass transcriber.
"""

import os
import sys
import argparse
import time
from pathlib import Path

# Ensure repo root on sys.path so we can import backend.* modules when run as a script
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Import backend modules lazily inside main() to avoid lint warnings when
# running the script directly from the repo root.


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", help="Path to video to transcribe (optional)")
    args = parser.parse_args()

    # Now import backend modules (after sys.path ensured)
    from backend.config import settings
    from backend.services.transcription_service import transcribe_two_pass

    if args.video:
        video = Path(args.video)
    else:
        vd = Path(settings.video_dir)
        vids = [
            p
            for p in vd.rglob("*.*")
            if p.suffix.lower() in {".mp4", ".mkv", ".mov", ".webm", ".m4v"}
        ]
        if not vids:
            print(f"No videos found in {vd}")
            return
        video = vids[0]

    print(f"Running two-pass on {video}")
    t0 = time.perf_counter()
    segs = transcribe_two_pass(str(video))
    t1 = time.perf_counter()
    print(f"Done in {t1-t0:.2f}s — {len(segs)} segments")
    for s in segs[:10]:
        print(f"{s['start']:.2f}-{s['end']:.2f}: {s['text'][:120]!r}")


if __name__ == "__main__":
    main()
