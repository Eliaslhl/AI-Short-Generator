"""
parallel_render.py

Lance le rendu de plusieurs clips en parallèle en utilisant le fast-path
ffmpeg (_render_with_ffmpeg) de `backend.video.video_editor`.

Usage:
  python3 backend/scripts/parallel_render.py --video <path> --workers 4 --segments 4

Par défaut, découpe la vidéo en N segments consécutifs et lance N jobs
concurrents. Mesure le temps par clip et le temps total.
"""

import argparse
import time
from pathlib import Path
import concurrent.futures
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# backend imports are done lazily inside functions to avoid linter issues


def make_segments(video_path: Path, n: int):
    """Découpe la vidéo en n segments égaux (temps) — retourne list of (start,end)."""
    import subprocess

    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(video_path),
    ]
    p = subprocess.run(cmd, capture_output=True, text=True)
    dur = float(p.stdout.strip()) if p.stdout and p.stdout.strip() else 0.0
    if dur <= 0:
        raise RuntimeError("Could not determine video duration")
    seg_len = dur / n
    segs = []
    for i in range(n):
        start = i * seg_len
        end = min(dur, (i + 1) * seg_len)
        segs.append((start, end))
    return segs


def render_one(args):
    video_path, start, end, out_path, idx = args
    t0 = time.perf_counter()
    # import here to ensure sys.path is configured
    from backend.video import video_editor

    ok = video_editor._render_with_ffmpeg(
        str(video_path), start, end, out_path, "", None, "default", None
    )
    t1 = time.perf_counter()
    return (idx, ok, t1 - t0, str(out_path))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--video",
        required=False,
        help="Path to video. If omitted, takes first video from settings.video_dir",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Number of parallel workers (overrides config)",
    )
    parser.add_argument("--segments", type=int, default=4)
    args = parser.parse_args()

    if args.video:
        video = Path(args.video)
    else:
        # pick first video in settings.video_dir
        from backend.config import settings

        vd = Path(settings.video_dir)
        vids = [
            p
            for p in vd.rglob("*.*")
            if p.suffix.lower() in {".mp4", ".mkv", ".mov", ".webm", ".m4v"}
        ]
        if not vids:
            print(f"Aucune vidéo trouvée dans {vd}")
            return
        video = vids[0]

    print(f"Using video: {video}")
    from backend.config import settings, get_render_workers

    out_dir = Path(settings.clips_dir) / "parallel"
    out_dir.mkdir(parents=True, exist_ok=True)

    segs = make_segments(video, args.segments)

    tasks = []
    for i, (s, e) in enumerate(segs):
        out_path = out_dir / f"{video.stem}_par_{i+1:02d}.mp4"
        tasks.append((video, s, e, out_path, i))

    workers_val = args.workers if args.workers is not None else get_render_workers()
    print(f"Launching {len(tasks)} renders with {workers_val} workers...")
    results = []
    t_start = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers_val) as ex:
        futures = [ex.submit(render_one, t) for t in tasks]
        for fut in concurrent.futures.as_completed(futures):
            try:
                res = fut.result()
                results.append(res)
                idx, ok, dt, path = res
                print(f"Clip {idx+1:02d}: ok={ok}, time={dt:.2f}s -> {path}")
            except Exception as e:
                print("Job failed:", e)
    t_end = time.perf_counter()

    print("\nSummary:")
    for idx, ok, dt, path in sorted(results):
        print(f" - clip {idx+1:02d}: ok={ok}, time={dt:.2f}s")
    print(f"Total wall time: {t_end - t_start:.2f}s")


if __name__ == "__main__":
    main()
