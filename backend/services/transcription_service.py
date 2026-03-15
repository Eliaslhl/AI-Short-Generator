"""
transcription_service.py – Transcribe a video file with Faster-Whisper.

Returns a list of segment dicts:
    {
        "start":    float,   # seconds
        "end":      float,   # seconds
        "text":     str,     # transcribed text
        "words":    list,    # word-level timestamps (if available)
    }
"""

import logging
from pathlib import Path
from typing import List, Dict, Any

from faster_whisper import WhisperModel

from backend.config import settings
import time
import json

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
#  Lazy-loaded model singleton (avoids reloading on every call)
# ──────────────────────────────────────────────
_model: WhisperModel | None = None
_models: dict[str, WhisperModel] = {}


def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        logger.info(
            f"Loading Faster-Whisper model '{settings.whisper_model}' "
            f"on device '{settings.whisper_device}'…"
        )
        _model = WhisperModel(
            settings.whisper_model,
            device=settings.whisper_device,
            compute_type="int8",         # fast & memory-efficient
        )
        logger.info("Whisper model loaded.")
    return _model


def _get_model_by_name(name: str, device: str | None = None, compute_type: str = "int8") -> WhisperModel:
    """Load or reuse a WhisperModel for a specific model name."""
    global _models
    key = f"{name}@{device or settings.whisper_device}:{compute_type}"
    if key in _models:
        return _models[key]
    logger.info(f"Loading Faster-Whisper model '{name}' on device '{device or settings.whisper_device}' (compute={compute_type})…")
    m = WhisperModel(name, device=device or settings.whisper_device, compute_type=compute_type)
    _models[key] = m
    logger.info(f"Model {name} loaded.")
    return m


def _ffprobe_duration(path: str) -> float:
    import subprocess
    try:
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)]
        p = subprocess.run(cmd, capture_output=True, text=True)
        return float(p.stdout.strip()) if p.stdout and p.stdout.strip() else 0.0
    except Exception:
        return 0.0


def _merge_windows(windows, gap=0.5):
    if not windows:
        return []
    ws = sorted(windows, key=lambda x: x[0])
    merged = [list(ws[0])]
    for s, e in ws[1:]:
        if s <= merged[-1][1] + gap:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return [(float(a), float(b)) for a, b in merged]


