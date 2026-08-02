"""
benchmark_transcription.py — FAST vs QUALITY transcription benchmark.

Measures whether TranscriptionMode.QUALITY (two-pass refine) is worth its
extra cost over TranscriptionMode.FAST (single tiny-model pass), on a
reproducible, synthetic local corpus: audio synthesized at run time from the
OS text-to-speech engine, against a known reference transcript. No private,
licensed, or otherwise real media is ever read from or written into the
repository — the corpus and the report are regenerated on every run and, by
default, live entirely in a temporary directory.

Metrics per (sample, mode): audio duration, wall time, isolated CPU time,
isolated peak RSS, word error rate against the known reference text, detected
language vs. expected language, segment/timestamp stability across two
independent runs of the same (sample, mode) pair, and a rough production-cost
extrapolation from measured CPU time (a documented, adjustable assumption,
not a guarantee).

Usage (run from the repository root):
    PYTHONPATH=. .venv/bin/python backend/scripts/benchmark_transcription.py
    PYTHONPATH=. .venv/bin/python backend/scripts/benchmark_transcription.py --json-out report.json
    PYTHONPATH=. .venv/bin/python backend/scripts/benchmark_transcription.py --corpus-dir my_corpus/

Corpus synthesis requires the macOS `say` command. On a platform without it,
pass --corpus-dir pointing at a local (not committed) directory containing
"<id>.wav" + "<id>.txt" (reference transcript) + "<id>.lang" (expected
ISO-639-1 code) triples.

Each transcription call runs in its own forked child process so its CPU time
and peak memory can be measured in isolation via os.wait4(), instead of a
single process's monotonically-increasing high-water mark blending every
mode and sample together.
"""

import argparse
import json
import os
import statistics
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


# ── Reference corpus: known ground truth, synthesized at run time ──────────

CORPUS = [
    {
        "id": "en-01",
        "language": "en",
        "voice": "Samantha",
        "text": (
            "The quick brown fox jumps over the lazy dog. Video creators often "
            "need to turn one long recording into several short clips. Choosing "
            "the right highlight is not always obvious, especially when the "
            "audio quality varies throughout the stream."
        ),
    },
    {
        "id": "en-02",
        "language": "en",
        "voice": "Samantha",
        "text": (
            "Artificial intelligence can help detect the most engaging moments "
            "in a video by analyzing both the motion on screen and the energy "
            "in the soundtrack. A good transcription is essential to generate "
            "accurate subtitles and searchable titles."
        ),
    },
    {
        "id": "fr-01",
        "language": "fr",
        "voice": "Amelie",
        "text": (
            "Le renard brun rapide saute par dessus le chien paresseux. Les "
            "createurs de videos ont souvent besoin de transformer un long "
            "enregistrement en plusieurs extraits courts et autonomes."
        ),
    },
    {
        "id": "fr-02",
        "language": "fr",
        "voice": "Amelie",
        "text": (
            "L'intelligence artificielle peut aider a reperer les moments les "
            "plus interessants d'une video en analysant a la fois le mouvement "
            "a l'ecran et l'energie de la bande sonore."
        ),
    },
    # Noisy samples: clean TTS audio degrades faster-whisper's confidence
    # well below two_pass_conf_threshold (0.70), which is what actually
    # exercises the QUALITY refine path — clean speech never triggers it.
    {
        "id": "en-03-noisy-short",
        "language": "en",
        "voice": "Samantha",
        "noise_db": 0,
        "text": (
            "Artificial intelligence can help detect the most engaging moments "
            "in a video by analyzing both the motion on screen and the energy "
            "in the soundtrack."
        ),
    },
    {
        "id": "en-04-noisy-long",
        "language": "en",
        "voice": "Samantha",
        "noise_db": 0,
        "text": " ".join(
            [
                "The quick brown fox jumps over the lazy dog.",
                "Video creators often need to turn one long recording into several short clips.",
                "Choosing the right highlight is not always obvious, especially when the audio "
                "quality varies throughout the stream.",
                "Artificial intelligence can help detect the most engaging moments in a video by "
                "analyzing both the motion on screen and the energy in the soundtrack.",
                "A good transcription is essential to generate accurate subtitles and searchable "
                "titles.",
                "Background noise, overlapping speakers, and low bitrate audio all make automatic "
                "transcription considerably harder in practice.",
                "This longer sample exists specifically to check whether the refine budget, which "
                "is capped as a fraction of total audio duration, behaves differently once there "
                "is more room for it to work with.",
            ]
        ),
    },
]

