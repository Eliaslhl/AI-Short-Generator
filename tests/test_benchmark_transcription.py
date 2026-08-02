"""Unit tests for the deterministic, pure-logic parts of the transcription
benchmark (WER, cost extrapolation, corpus loading). The benchmark's own
subprocess-driven parts (macOS `say`, ffmpeg noise mixing, real Faster-Whisper
transcription) are exercised manually — they are slow, platform-specific, and
depend on the real model, so they do not belong in the fast/deterministic
backend test suite."""

from pathlib import Path

import pytest

import backend.scripts.benchmark_transcription as bench


def test_wer_is_zero_for_identical_text():
    assert bench.word_error_rate("hello world", "hello world") == 0.0


def test_wer_is_one_for_completely_different_text():
    assert bench.word_error_rate("hello world", "goodbye moon") == 1.0


def test_wer_counts_a_single_substitution():
    # 1 wrong word out of 3 reference words.
    assert bench.word_error_rate("the quick fox", "the slow fox") == pytest.approx(1 / 3)


def test_wer_counts_insertions_and_deletions():
    # reference has 3 words; hypothesis drops "quick" (1 deletion) and adds
    # "very" (1 insertion) -> 2 edits / 3 reference words.
    assert bench.word_error_rate("the quick brown fox", "the very brown") == pytest.approx(2 / 4)


def test_wer_ignores_case_and_punctuation():
    assert bench.word_error_rate("Hello, world!", "hello world") == 0.0


def test_wer_handles_empty_reference():
    assert bench.word_error_rate("", "") == 0.0
    assert bench.word_error_rate("", "some text") == 1.0


def test_estimate_cost_is_zero_for_zero_duration():
    assert bench.estimate_cost_per_hour_of_video(cpu_time_seconds=10.0, audio_duration_seconds=0.0) == 0.0


def test_estimate_cost_scales_with_cpu_to_audio_ratio():
    # 1 CPU-second per 1 audio-second -> 3600 CPU-seconds per hour of video
    # -> 1 vCPU-hour -> exactly ASSUMED_USD_PER_VCPU_HOUR.
    cost = bench.estimate_cost_per_hour_of_video(cpu_time_seconds=10.0, audio_duration_seconds=10.0)
    assert cost == pytest.approx(bench.ASSUMED_USD_PER_VCPU_HOUR)


def test_load_corpus_dir_reads_matching_triples(tmp_path):
    (tmp_path / "sample-a.txt").write_text("hello world")
    (tmp_path / "sample-a.wav").write_bytes(b"fake-wav")
    (tmp_path / "sample-a.lang").write_text("en\n")

    samples = bench.load_corpus_dir(tmp_path)

    assert samples == [
        {
            "id": "sample-a",
            "language": "en",
            "text": "hello world",
            "audio_path": str(tmp_path / "sample-a.wav"),
        }
    ]


def test_load_corpus_dir_skips_a_txt_without_a_matching_wav(tmp_path, capsys):
    (tmp_path / "orphan.txt").write_text("no audio for this one")

    samples = bench.load_corpus_dir(tmp_path)

    assert samples == []
    assert "orphan" in capsys.readouterr().err


def test_load_corpus_dir_defaults_language_to_empty_when_no_lang_file(tmp_path):
    (tmp_path / "sample-b.txt").write_text("bonjour")
    (tmp_path / "sample-b.wav").write_bytes(b"fake-wav")

    samples = bench.load_corpus_dir(tmp_path)

    assert samples[0]["language"] == ""
