#!/usr/bin/env python3
"""Test script for include_subtitles feature."""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.config import settings
from backend.api.routes import GenerateRequest

def test_include_subtitles():
    """Test that include_subtitles parameter works correctly."""
    
    print("Testing include_subtitles feature...\n")
    
    # Test 1: Default value (False)
    req1 = GenerateRequest(youtube_url="https://www.youtube.com/watch?v=test")
    print(f"✅ Test 1: Default include_subtitles = {req1.include_subtitles}")
    assert not req1.include_subtitles, "Default should be False"
    
    # Test 2: Explicitly set to True
    req2 = GenerateRequest(
        youtube_url="https://www.youtube.com/watch?v=test",
        include_subtitles=True
    )
    print(f"✅ Test 2: Explicit include_subtitles=True = {req2.include_subtitles}")
    assert req2.include_subtitles
    
    # Test 3: Explicitly set to False
    req3 = GenerateRequest(
        youtube_url="https://www.youtube.com/watch?v=test",
        include_subtitles=False
    )
    print(f"✅ Test 3: Explicit include_subtitles=False = {req3.include_subtitles}")
    assert not req3.include_subtitles
    
    # Test 4: Config default
    print(f"\n✅ Test 4: Config default include_subtitles_by_default = {settings.include_subtitles_by_default}")
    assert not settings.include_subtitles_by_default, "Config default should be False"
    
    print("\n✅ All tests passed!")
    print("\nSummary:")
    print("- API parameter 'include_subtitles' defaults to False")
    print("- Config 'include_subtitles_by_default' is False")
    print("- Users can opt-in to subtitles via API parameter")
    print("- When disabled, caption generation is skipped for performance")

if __name__ == "__main__":
    test_include_subtitles()