MODES = ["fast", "quality"]
RUNS_PER_MODE = 2  # second run only used to measure timestamp/text stability


# ── Corpus synthesis (macOS `say`, never written into the repo) ────────────

def synthesize_corpus(out_dir: Path) -> list[dict]:
    samples = []
    for item in CORPUS:
        aiff_path = out_dir / f"{item['id']}.aiff"
        wav_path = out_dir / f"{item['id']}.wav"
        subprocess.run(
            ["say", "-v", item["voice"], "-o", str(aiff_path), item["text"]],
            check=True,
            capture_output=True,
        )
        noise_db = item.get("noise_db")
        if noise_db is None:
            subprocess.run(
                [
                    "ffmpeg", "-v", "error", "-y",
                    "-i", str(aiff_path),
                    "-ac", "1", "-ar", "16000",
                    str(wav_path),
                ],
                check=True,
                capture_output=True,
            )
        else:
            # Mix in pink noise to push faster-whisper's average word
            # confidence below two_pass_conf_threshold — clean TTS speech
            # never triggers the QUALITY refine path at all.
            subprocess.run(
                [
                    "ffmpeg", "-v", "error", "-y",
                    "-i", str(aiff_path),
                    "-f", "lavfi", "-i", "anoisesrc=color=pink:amplitude=1",
                    "-filter_complex",
                    f"[1:a]volume={noise_db}dB[n];"
                    "[0:a][n]amix=inputs=2:duration=first:dropout_transition=0",
                    "-ac", "1", "-ar", "16000",
                    str(wav_path),
                ],
                check=True,
                capture_output=True,
            )
        aiff_path.unlink(missing_ok=True)
        samples.append({**item, "audio_path": str(wav_path)})
    return samples


def load_corpus_dir(corpus_dir: Path) -> list[dict]:
    samples = []
    for txt_path in sorted(corpus_dir.glob("*.txt")):
        sample_id = txt_path.stem
        wav_path = corpus_dir / f"{sample_id}.wav"
        lang_path = corpus_dir / f"{sample_id}.lang"
        if not wav_path.is_file():
            print(f"skip {sample_id}: no matching .wav", file=sys.stderr)
            continue
        samples.append({
            "id": sample_id,
            "language": lang_path.read_text().strip() if lang_path.is_file() else "",
            "text": txt_path.read_text().strip(),
            "audio_path": str(wav_path),
        })
    return samples


# ── Word Error Rate (Levenshtein over words; no external dependency) ───────

def _normalize_words(text: str) -> list[str]:
    cleaned = "".join(c.lower() if c.isalnum() or c.isspace() else " " for c in text)
    return cleaned.split()


