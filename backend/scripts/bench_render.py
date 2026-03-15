"""
bench_render.py

Script de benchmarking pour comparer le rendu ffmpeg (fast-path) vs MoviePy
pour un petit échantillon (jusqu'à 3 vidéos) et mesurer :
 - temps total de rendu
 - temps jusqu'au premier clip écrit
 - utilisation CPU (moyenne pendant le rendu)
 - si disponible, lecture simple d'utilisation GPU via nvidia-smi

Usage:
  python3 backend/scripts/bench_render.py

Le script cherche les fichiers vidéo dans `settings.video_dir` et prend
jusqu'à 3 fichiers .mp4/.mkv/.mov.

Note: exécutez ce script depuis la racine du repo (il fait des imports relatifs
vers `backend.video.video_editor`).
"""

import time
import threading
import shutil
import os
import sys
from pathlib import Path
from statistics import mean

# Attempt to import project modules
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

try:
    from backend.config import settings
    from backend.video import video_editor
except Exception as e:
    print("Erreur d'import des modules du projet:", e)
    raise

# Optional psutil for CPU sampling
try:
    import psutil  # type: ignore
except Exception:
    psutil = None

# Optional ffprobe via ffmpeg to get duration if MoviePy not desired

VIDEO_DIR = Path(settings.video_dir)
OUT_DIR = Path(settings.clips_dir) / "bench"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# find candidate videos
candidates = [p for p in VIDEO_DIR.rglob("*.*") if p.suffix.lower() in {".mp4", ".mkv", ".mov", ".webm", ".m4v"}]
if not candidates:
    print(f"Aucune vidéo trouvée dans {VIDEO_DIR}. Placez des vidéos de test et relancez.")
    sys.exit(1)

videos = candidates[:3]
print(f"Found {len(videos)} test videos:")
for v in videos:
    print(" -", v)

SAMPLE_DURATION = 30.0  # seconds to render for each clip (adjustable)

# CPU sampler thread
class Sampler(threading.Thread):
    def __init__(self, interval=0.5):
        super().__init__()
        self.interval = interval
        self.samples = []
        self._stop = threading.Event()

    def run(self):
        while not self._stop.is_set():
            if psutil:
                try:
                    self.samples.append(psutil.cpu_percent(interval=None))
                except Exception:
                    pass
            time.sleep(self.interval)

    def stop(self):
        self._stop.set()

    def mean(self):
        return mean(self.samples) if self.samples else 0.0

# GPU util quick probe via nvidia-smi (optional)
def gpu_util_probe():
    if shutil.which("nvidia-smi"):
        try:
            out = os.popen("nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits").read()
            vals = [int(x.strip()) for x in out.splitlines() if x.strip().isdigit()]
            return vals
        except Exception:
            return None
    return None

results = []

for video in videos:
    # Determine a segment: start at 10s or 0 if shorter
    try:
        # quick probe duration via ffprobe
        import subprocess
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(video)]
        p = subprocess.run(cmd, capture_output=True, text=True)
        dur = float(p.stdout.strip()) if p.stdout.strip() else SAMPLE_DURATION
    except Exception:
        dur = SAMPLE_DURATION

    start = 10.0 if dur > (SAMPLE_DURATION + 20) else 0.0
    end = min(dur, start + SAMPLE_DURATION)
    seg_dur = end - start

    print(f"\n=== Benchmarking {video.name} (segment {start:.1f}-{end:.1f}s, duration {seg_dur:.1f}s) ===")

    # Common metadata
    hook = "Test hook for benchmarking"
    captions = [{"start": start + 2.0, "end": start + 4.0, "text": "Hello world"}]

    # 1) ffmpeg fast-path (call _render_with_ffmpeg directly). To avoid
    # filter_complex quoting issues we skip burning subtitles in this
    # simple benchmark run (captions handled separately when needed).
    out_ff = OUT_DIR / f"{video.stem}_ffmpeg.mp4"
    # clean
    try:
        out_ff.unlink()
    except Exception:
        pass

    sampler = Sampler()
    sampler.start()
    t0 = time.perf_counter()
    start_write_time = None
    try:
        # watch filesystem for output file existence (best-effort)
        wrote_event = threading.Event()

        def watch_file(path, event):
            for _ in range(600):
                if path.exists():
                    event.set()
                    return
                time.sleep(0.1)

        watcher = threading.Thread(target=watch_file, args=(out_ff, wrote_event))
        watcher.start()

        ok = video_editor._render_with_ffmpeg(str(video), start, end, out_ff, hook, None, "default", None)
        t1 = time.perf_counter()
        if wrote_event.is_set():
            start_write_time = None  # can't get precise without more instrumentation
    except Exception as e:
        print("ffmpeg render exception:", e)
        ok = False
        t1 = time.perf_counter()
    finally:
        sampler.stop()
        sampler.join()

    ff_time = t1 - t0
    ff_cpu = sampler.mean() if psutil else None
    ff_gpu = gpu_util_probe()
    print(f"ffmpeg: success={ok}, time={ff_time:.2f}s, cpu_avg={ff_cpu}, gpu_samples={ff_gpu}")

    # 2) MoviePy path: force fallback by monkeypatching _render_with_ffmpeg to return False
    # If moviepy is not installed, skip this step.
    import importlib.util
    have_moviepy = importlib.util.find_spec("moviepy") is not None

    if not have_moviepy:
        print("MoviePy not installed in this environment — skipping MoviePy benchmark")
        ok2 = False
        mp_time = 0.0
        mp_cpu = None
        mp_gpu = None
    else:
        out_mp = OUT_DIR / f"{video.stem}_moviepy.mp4"
        try:
            out_mp.unlink()
        except Exception:
            pass

        original = getattr(video_editor, "_render_with_ffmpeg", None)
        # force fallback
        setattr(video_editor, "_render_with_ffmpeg", lambda *a, **k: False)

        sampler2 = Sampler()
        sampler2.start()
        t0 = time.perf_counter()
        try:
            meta = video_editor.render_clip(str(video), {"start": start, "end": end, "text": "bench", "captions": captions}, job_id="bench", clip_index=0)
            ok2 = True
        except Exception as e:
            print("MoviePy render exception:", e)
            ok2 = False
        t1 = time.perf_counter()
        sampler2.stop()
        sampler2.join()

        mp_time = t1 - t0
        mp_cpu = sampler2.mean() if psutil else None
        mp_gpu = gpu_util_probe()
        print(f"moviepy: success={ok2}, time={mp_time:.2f}s, cpu_avg={mp_cpu}, gpu_samples={mp_gpu}")

        # restore
        if original is not None:
            setattr(video_editor, "_render_with_ffmpeg", original)

    results.append({
        "video": video.name,
        "ffmpeg_time": ff_time,
        "ffmpeg_cpu": ff_cpu,
        "ffmpeg_gpu": ff_gpu,
        "moviepy_time": mp_time,
        "moviepy_cpu": mp_cpu,
        "moviepy_gpu": mp_gpu,
    })

# Print summary
print("\n=== Summary ===")
print(f"Output files in: {OUT_DIR}")
for r in results:
    print(f"\nVideo: {r['video']}")
    print(f" ffmpeg -> time: {r['ffmpeg_time']:.2f}s, cpu_avg: {r['ffmpeg_cpu']}, gpu_samples: {r['ffmpeg_gpu']}")
    print(f" MoviePy -> time: {r['moviepy_time']:.2f}s, cpu_avg: {r['moviepy_cpu']}, gpu_samples: {r['moviepy_gpu']}")

print("\nBench finished.")