def transcribe_two_pass(video_path: str, language: str | None = None, job_max_refine_fraction: float | None = None) -> List[Dict[str, Any]]:
    """Two-pass transcription:

    1) Fast pass with tiny model to get coarse segments + per-word probs
    2) Select low-confidence windows and run refine model only on those windows
    3) Stitch refined windows into final segments
    Returns list of segments like transcribe_video.
    """
    from statistics import mean
    import tempfile
    import os
    from backend.services.youtube_service import extract_audio

    path = Path(video_path)
    if not path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    t_start = time.perf_counter()

    lang = language if language else (settings.whisper_language or None)

    # Fast model
    fast_model_name = settings.whisper_fast_model
    refine_model_name = settings.whisper_refine_model
    fast_model = _get_model_by_name(fast_model_name, compute_type="int8")

    logger.info(f"Fast-pass ({fast_model_name}) transcribing {path.name}…")
    fast_iter, info = fast_model.transcribe(
        str(path), language=lang, word_timestamps=True, vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
    )

    fast_segments: List[Dict[str, Any]] = []
    flagged_windows = []  # tuples (start,end,avg_conf)
    for seg in fast_iter:
        words = []
        if seg.words:
            words = [{"word": w.word, "start": w.start, "end": w.end, "prob": getattr(w, 'probability', None)} for w in seg.words]
        avg_conf = None
        probs = [w["prob"] for w in words if w.get("prob") is not None]
        if probs:
            avg_conf = mean(probs)
        else:
            avg_conf = 1.0

        fast_segments.append({"start": seg.start, "end": seg.end, "text": seg.text.strip(), "words": words, "avg_conf": avg_conf})

        if avg_conf < settings.two_pass_conf_threshold:
            flagged_windows.append((seg.start, seg.end, avg_conf))

    total_dur = _ffprobe_duration(str(path)) or 0.0

    # Merge flagged windows and pad
    raw_windows = [(s, e) for s, e, _ in flagged_windows]
    merged = _merge_windows(raw_windows, gap=settings.two_pass_window_overlap)
    padded = []
    for s, e in merged:
        ns = max(0.0, s - settings.two_pass_pad)
        ne = min(total_dur or e + settings.two_pass_pad, e + settings.two_pass_pad)
        padded.append((ns, ne))

    # Limit total refine seconds. Allow a job-level cap to be provided which is
    # applied conservatively (min of global setting and job-level cap). If no
    # job-level cap is given, use the global setting.
    effective_frac = settings.two_pass_max_refine_fraction
    if job_max_refine_fraction is not None:
        # be conservative: don't allow job to raise the global fraction
        effective_frac = min(settings.two_pass_max_refine_fraction, float(job_max_refine_fraction))
        if effective_frac != settings.two_pass_max_refine_fraction:
            logger.info(f"Job-level refine cap applied: job_max_refine_fraction={job_max_refine_fraction} -> effective_frac={effective_frac}")
    max_refine_secs = effective_frac * (total_dur or sum(e - s for s, e in padded))
    # compute importance by lowest avg_conf inside windows
    # Build window importance list
    win_infos = []
    for s, e in padded:
        # average avg_conf of contained fast_segments
        seg_confs = [fs["avg_conf"] for fs in fast_segments if not (fs["end"] < s or fs["start"] > e)]
        avgc = mean(seg_confs) if seg_confs else 1.0
        win_infos.append({"start": s, "end": e, "avg_conf": avgc, "dur": e - s})

    # sort by avg_conf ascending (lowest confidence first)
    win_infos.sort(key=lambda x: x["avg_conf"])
    selected = []
    selected_secs = 0.0
    for w in win_infos:
        if selected_secs + w["dur"] <= max_refine_secs:
            selected.append((w["start"], w["end"]))
            selected_secs += w["dur"]

    logger.info(f"Selected {len(selected)} windows for refine (total {selected_secs:.2f}s) out of {total_dur:.2f}s")

    refined_segments = []
    refine_time = 0.0
    refine_cut = False
    if selected:
        refine_start = time.perf_counter()
        refine_model = _get_model_by_name(refine_model_name, compute_type="int8")
        # process windows in parallel but submit progressively so we can stop when
        # the dynamic cap is exceeded. This prevents unbounded work when many
        # windows are selected.
        from concurrent.futures import ThreadPoolExecutor, as_completed

        def refine_window(args):
            s, e = args
            dur = e - s
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name
            try:
                extract_audio(str(path), tmp_path, start=s, duration=dur)
                segs_iter, _ = refine_model.transcribe(tmp_path, language=lang, word_timestamps=True, vad_filter=False)
                out = []
                for seg in segs_iter:
                    words = []
                    if seg.words:
                        words = [{"word": w.word, "start": s + w.start, "end": s + w.end, "prob": getattr(w, 'probability', None)} for w in seg.words]
                    out.append({"start": s + seg.start, "end": s + seg.end, "text": seg.text.strip(), "words": words})
                return out
            finally:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
    cap_seconds = float(settings.two_pass_dynamic_cap_seconds)  # dynamic cap in seconds (abort refine if exceeded)
    max_workers = max(1, int(settings.transcribe_workers))
    futures = []
    windows_submitted = 0
    windows_processed = 0
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        # submit up to transcribe_workers but allow progressive submission
        for w in selected:
            # if we've already exceeded the dynamic cap, stop submitting
            elapsed = time.perf_counter() - refine_start
            if elapsed >= cap_seconds:
                refine_cut = True
                break
            futures.append(ex.submit(refine_window, w))
            windows_submitted += 1

        # collect completed futures; if cap exceeded while collecting we stop
        try:
            for fut in as_completed(futures):
                try:
                    res = fut.result()
                except Exception:
                    res = []
                refined_segments.extend(res)
                windows_processed += 1
                elapsed = time.perf_counter() - refine_start
                if elapsed >= cap_seconds:
                    refine_cut = True
                    break
        finally:
            # attempt to cancel any futures that haven't started/finished
            for fut in futures:
                if not fut.done():
                    try:
                        fut.cancel()
                    except Exception:
                        pass
    refine_time = time.perf_counter() - refine_start
    if refine_cut:
        logger.info(f"Refine cut short after {refine_time:.2f}s (windows submitted={windows_submitted}, processed={windows_processed})")

    # Build final segments: keep fast segments that do not overlap selected windows, and insert refined segments
    final = []
    sel_intervals = selected

    def overlaps_any(seg_s, seg_e, intervals):
        for a, b in intervals:
            if not (seg_e <= a or seg_s >= b):
                return True
        return False

    # add non-overlapping fast segments
    for fs in fast_segments:
        if not overlaps_any(fs["start"], fs["end"], sel_intervals):
            final.append({"start": fs["start"], "end": fs["end"], "text": fs["text"], "words": fs["words"]})

    # add refined segments
    for rs in refined_segments:
        final.append(rs)

    # sort and return
    final_sorted = sorted(final, key=lambda x: x["start"]) if final else []
    t_total = time.perf_counter() - t_start

    # Emit a compact structured log line to help monitoring/tuning in prod.
    metrics = {
        "video": path.name,
        "total_audio_secs": round(total_dur, 2),
        "fast_segments": len(fast_segments),
        "flagged_windows_raw": len(raw_windows),
        "merged_windows": len(merged),
        "padded_windows": len(padded),
        "selected_windows": len(selected),
        "selected_secs": round(selected_secs, 2),
        "max_refine_secs": round(max_refine_secs, 2),
        "effective_refine_fraction": effective_frac,
        "refine_time_secs": round(refine_time, 2),
        "total_time_secs": round(t_total, 2),
    }
    logger.info("two_pass_metrics: %s", json.dumps(metrics, ensure_ascii=False))
    logger.info(f"Two-pass transcription complete: {len(final_sorted)} segments (took {t_total:.2f}s)")
    return final_sorted


