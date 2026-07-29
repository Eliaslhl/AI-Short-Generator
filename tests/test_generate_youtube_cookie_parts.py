"""CLI regression tests for the cookie-parts helper."""

import subprocess
import sys
from pathlib import Path


SCRIPT = Path("scripts/generate_youtube_cookie_parts.py")


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def test_cookie_parts_rejects_missing_empty_and_directory_inputs(tmp_path):
    output = tmp_path / "parts.env"
    empty = tmp_path / "empty cookies.txt"
    empty.write_bytes(b"")

    for source, message in (
        (tmp_path / "missing.txt", "Input not found"),
        (empty, "Input cookies file is empty"),
        (tmp_path, "Input not found"),
    ):
        result = _run("--input", str(source), "--out", str(output))
        assert result.returncode != 0
        assert message in result.stderr
        assert "Traceback" not in result.stderr


def test_cookie_parts_supports_spaces_without_printing_cookie_contents(tmp_path):
    source = tmp_path / "cookies with spaces.txt"
    output = tmp_path / "parts.env"
    secret_cookie_value = "synthetic-cookie-value"
    source.write_text(secret_cookie_value, encoding="utf-8")

    result = _run("--input", str(source), "--parts", "2", "--out", str(output))

    assert result.returncode == 0
    assert secret_cookie_value not in result.stdout
    assert source.name in output.read_text(encoding="utf-8")
    assert str(source.parent) not in output.read_text(encoding="utf-8")
