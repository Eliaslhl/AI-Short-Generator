"""Regression coverage for detected Whisper language metadata."""

from types import SimpleNamespace

import backend.services.transcription_service as transcription_service


def test_fast_transcription_preserves_detected_language_for_all_segments(monkeypatch, tmp_path):
    video_path = tmp_path / "source.mp4"
    video_path.write_bytes(b"video")
    segments = [
        SimpleNamespace(start=0.0, end=1.0, text="Bonjour", words=[]),
        SimpleNamespace(start=1.0, end=2.0, text="Monde", words=[]),
    ]
    info = SimpleNamespace(language="fr")
    model = SimpleNamespace(transcribe=lambda *_args, **_kwargs: (iter(segments), info))
    monkeypatch.setattr(transcription_service, "_get_model_by_name", lambda *_args, **_kwargs: model)

    result = transcription_service.transcribe_fast_full(str(video_path))

    assert result == [
        {
            "start": 0.0,
            "end": 1.0,
            "text": "Bonjour",
            "words": [],
            "detected_language": "fr",
        },
        {
            "start": 1.0,
            "end": 2.0,
            "text": "Monde",
            "words": [],
            "detected_language": "fr",
        },
    ]


def test_fast_transcription_accepts_missing_detected_language(monkeypatch, tmp_path):
    video_path = tmp_path / "source.mp4"
    video_path.write_bytes(b"video")
    segment = SimpleNamespace(start=0.0, end=1.0, text="Hello", words=[])
    model = SimpleNamespace(
        transcribe=lambda *_args, **_kwargs: (iter([segment]), SimpleNamespace())
    )
    monkeypatch.setattr(transcription_service, "_get_model_by_name", lambda *_args, **_kwargs: model)

    assert transcription_service.transcribe_fast_full(str(video_path)) == [
        {"start": 0.0, "end": 1.0, "text": "Hello", "words": []}
    ]
