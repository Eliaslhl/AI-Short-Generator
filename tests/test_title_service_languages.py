"""Regression coverage for localized title generation."""

import asyncio
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

import backend.api.routes as routes
import backend.database as database
import backend.services.title_service as title_service


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("en", "en"),
        ("en-US", "en"),
        ("en_GB", "en"),
        ("fr", "fr"),
        ("fr-FR", "fr"),
        ("fr_CA", "fr"),
        ("es", "es"),
        ("es-MX", "es"),
        ("de", "de"),
        ("de-DE", "de"),
        ("FR-fr", "fr"),
        (None, "en"),
        ("", "en"),
        ("auto", "en"),
        ("pt-BR", "en"),
    ],
)
def test_normalize_title_language(value, expected):
    assert title_service.normalize_title_language(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("EN_us", "en"),
        (" fr-FR ", "fr"),
        ("es_MX", "es"),
        ("de-DE", "de"),
        ("auto", None),
        ("", None),
        ("   ", None),
        (None, None),
        ("pt-BR", None),
        (123, None),
    ],
)
def test_normalize_supported_language_distinguishes_unknown_values(value, expected):
    assert title_service.normalize_supported_language(value) == expected


@pytest.mark.parametrize(
    ("language", "expected_instruction"),
    [
        ("en-US", "output ONLY the title"),
        ("fr-FR", "titre en français"),
        ("es_MX", "título en español"),
        ("de-DE", "Titel auf Deutsch"),
        ("unknown", "output ONLY the title"),
        (None, "output ONLY the title"),
        ("auto", "output ONLY the title"),
    ],
)
def test_generate_title_uses_localized_prompt(monkeypatch, language, expected_instruction):
    prompts = []
    monkeypatch.setattr(
        title_service,
        "_call_groq",
        lambda prompt: prompts.append(prompt) or "A concise title",
    )

    assert title_service.generate_title("A transcript excerpt.", language) == "A concise title"
    assert expected_instruction in prompts[0]
    assert 'A transcript excerpt.' in prompts[0]


@pytest.mark.parametrize(
    ("provider_response", "expected"),
    [
        ('"A quoted title"', "A quoted title"),
        ("Titre: Un titre français", "Un titre français"),
        ("Título: Un título español", "Un título español"),
        ("Titel: Ein deutscher Titel", "Ein deutscher Titel"),
        ("« Un titre français »", "Un titre français"),
        ("Title - A title", "A title"),
        ("First line\nSecond line", "First line"),
    ],
)
def test_generate_title_cleans_provider_formatting(monkeypatch, provider_response, expected):
    monkeypatch.setattr(title_service, "_call_groq", lambda _prompt: provider_response)
    assert title_service.generate_title("A transcript excerpt.", language="fr") == expected


@pytest.mark.parametrize("response", ["", "   "])
def test_generate_title_uses_non_empty_fallback_for_empty_provider_response(monkeypatch, response):
    monkeypatch.setattr(title_service, "_call_groq", lambda _prompt: response)
    assert title_service.generate_title("This is the fallback sentence.") == "This is the fallback sentence"


def test_generate_title_uses_historical_fallback_when_provider_fails(monkeypatch):
    monkeypatch.setattr(title_service, "_call_groq", lambda _prompt: (_ for _ in ()).throw(RuntimeError()))
    assert title_service.generate_title("This is the fallback sentence.") == "This is the fallback sentence"


class _Result:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _PipelineSession:
    def __init__(self, job_record):
        self.job_record = job_record

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def execute(self, _statement):
        return _Result(self.job_record)

    async def commit(self):
        return None


async def _run_title_pipeline(monkeypatch, language, detected_language=None):
    job_id = "localized-title-job"
    segment = {
        "start": 0.0,
        "end": 10.0,
        "text": "A transcript excerpt.",
        "words": [],
    }
    if detected_language:
        segment["detected_language"] = detected_language

    job_record = SimpleNamespace(
        id=job_id,
        status="pending",
        progress=0,
        clips_json=None,
        video_title=None,
        error=None,
    )
    monkeypatch.setattr(database, "AsyncSessionLocal", lambda: _PipelineSession(job_record))
    monkeypatch.setattr(routes, "download_youtube", lambda *_args: (Path("source.mp4"), "Source"))
    transcribe_calls = []
    monkeypatch.setattr(
        "backend.services.transcription_service.transcribe_for_job",
        lambda *_args: transcribe_calls.append(_args) or [segment],
    )
    monkeypatch.setattr(routes, "select_top_segments", lambda *_args: [dict(segment)])
    monkeypatch.setattr(routes, "generate_hook", lambda _text: "Hook")
    monkeypatch.setattr(routes, "generate_hashtags", lambda _text: [])
    title_calls = []
    monkeypatch.setattr(
        routes,
        "generate_title",
        lambda text, *, language: title_calls.append((text, language)) or "Localized title",
    )
    monkeypatch.setattr(routes, "build_captions", lambda *_args: [])
    monkeypatch.setattr(routes, "render_clip", lambda **_kwargs: {"file": "/clips/job.mp4"})
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(stdout=json.dumps({"format": {"duration": "10"}})),
    )
    routes.jobs[job_id] = {"status": "pending", "progress": 0, "step": "Queued", "clips": []}
    try:
        await routes.run_pipeline(
            job_id,
            "https://www.youtube.com/watch?v=test",
            "user-id",
            max_clips=1,
            language=language,
            is_proplus=True,
        )
    finally:
        routes.jobs.pop(job_id, None)
    return title_calls, transcribe_calls


@pytest.mark.parametrize(
    ("language", "detected_language", "expected_title_language", "expected_transcription_language"),
    [
        ("fr", "en", "fr", "fr"),
        ("fr-FR", "en", "fr", "fr-FR"),
        ("auto", "es", "es", None),
        (None, "de", "de", None),
        ("", "fr", "fr", None),
        ("pt-BR", "es", "es", "pt-BR"),
        ("pt-BR", "pt", "en", "pt-BR"),
        ("pt-BR", None, "en", "pt-BR"),
        ("en", "fr", "en", "en"),
        ("unknown", "unknown", "en", "unknown"),
    ],
)
def test_pipeline_propagates_resolved_title_language(
    monkeypatch,
    language,
    detected_language,
    expected_title_language,
    expected_transcription_language,
):
    title_calls, transcribe_calls = asyncio.run(
        _run_title_pipeline(monkeypatch, language, detected_language)
    )

    assert title_calls == [("A transcript excerpt.", expected_title_language)]
    assert transcribe_calls[0][-1] == expected_transcription_language
