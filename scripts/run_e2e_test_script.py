#!/usr/bin/env python3
"""Simple end-to-end test: download a YouTube video (using cookies), then run fast transcription.

Usage: python scripts/run_e2e_test_script.py <youtube_url>

This script prints a short summary and the first few transcript segments.
"""

import sys
import uuid
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

if len(sys.argv) < 2:
    print("Usage: python scripts/run_e2e_test_script.py <youtube_url>")
    sys.exit(2)

url = sys.argv[1]
job_id = f"e2e_test_{uuid.uuid4().hex[:8]}"

try:
    from backend.services.youtube_service import download_video
    from backend.services.transcription_service import transcribe_for_job
except Exception as e:
    logger.exception("Failed to import project modules: %s", e)
    raise

try:
    logger.info(f"Starting E2E test for {url} (job_id={job_id})")
    video_path, title = download_video(url, job_id, audio_only=False)
    logger.info(f"Downloaded video: {video_path} (title: {title})")

    # Run a fast transcription to keep this test quick
    segs = transcribe_for_job(str(video_path), transcription_mode="FAST")
    logger.info(f"Transcription produced {len(segs)} segments. Showing up to 5:")
    for s in segs[:5]:
        print(f"[{s['start']:.1f}-{s['end']:.1f}] {s['text']}")

    logger.info("E2E test completed successfully.")
except Exception as e:
    logger.exception("E2E test failed: %s", e)
    raise
