# Transcription QUALITY vs FAST — benchmark

`backend/scripts/benchmark_transcription.py` measures whether `TranscriptionMode.QUALITY`
(two-pass refine) is worth its extra cost over `TranscriptionMode.FAST` (single
`tiny`-model pass).

## Reproducing

```bash
PYTHONPATH=. .venv/bin/python backend/scripts/benchmark_transcription.py
```

The corpus is synthesized at run time from the macOS `say` command against a
known reference transcript (no private, licensed, or otherwise real media is
read from or written into the repository). On a platform without `say`, pass
`--corpus-dir` pointing at a local, uncommitted directory of `<id>.wav` /
`<id>.txt` / `<id>.lang` triples.

Each transcription runs in an isolated forked child process so its CPU time
and peak RSS are measured via `os.wait4()`, not blended with any other call.
Every `(sample, mode)` pair runs twice to check whether segment timestamps
are stable across identical repeated runs.

## Findings (2026-08-03, CPU-only, `whisper_fast_model=tiny`, `whisper_refine_model=base`)

- **QUALITY produced a byte-identical transcript to FAST on the majority of
  the corpus**, including every clean-audio sample (English and French).
  `TranscriptionMode.QUALITY`'s refine pass only touches segments whose
  average word probability falls below `two_pass_conf_threshold` (0.70) —
  clean, correctly-pronounced speech stays above that threshold, so the
  refine step never runs and QUALITY costs exactly the same as FAST while
  changing nothing.

- **On uniformly noisy audio, the refine pass can also do nothing — for a
  different reason.** `transcribe_two_pass` selects flagged windows
  all-or-nothing against a `two_pass_max_refine_fraction` (0.15 = 15% of
  total audio duration) budget: if adjacent low-confidence segments merge
  into one window whose *total* duration exceeds that budget, the entire
  window is dropped, not partially included. Measured directly: a ~44s
  clip with noise spread throughout flagged 13/13 segments, merged them
  into one ~38s window against a 6.69s budget, and selected **zero**
  seconds for refine. The same pattern reproduced across every noise
  level and burst placement tried (uniform noise, a short localized
  burst, several dB levels) — the mechanism is easy to starve for
  anything but a few small, isolated low-confidence pockets in an
  otherwise clean, longer recording.

- **Where QUALITY did change the output** (noisy samples, one run of the
  full corpus), the effect was small and not clearly better: e.g. one
  ~44s noisy sample went from 65.6% WER (FAST) to 64.0% WER (QUALITY) —
  within run-to-run noise, not a demonstrated accuracy win.

- **Timestamp/text stability**: identical repeated runs of the same
  `(sample, mode)` pair were stable on every clean sample. On the
  heaviest-noise short sample, two identical runs produced *different*
  segment counts, different detected language, and 100% WER both times —
  i.e. under heavy noise, Faster-Whisper's own output is not perfectly
  deterministic in this environment, independent of FAST vs QUALITY.

- **Language detection**: correct on clean English/French samples in every
  run; degraded (including misdetecting a completely unrelated language)
  on the heaviest-noise sample — expected, not FAST/QUALITY-specific.

- **Cost**: QUALITY's estimated cost only exceeds FAST's when the refine
  pass actually runs (the noisy-sample rows). On the tested corpus this
  puts QUALITY at roughly the same cost as FAST on average, because refine
  rarely fires at all — see the caveat below before reading too much into
  the absolute dollar figures.

## What this does **not** show

- This corpus is short (7–45s per sample) and CPU-only on a single
  developer machine; production transcribes full source videos (minutes
  long, per `backend/api/routes.py::run_pipeline`), where the 15% refine
  budget has much more headroom in absolute seconds. The all-or-nothing
  window-selection bug reproduces regardless of clip length, but whether
  it materially affects real, minutes-long VODs was not measured here.
- Real noisy audio (crowd noise, music, cross-talk) differs qualitatively
  from synthetic pink noise mixed with TTS speech; WER numbers here are
  not representative of real-world accuracy, only useful for a relative
  FAST-vs-QUALITY comparison under matched, reproducible conditions.
- `estimate_cost_per_hour_of_video()` extrapolates from measured CPU time
  using a single documented assumption (`$0.05`/vCPU-hour, adjustable in
  the script) — it is a rough order-of-magnitude figure, not a production
  billing estimate.

## Conclusion

No quota, model, or pipeline change is proposed here, per scope. The data
above is a reason to look specifically at the window-selection logic in
`transcribe_two_pass` (`backend/services/transcription_service.py`) — an
all-or-nothing budget check that can discard an entire flagged window
instead of consuming a partial budget — as a likely candidate for why
QUALITY is not currently earning its cost, before deciding whether to
adjust `two_pass_max_refine_fraction`, make the selection budget-aware
per-window, or reconsider the Pro+ gating on this mode.
