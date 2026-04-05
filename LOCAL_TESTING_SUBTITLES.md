#!/usr/bin/env python3
"""
LOCAL TESTING GUIDE: include_subtitles Feature

This guide shows how to test the new subtitle toggle feature locally.
"""

GUIDE = """
================================================================================
TESTING THE SUBTITLES FEATURE LOCALLY
================================================================================

## Setup

1. Start the backend server:
   cd ai-shorts-generator
   python -m backend.main

2. In another terminal, run tests:
   python test_include_subtitles.py

## Test Cases

### Test 1: Default behavior (no subtitles)
Request without 'include_subtitles' parameter:
{
    "youtube_url": "https://www.youtube.com/watch?v=c6W0FHkRujQ",
    "max_clips": 3
}
Expected: Shorts generated WITHOUT subtitles (faster processing)

### Test 2: Explicitly enable subtitles
Request with 'include_subtitles': true:
{
    "youtube_url": "https://www.youtube.com/watch?v=c6W0FHkRujQ",
    "max_clips": 3,
    "include_subtitles": true
}
Expected: Shorts generated WITH subtitle overlays

### Test 3: Explicitly disable subtitles
Request with 'include_subtitles': false:
{
    "youtube_url": "https://www.youtube.com/watch?v=c6W0FHkRujQ",
    "max_clips": 3,
    "include_subtitles": false
}
Expected: Shorts generated WITHOUT subtitles (same as default)

## Using curl for testing

### Test without subtitles:
curl -X POST http://localhost:8000/api/generate \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -d '{
    "youtube_url": "https://www.youtube.com/watch?v=c6W0FHkRujQ",
    "max_clips": 3,
    "include_subtitles": false
  }'

### Test with subtitles:
curl -X POST http://localhost:8000/api/generate \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -d '{
    "youtube_url": "https://www.youtube.com/watch?v=c6W0FHkRujQ",
    "max_clips": 3,
    "include_subtitles": true
  }'

## Checking Generated Clips

After running a test, check the output:
1. Without subtitles: 
   - Should see video with no text overlays
   - Processing time should be shorter
   - No emoji captions generation step

2. With subtitles:
   - Should see video with yellow emoji captions at bottom
   - Processing time longer
   - Visible "Building emoji captions..." step

## Performance Comparison

Run two tests and compare:

Test 1 (no subtitles):
time curl ... -d '{"youtube_url":"...", "include_subtitles": false}'

Test 2 (with subtitles):
time curl ... -d '{"youtube_url":"...", "include_subtitles": true}'

Expected difference: ~10-15% faster without subtitles

## Configuration Testing

### Test 1: Default config (subtitles disabled)
Current .env:
  include_subtitles_by_default=false
Expected: Request without 'include_subtitles' → no subtitles

### Test 2: Override config (subtitles enabled by default)
Edit .env:
  include_subtitles_by_default=true
Restart server
Expected: Request without 'include_subtitles' → WITH subtitles

API parameter still overrides config:
{
    "youtube_url": "https://...",
    "include_subtitles": false  # Override config setting
}
Result: Even with config enabled, this request gets no subtitles

## Logging/Debugging

Monitor the backend logs:
- Look for "Skipping caption generation..." when include_subtitles=false
- Look for "Building emoji captions..." when include_subtitles=true

Example log output:
  [job-123] 60% – Processing segments…
  [job-123] 65% – Skipping caption generation…  (when false)
  [job-123] 75% – Rendering clip 1/3…

vs

  [job-456] 60% – Processing segments…
  [job-456] 65% – Building emoji captions…  (when true)
  [job-456] 75% – Rendering clip 1/3…

## Cleanup

Remove test files when done:
rm -f test_include_subtitles.py benchmark_youtube.py test_youtube_*.py
rm -rf data/videos/youtube_benchmark
"""

if __name__ == "__main__":
    print(GUIDE)
    print("\n" + "="*80)
    print("START TESTING!")
    print("="*80)
