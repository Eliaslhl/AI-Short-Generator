#!/usr/bin/env python3
"""Benchmark two-pass transcription vs single-pass.

For up to N videos (default 3), extract a short sample (30s) and run:
 - single-pass: transcribe_video (uses settings.whisper_model, default 'base')
 - two-pass: transcribe_two_pass (tiny -> base)

Prints timings, number of segments, and a small text comparison for the first few segments.
"""

import os
import sys
import argparse
import time
import tempfile
import json
from pathlib import Path
import difflib

# Ensure repo root on sys.path so we can import backend.* modules when run as a script
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# The backend modules are imported lazily inside functions after ensuring
# the repo root is on sys.path (avoids lint warnings about imports not at top).


def sample_videos(max_items=3):
    from backend.config import settings

    vd = Path(settings.video_dir)
    vids = [
        p
        for p in vd.rglob("*.*")
        if p.suffix.lower() in {".mp4", ".mkv", ".mov", ".webm", ".m4v", ".wav"}
    ]
    return vids[:max_items]


def short_text(seg_list, n=5):
    out = []
    for s in seg_list[:n]:
        text = s.get("text") if isinstance(s, dict) else str(s)
        text = text or ""
        out.append(text.replace("\n", " ")[:200])
    return out


def similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a, b).ratio()


def run_on_sample(video_path: Path, start: float, duration: float):
    print(
        f"\n--- Video: {video_path.name} (sample {start:.1f}-{start+duration:.1f}s) ---"
    )
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_wav = Path(tmp.name)
    from backend.services.youtube_service import extract_audio

    try:
        extract_audio(str(video_path), tmp_wav, start=start, duration=duration)
    except Exception as e:
        print("Failed to extract audio:", e)
        try:
            tmp_wav.unlink()
        except Exception:
            pass
        return None

    results = {"video": video_path.name, "sample_start": start, "sample_dur": duration}

    # Single-pass
    t0 = time.perf_counter()
    from backend.services import transcription_service

    segs_single = transcription_service.transcribe_video(str(tmp_wav), None)
    t1 = time.perf_counter()
    results["single_time"] = t1 - t0
    results["single_n_segments"] = len(segs_single)

    # Two-pass
    t0 = time.perf_counter()
    segs_two = transcription_service.transcribe_two_pass(str(tmp_wav), None)
    t1 = time.perf_counter()
    results["two_pass_time"] = t1 - t0
    results["two_n_segments"] = len(segs_two)

    # Simple comparisons
    single_texts = "\n".join(short_text(segs_single, 10))
    two_texts = "\n".join(short_text(segs_two, 10))

    results["sample_single_excerpt"] = single_texts
    results["sample_two_excerpt"] = two_texts
    results["excerpt_similarity"] = similarity(single_texts, two_texts)

    # print
    print(
        f"single-pass: time={results['single_time']:.2f}s, segments={results['single_n_segments']}"
    )
    print(
        f"two-pass:   time={results['two_pass_time']:.2f}s, segments={results['two_n_segments']}"
    )
    print(f"excerpt similarity (0..1): {results['excerpt_similarity']:.3f}")

    print("\n-- single excerpt --")
    print(single_texts[:1000])
    print("\n-- two-pass excerpt --")
    print(two_texts[:1000])

    try:
        tmp_wav.unlink()
    except Exception:
        pass

    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--max", type=int, default=3, help="Max number of videos to test"
    )
    parser.add_argument(
        "--sample_dur", type=float, default=30.0, help="Sample duration in seconds"
    )
    parser.add_argument(
        "--start_at", type=float, default=10.0, help="Start offset for sample (seconds)"
    )
    parser.add_argument(
        "--out", default=None, help="Optional JSON output file to write results"
    )
    args = parser.parse_args()

    vids = sample_videos(args.max)
    if not vids:
        print(
            "No videos found in settings.video_dir; put test videos there or pass --video"
        )
        return

    all_results = []
    for v in vids:
        res = run_on_sample(v, args.start_at, args.sample_dur)
        if res:
            all_results.append(res)

    if args.out:
        with open(args.out, "w") as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        print("Results written to", args.out)

    print("\nDone.")


if __name__ == "__main__":
    main()