def word_error_rate(reference: str, hypothesis: str) -> float:
    ref = _normalize_words(reference)
    hyp = _normalize_words(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0
    dp = list(range(len(hyp) + 1))
    for i in range(1, len(ref) + 1):
        prev, dp[0] = dp[0], i
        for j in range(1, len(hyp) + 1):
            cur = dp[j]
            dp[j] = prev if ref[i - 1] == hyp[j - 1] else 1 + min(prev, dp[j], dp[j - 1])
            prev = cur
    return dp[len(hyp)] / len(ref)


# ── ffprobe duration (stdlib subprocess only) ───────────────────────────────

def ffprobe_duration(path: str) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True,
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


# ── Isolated worker: one transcription call, resource-usage measured by the
#    parent via os.wait4() so CPU/RSS numbers are never blended across runs.

def _run_worker(audio_path: str, mode: str, language: Optional[str], out_path: str) -> None:
    from backend.services.transcription_service import transcribe_for_job, TranscriptionMode

    t0 = time.perf_counter()
    segments = transcribe_for_job(
        audio_path,
        transcription_mode=TranscriptionMode.QUALITY if mode == "quality" else TranscriptionMode.FAST,
        language=language,
    )
    wall_time = time.perf_counter() - t0
    detected_language = next(
        (s.get("detected_language") for s in segments if s.get("detected_language")), None
    )
    Path(out_path).write_text(json.dumps({
        "wall_time": wall_time,
        "detected_language": detected_language,
        "num_segments": len(segments),
        "text": " ".join(s["text"] for s in segments),
        "segment_bounds": [[s["start"], s["end"]] for s in segments],
    }))


@dataclass
class RunResult:
    wall_time: float
    cpu_time: float
    peak_rss_mb: float
    detected_language: Optional[str]
    num_segments: int
    text: str
    segment_bounds: list


def run_isolated(audio_path: str, mode: str, language: Optional[str], out_dir: Path) -> RunResult:
    """Run one transcription in a child process; read its exact rusage via os.wait4()."""
    result_path = out_dir / f"result-{os.getpid()}-{time.time_ns()}.json"
    pid = os.fork()
    if pid == 0:
        try:
            _run_worker(audio_path, mode, language, str(result_path))
            os._exit(0)
        except Exception as exc:  # pragma: no cover - child-process crash path
            print(f"worker crashed: {exc}", file=sys.stderr)
            os._exit(1)
    _, status, rusage = os.wait4(pid, 0)
    if os.WEXITSTATUS(status) != 0 or not result_path.is_file():
        raise RuntimeError(f"transcription worker failed for {audio_path} mode={mode}")
    payload = json.loads(result_path.read_text())
    result_path.unlink(missing_ok=True)
    peak_rss_raw = rusage.ru_maxrss
    peak_rss_mb = peak_rss_raw / (1024 * 1024) if sys.platform == "darwin" else peak_rss_raw / 1024
    return RunResult(
        wall_time=payload["wall_time"],
        cpu_time=rusage.ru_utime + rusage.ru_stime,
        peak_rss_mb=peak_rss_mb,
        detected_language=payload["detected_language"],
        num_segments=payload["num_segments"],
        text=payload["text"],
        segment_bounds=payload["segment_bounds"],
    )


# ── Cost extrapolation: a documented, adjustable assumption ────────────────

ASSUMED_USD_PER_VCPU_HOUR = 0.05  # generic general-purpose cloud vCPU; adjust to your provider


def estimate_cost_per_hour_of_video(cpu_time_seconds: float, audio_duration_seconds: float) -> float:
    if audio_duration_seconds <= 0:
        return 0.0
    cpu_seconds_per_hour_of_video = (cpu_time_seconds / audio_duration_seconds) * 3600
    return (cpu_seconds_per_hour_of_video / 3600) * ASSUMED_USD_PER_VCPU_HOUR


# ── Report ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--corpus-dir", type=Path, default=None,
                         help="Use a pre-existing local corpus instead of synthesizing one via `say`.")
    parser.add_argument("--json-out", type=Path, default=None,
                         help="Write the full machine-readable report here (default: temp file only).")
    parser.add_argument("--output-dir", type=Path, default=None,
                         help="Keep the synthesized corpus audio here instead of a temp dir "
                              "(never point this at a path tracked by git).")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="transcription-bench-") as tmp:
        work_dir = args.output_dir or Path(tmp)
        work_dir.mkdir(parents=True, exist_ok=True)

        if args.corpus_dir:
            samples = load_corpus_dir(args.corpus_dir)
        else:
            samples = synthesize_corpus(work_dir)

        if not samples:
            print("No corpus samples available — nothing to benchmark.", file=sys.stderr)
            sys.exit(1)

        report = {"assumed_usd_per_vcpu_hour": ASSUMED_USD_PER_VCPU_HOUR, "samples": []}

        for sample in samples:
            duration = ffprobe_duration(sample["audio_path"])
            sample_report = {
                "id": sample["id"],
                "expected_language": sample["language"],
                "audio_duration_seconds": duration,
                "modes": {},
            }
            for mode in MODES:
                runs = [
                    run_isolated(sample["audio_path"], mode, None, work_dir)
                    for _ in range(RUNS_PER_MODE)
                ]
                wer_values = [word_error_rate(sample["text"], r.text) for r in runs]
                stable = runs[0].segment_bounds == runs[1].segment_bounds
                sample_report["modes"][mode] = {
                    "wall_time_seconds": statistics.mean(r.wall_time for r in runs),
                    "cpu_time_seconds": statistics.mean(r.cpu_time for r in runs),
                    "peak_rss_mb": max(r.peak_rss_mb for r in runs),
                    "word_error_rate": statistics.mean(wer_values),
                    "detected_language": runs[0].detected_language,
                    "language_correct": runs[0].detected_language == sample["language"],
                    "num_segments": runs[0].num_segments,
                    "timestamps_stable_across_runs": stable,
                    "text": runs[0].text,
                    "estimated_usd_per_hour_of_video": estimate_cost_per_hour_of_video(
                        statistics.mean(r.cpu_time for r in runs), duration
                    ),
                }
                print(f"  {sample['id']:>8} {mode:>7}: "
                      f"wall={sample_report['modes'][mode]['wall_time_seconds']:.2f}s "
                      f"cpu={sample_report['modes'][mode]['cpu_time_seconds']:.2f}s "
                      f"wer={sample_report['modes'][mode]['word_error_rate']:.2%} "
                      f"lang={runs[0].detected_language} "
                      f"stable={stable}")
            # QUALITY's refine step only touches windows below
            # two_pass_conf_threshold that also fit the refine-time budget;
            # when it never fires (or changes nothing), FAST and QUALITY
            # produce byte-identical transcripts — this is the direct,
            # reproducible signal that the extra pass had zero effect here.
            sample_report["quality_changed_output"] = (
                sample_report["modes"]["fast"]["text"] != sample_report["modes"]["quality"]["text"]
            )
            report["samples"].append(sample_report)

        _print_summary(report)

        out_path = args.json_out or (work_dir / "transcription_benchmark_report.json")
        out_path.write_text(json.dumps(report, indent=2))
        print(f"\nFull report: {out_path}")


