#!/usr/bin/env python3
"""Scale benchmark for parallel rendering.
Runs `parallel_render.py` for different worker counts and samples system metrics using psutil.
Writes results to data/bench/scale_results.json and scale_results.csv
"""
import argparse
import json
import os
import re
import subprocess
import threading
import time
import sys
from pathlib import Path

try:
    import psutil  # type: ignore
except Exception:
    psutil = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Ensure repo root on sys.path so we can import backend.* modules when run as a script
ROOT_PATH = Path(ROOT)
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))
DATA_DIR = os.path.join(ROOT, "data", "bench")
os.makedirs(DATA_DIR, exist_ok=True)

OUTPUT_JSON = os.path.join(DATA_DIR, "scale_results.json")
OUTPUT_CSV = os.path.join(DATA_DIR, "scale_results.csv")

SAMPLE_INTERVAL = 0.2

WALL_TIME_RE = re.compile(r"Total wall time:\s*([0-9.]+)s")


def sample_system(stop_event, samples):
    if psutil is None:
        return
    prev_io = psutil.disk_io_counters() or None
    while not stop_event.is_set():
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory().percent
        now_io = psutil.disk_io_counters() or None
        read_bytes = (getattr(now_io, "read_bytes", 0) - getattr(prev_io, "read_bytes", 0)) if now_io is not None else 0
        write_bytes = (getattr(now_io, "write_bytes", 0) - getattr(prev_io, "write_bytes", 0)) if now_io is not None else 0
        prev_io = now_io or prev_io
        samples.append({
            "ts": time.time(),
            "cpu": cpu,
            "mem": mem,
            "read_bytes": read_bytes,
            "write_bytes": write_bytes,
        })
        time.sleep(SAMPLE_INTERVAL)


def run_one(workers, segments, video, timeout=None):
    cmd = ["python3", os.path.join("backend", "scripts", "parallel_render.py"), "--workers", str(workers), "--segments", str(segments)]
    if video:
        cmd += ["--video", video]
    print("Running:", " ".join(cmd))
    start = time.time()
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    samples = []
    stop_event = threading.Event()
    sampler = None
    if psutil is not None:
        sampler = threading.Thread(target=sample_system, args=(stop_event, samples), daemon=True)
        sampler.start()

    stdout_lines = []
    try:
        if proc.stdout is not None:
            for line in proc.stdout:
                print(line, end="")
                stdout_lines.append(line)
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        raise
    finally:
        if sampler:
            stop_event.set()
            sampler.join(timeout=1.0)

    end = time.time()
    duration = end - start

    # parse wall time from stdout if present
    wall_time = None
    for ln in stdout_lines[::-1]:
        m = WALL_TIME_RE.search(ln)
        if m:
            try:
                wall_time = float(m.group(1))
                break
            except Exception:
                pass

    # compute stats
    stats = {
        "workers": workers,
        "segments": segments,
        "duration_secs": duration,
        "wall_time_reported_secs": wall_time,
        "timestamp": start,
        "samples_count": len(samples),
    }
    if samples:
        cpus = [s["cpu"] for s in samples]
        mems = [s["mem"] for s in samples]
        read_total = sum(s["read_bytes"] for s in samples)
        write_total = sum(s["write_bytes"] for s in samples)
        stats.update(
            {
                "cpu_avg": sum(cpus) / len(cpus),
                "cpu_max": max(cpus),
                "mem_avg": sum(mems) / len(mems),
                "mem_max": max(mems),
                "read_bytes": read_total,
                "write_bytes": write_total,
            }
        )
    return stats


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers-list", default="1,2,4,8", help="Comma-separated worker counts to test")
    parser.add_argument("--segments", type=int, default=4, help="Segments per run")
    parser.add_argument("--repeat", type=int, default=2, help="Repeat each setting N times")
    parser.add_argument("--video", default=None, help="Optional video path to use (first video otherwise)")
    parser.add_argument("--use-config-default", action="store_true", help="Run a single benchmark using the config default render_workers value")
    args = parser.parse_args()

    if psutil is None:
        print("psutil not available; aborting. Please install psutil and re-run.")
        return

    workers_list = [int(x) for x in args.workers_list.split(",") if x.strip()]
    if args.use_config_default:
        try:
            from backend.config import get_render_workers
            workers_list = [get_render_workers()]
            print(f"Using config default render_workers={workers_list[0]}")
        except Exception as e:
            print("Could not import get_render_workers from config:", e)

    results = []
    for workers in workers_list:
        for i in range(args.repeat):
            print(f"\n=== Run workers={workers} repeat={i+1}/{args.repeat} ===")
            try:
                stats = run_one(workers, args.segments, args.video)
                results.append(stats)
            except Exception as e:
                print("Run failed:", e)
                results.append({"workers": workers, "error": str(e)})

    # save JSON
    with open(OUTPUT_JSON, "w") as f:
        json.dump(results, f, indent=2)

    # save CSV
    csv_lines = ["workers,segments,duration_secs,wall_time_reported_secs,cpu_avg,cpu_max,mem_avg,mem_max,read_bytes,write_bytes,samples_count"]
    for r in results:
        if "error" in r:
            continue
        csv_lines.append(
            ",".join(
                str(r.get(k, ""))
                for k in [
                    "workers",
                    "segments",
                    "duration_secs",
                    "wall_time_reported_secs",
                    "cpu_avg",
                    "cpu_max",
                    "mem_avg",
                    "mem_max",
                    "read_bytes",
                    "write_bytes",
                    "samples_count",
                ]
            )
        )
    with open(OUTPUT_CSV, "w") as f:
        f.write("\n".join(csv_lines))

    print("\nResults written:", OUTPUT_JSON, OUTPUT_CSV)


if __name__ == "__main__":
    main()
