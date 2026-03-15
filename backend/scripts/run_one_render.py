import time
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.config import settings  # noqa: E402
from backend.video import video_editor  # noqa: E402

VIDEO_DIR = Path(settings.video_dir)

candidates = [
    p
    for p in VIDEO_DIR.rglob("*.*")
    if p.suffix.lower() in {".mp4", ".mkv", ".mov", ".webm", ".m4v"}
]
if not candidates:
    print(f"No videos found in {VIDEO_DIR}")
    sys.exit(1)

video = candidates[0]
start = 10.0
end = min(start + 30.0, 60.0)
out = Path(settings.clips_dir) / "bench" / f"{video.stem}_single.mp4"
out.parent.mkdir(parents=True, exist_ok=True)


def _run_render(video_path: str, start_t: float, end_t: float, out_path: Path):
    """Run the ffmpeg fast-path directly and return result and elapsed time.

    Note: this runs in-process and will block until ffmpeg finishes. Use
    an external watchdog if you need a hard timeout in CI.
    """
    try:
        t0 = time.perf_counter()
        ok = video_editor._render_with_ffmpeg(
            str(video_path),
            start_t,
            end_t,
            out_path,
            "bench hook",
            None,
            "default",
            None,
        )
        t1 = time.perf_counter()
        return {"ok": ok, "time": t1 - t0}
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    res = _run_render(str(video), start, end, out)
    if "error" in res:
        print("Render error:", res["error"])
        sys.exit(1)
    print(f"Render success={res['ok']}, time={res['time']:.2f}s, output={out}")