def _print_summary(report: dict) -> None:
    print("\n=== FAST vs QUALITY summary (averaged across corpus) ===")
    for mode in MODES:
        entries = [s["modes"][mode] for s in report["samples"]]
        avg_wall = statistics.mean(e["wall_time_seconds"] for e in entries)
        avg_cpu = statistics.mean(e["cpu_time_seconds"] for e in entries)
        avg_rss = statistics.mean(e["peak_rss_mb"] for e in entries)
        avg_wer = statistics.mean(e["word_error_rate"] for e in entries)
        lang_acc = sum(e["language_correct"] for e in entries) / len(entries)
        avg_cost = statistics.mean(e["estimated_usd_per_hour_of_video"] for e in entries)
        all_stable = all(e["timestamps_stable_across_runs"] for e in entries)
        print(
            f"{mode.upper():>8}: wall={avg_wall:.2f}s cpu={avg_cpu:.2f}s "
            f"peak_rss={avg_rss:.1f}MB wer={avg_wer:.2%} lang_acc={lang_acc:.0%} "
            f"stable={all_stable} est_cost=${avg_cost:.4f}/hour-of-video "
            f"(@ ${ASSUMED_USD_PER_VCPU_HOUR}/vCPU-hour)"
        )
    changed = sum(1 for s in report["samples"] if s["quality_changed_output"])
    print(
        f"\nQUALITY changed the transcript vs. FAST on {changed}/{len(report['samples'])} "
        f"corpus samples (byte-for-byte text comparison)."
    )


if __name__ == "__main__":
    main()
