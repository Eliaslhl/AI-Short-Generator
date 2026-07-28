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


def test_quality_transcription_preserves_fast_pass_language_and_timestamps(
    monkeypatch, tmp_path
):
    video_path = tmp_path / "source.mp4"
    video_path.write_bytes(b"video")
    word = SimpleNamespace(word="Hola", start=0.0, end=0.5, probability=0.99)
    segment = SimpleNamespace(start=0.0, end=1.0, text="Hola", words=[word])
    calls = []

    def transcribe(*_args, **kwargs):
        calls.append(kwargs)
        return iter([segment]), SimpleNamespace(language="es")

    model = SimpleNamespace(transcribe=transcribe)
    monkeypatch.setattr(
        transcription_service,
        "_get_model_by_name",
        lambda *_args, **_kwargs: model,
    )
    monkeypatch.setattr(transcription_service, "_ffprobe_duration", lambda _path: 1.0)

    assert transcription_service.transcribe_two_pass(str(video_path)) == [
        {
            "start": 0.0,
            "end": 1.0,
            "text": "Hola",
            "words": [{"word": "Hola", "start": 0.0, "end": 0.5, "prob": 0.99}],
            "detected_language": "es",
        }
    ]
    assert calls == [
        {
            "language": None,
            "word_timestamps": True,
            "vad_filter": True,
            "vad_parameters": {"min_silence_duration_ms": 500},
        }
    ]


def test_quality_refinement_preserves_fast_pass_language_and_word_timestamps(
    monkeypatch, tmp_path
):
    video_path = tmp_path / "source.mp4"
    video_path.write_bytes(b"video")
    fast_word = SimpleNamespace(word="Holla", start=0.0, end=0.5, probability=0.2)
    refined_word = SimpleNamespace(word="Hola", start=0.0, end=0.5, probability=0.99)
    fast_segment = SimpleNamespace(start=0.0, end=1.0, text="Holla", words=[fast_word])
    refined_segment = SimpleNamespace(
        start=0.0, end=0.75, text="Hola", words=[refined_word]
    )
    calls = []

    def fast_transcribe(*_args, **kwargs):
        calls.append(("fast", kwargs))
        return iter([fast_segment]), SimpleNamespace(language="es")

    def refine_transcribe(*_args, **kwargs):
        calls.append(("refine", kwargs))
        return iter([refined_segment]), SimpleNamespace(language="en")

    models = iter(
        [
            SimpleNamespace(transcribe=fast_transcribe),
            SimpleNamespace(transcribe=refine_transcribe),
        ]
    )
    monkeypatch.setattr(
        transcription_service,
        "_get_model_by_name",
        lambda *_args, **_kwargs: next(models),
    )
    monkeypatch.setattr(transcription_service, "_ffprobe_duration", lambda _path: 10.0)
    monkeypatch.setattr(
        "backend.services.youtube_service.extract_audio",
        lambda _source, destination, **_kwargs: open(destination, "wb").close(),
    )

    assert transcription_service.transcribe_two_pass(str(video_path)) == [
        {
            "start": 0.0,
            "end": 0.75,
            "text": "Hola",
            "words": [{"word": "Hola", "start": 0.0, "end": 0.5, "prob": 0.99}],
            "detected_language": "es",
        }
    ]
    assert calls == [
        (
            "fast",
            {
                "language": None,
                "word_timestamps": True,
                "vad_filter": True,
                "vad_parameters": {"min_silence_duration_ms": 500},
            },
        ),
        (
            "refine",
            {"language": None, "word_timestamps": True, "vad_filter": False},
        ),
    ]