def transcribe_fast_full(video_path: str, language: str | None = None) -> List[Dict[str, Any]]:
    """Fast single-pass transcription using the configured fast model.

    This is intended for the FAST job mode: run the small/fast model
    (usually 'tiny') over the whole audio to prioritise latency.
    """
    path = Path(video_path)
    if not path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    lang = language if language else (settings.whisper_language or None)
    fast_model_name = settings.whisper_fast_model
    fast_model = _get_model_by_name(fast_model_name, compute_type="int8")

    logger.info(f"Fast-full ({fast_model_name}) transcribing {path.name}…")
    seg_iter, _ = fast_model.transcribe(str(path), language=lang, word_timestamps=True, vad_filter=True,
                                        vad_parameters=dict(min_silence_duration_ms=500))

    segments: List[Dict[str, Any]] = []
    for seg in seg_iter:
        words = []
        if seg.words:
            words = [{"word": w.word, "start": w.start, "end": w.end, "prob": getattr(w, 'probability', None)} for w in seg.words]
        segments.append({"start": seg.start, "end": seg.end, "text": seg.text.strip(), "words": words})

    logger.info(f"Fast-full transcription complete: {len(segments)} segments detected.")
    return segments


def transcribe_for_job(video_path: str, transcription_mode: str | None = None, language: str | None = None) -> List[Dict[str, Any]]:
    """Job-level transcription entrypoint with simple FAST/QUALITY modes.

    Modes:
      - None or "FAST": low-latency fast model (single-pass tiny/base depending on config)
      - "QUALITY": run the two-pass refine workflow (may be slower but higher quality)

    This wrapper implements a minimal adaptive policy: FAST jobs avoid the
    expensive refine step entirely, while QUALITY jobs run the two-pass flow
    and honour the configured two_pass_max_refine_fraction. The job-level
    override is conservative and cannot increase the global refine fraction.
    """
    mode = (transcription_mode or "FAST").upper()
    logger.info(f"Transcription requested for {Path(video_path).name} with mode={mode}")

    if mode == "QUALITY":
        # Allow full two-pass behaviour as configured. We do not increase the
        # global fraction here; passing None keeps global behaviour.
        return transcribe_two_pass(video_path, language=language)

    # Default / FAST: return a fast single-pass transcript (no refine windows)
    return transcribe_fast_full(video_path, language=language)


def transcribe_video(video_path: str, language: str | None = None) -> List[Dict[str, Any]]:
    """
    Transcribe the audio track of a video file.

    Parameters
    ----------
    video_path : str
        Absolute path to the MP4 (or any ffmpeg-readable file).
    language : str | None
        ISO-639-1 language code (e.g. "fr", "en", "es").
        None or "" → Whisper auto-detects the language.

    Returns
    -------
    List of segment dicts with start/end timestamps and text.
    """
    path = Path(video_path)
    if not path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    model = _get_model()

    # Explicit language overrides the .env default; None = auto-detect
    lang = language if language else (settings.whisper_language or None)

    logger.info(f"Transcribing {path.name} (language={lang or 'auto'})…")
    segments_iter, info = model.transcribe(
        str(path),
        language=lang,
        word_timestamps=True,
        vad_filter=True,         # skip silent sections
        vad_parameters=dict(
            min_silence_duration_ms=500,
        ),
    )

    segments: List[Dict[str, Any]] = []
    for seg in segments_iter:
        words = []
        if seg.words:
            words = [
                {"word": w.word, "start": w.start, "end": w.end, "prob": w.probability}
                for w in seg.words
            ]
        segments.append(
            {
                "start": seg.start,
                "end":   seg.end,
                "text":  seg.text.strip(),
                "words": words,
            }
        )

    logger.info(f"Transcription complete: {len(segments)} segments detected.")
    return segments
