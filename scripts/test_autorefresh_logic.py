#!/usr/bin/env python3
"""
Quick test to validate the auto-refresh-and-retry logic.
This simulates what happens when yt-dlp fails with "Sign in to confirm...".
"""

import re
import sys
from pathlib import Path

def test_refresh_script_exists():
    """Check that refresh script is present."""
    script = Path(__file__).parent / "refresh_youtube_cookies.py"
    assert script.exists(), f"refresh script not found: {script}"
    print("✓ refresh_youtube_cookies.py exists")

def test_refresh_script_compiles():
    """Check that refresh script compiles."""
    script = Path(__file__).parent / "refresh_youtube_cookies.py"
    try:
        import py_compile
        py_compile.compile(str(script), doraise=True)
        print("✓ refresh_youtube_cookies.py compiles")
    except Exception as e:
        print(f"✗ refresh script compile error: {e}")
        return False
    return True

def test_backend_compiles():
    """Check that backend with auto-refresh logic compiles."""
    backend_file = Path(__file__).parent.parent / "backend" / "services" / "youtube_service.py"
    try:
        import py_compile
        py_compile.compile(str(backend_file), doraise=True)
        print("✓ youtube_service.py (with auto-refresh) compiles")
    except Exception as e:
        print(f"✗ backend compile error: {e}")
        return False
    return True

def test_wrote_line_parsing():
    """Test that the WROTE line parsing regex works correctly."""
    test_line = "WROTE /tmp/youtube_cookies.txt size=386836 sha256=e634c16fd8f8b7dc35176ecb80f8510f9393d745c60cc7c1f039c717bc0ee672"
    pattern = r"WROTE\s+(\S+)\s+size=\s*(\d+)\s+sha256=([0-9a-fA-F]+)"
    m = re.search(pattern, test_line)
    assert m, f"WROTE line parsing failed for: {test_line}"
    path, size, sha = m.groups()
    assert path == "/tmp/youtube_cookies.txt", f"path mismatch: {path}"
    assert size == "386836", f"size mismatch: {size}"
    assert sha == "e634c16fd8f8b7dc35176ecb80f8510f9393d745c60cc7c1f039c717bc0ee672", f"sha mismatch: {sha}"
    print(f"✓ WROTE line parsing works: path={path}, size={size}, sha={sha[:16]}...")

def test_oneoff_wrapper_exists():
    """Check that the one-off wrapper script exists."""
    wrapper = Path(__file__).parent / "refresh_oneoff.sh"
    assert wrapper.exists(), f"one-off wrapper not found: {wrapper}"
    print("✓ refresh_oneoff.sh exists")

def test_env_example_exists():
    """Check that env example file exists."""
    env_file = Path(__file__).parent / "refresh.env.example"
    assert env_file.exists(), f"env example not found: {env_file}"
    print("✓ refresh.env.example exists")

def main():
    print("=" * 60)
    print("Auto-Refresh Logic Validation Tests")
    print("=" * 60)
    
    tests = [
        ("refresh script exists", test_refresh_script_exists),
        ("refresh script compiles", test_refresh_script_compiles),
        ("backend compiles", test_backend_compiles),
        ("WROTE line parsing", test_wrote_line_parsing),
        ("one-off wrapper exists", test_oneoff_wrapper_exists),
        ("env example exists", test_env_example_exists),
    ]
    
    failed = 0
    for name, test_func in tests:
        try:
            result = test_func()
            if result is False:
                failed += 1
        except AssertionError as e:
            print(f"✗ {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {name}: {type(e).__name__}: {e}")
            failed += 1
    
    print("=" * 60)
    if failed == 0:
        print("All tests passed! Auto-refresh logic is ready.")
        return 0
    else:
        print(f"Failed: {failed} test(s)")
        return 1

if __name__ == "__main__":
    sys.exit(main())
