#!/usr/bin/env python3
"""
Example API client demonstrating the include_subtitles feature.

This script shows how to call the generate endpoint with and without subtitles.
"""

import requests
import json
import time
from typing import Optional

class AIShortGeneratorClient:
    """Client for the AI Shorts Generator API."""
    
    def __init__(self, base_url: str = "http://localhost:8000", token: Optional[str] = None):
        """Initialize the client.
        
        Args:
            base_url: API base URL (default: localhost:8000)
            token: JWT auth token (optional for development)
        """
        self.base_url = base_url
        self.token = token
        self.session = requests.Session()
        if token:
            self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def generate_without_subtitles(self, youtube_url: str, max_clips: int = 3) -> dict:
        """Generate shorts WITHOUT subtitles (faster processing).
        
        Args:
            youtube_url: YouTube URL to process
            max_clips: Maximum number of clips to generate
            
        Returns:
            Response with job_id
        """
        payload = {
            "youtube_url": youtube_url,
            "max_clips": max_clips,
            "include_subtitles": False,  # NEW: Explicitly disable subtitles
        }
        
        print("\n📹 Generating shorts WITHOUT subtitles...")
        print(f"   URL: {youtube_url}")
        print(f"   Max clips: {max_clips}")
        
        response = self.session.post(
            f"{self.base_url}/api/generate",
            json=payload
        )
        response.raise_for_status()
        result = response.json()
        print(f"   ✅ Job ID: {result.get('job_id')}")
        return result
    
    def generate_with_subtitles(self, youtube_url: str, max_clips: int = 3) -> dict:
        """Generate shorts WITH subtitles (standard processing).
        
        Args:
            youtube_url: YouTube URL to process
            max_clips: Maximum number of clips to generate
            
        Returns:
            Response with job_id
        """
        payload = {
            "youtube_url": youtube_url,
            "max_clips": max_clips,
            "include_subtitles": True,   # NEW: Enable subtitles
        }
        
        print("\n📹 Generating shorts WITH subtitles...")
        print(f"   URL: {youtube_url}")
        print(f"   Max clips: {max_clips}")
        
        response = self.session.post(
            f"{self.base_url}/api/generate",
            json=payload
        )
        response.raise_for_status()
        result = response.json()
        print(f"   ✅ Job ID: {result.get('job_id')}")
        return result
    
    def get_status(self, job_id: str) -> dict:
        """Get the status of a generation job.
        
        Args:
            job_id: Job ID returned from generate()
            
        Returns:
            Job status information
        """
        response = self.session.get(f"{self.base_url}/api/status/{job_id}")
        response.raise_for_status()
        return response.json()
    
    def wait_for_completion(self, job_id: str, timeout: int = 3600) -> dict:
        """Wait for a job to complete.
        
        Args:
            job_id: Job ID to monitor
            timeout: Maximum seconds to wait
            
        Returns:
            Final job status
        """
        start_time = time.time()
        last_progress = -1
        
        while time.time() - start_time < timeout:
            status = self.get_status(job_id)
            progress = status.get("progress", 0)
            
            if progress != last_progress:
                print(f"   {progress}% - {status.get('step', 'Processing...')}")
                last_progress = progress
            
            if status.get("status") in ("completed", "error"):
                return status
            
            time.sleep(2)
        
        raise TimeoutError(f"Job {job_id} did not complete within {timeout} seconds")


def demo():
    """Demo the include_subtitles feature."""
    
    print("="*70)
    print("AI Shorts Generator - Subtitles Feature Demo")
    print("="*70)
    
    # Example YouTube URL
    youtube_url = "https://www.youtube.com/watch?v=c6W0FHkRujQ"
    
    client = AIShortGeneratorClient()
    
    # Example 1: Generate WITHOUT subtitles (recommended for faster processing)
    print("\n📊 EXAMPLE 1: Generate WITHOUT subtitles")
    print("-" * 70)
    client.generate_without_subtitles(youtube_url, max_clips=3)
    print("Request payload:")
    print(json.dumps({
        "youtube_url": youtube_url,
        "max_clips": 3,
        "include_subtitles": False,  # 👈 Key parameter
    }, indent=2))
    
    # Example 2: Generate WITH subtitles (emoji captions)
    print("\n📊 EXAMPLE 2: Generate WITH subtitles")
    print("-" * 70)
    client.generate_with_subtitles(youtube_url, max_clips=3)
    print("Request payload:")
    print(json.dumps({
        "youtube_url": youtube_url,
        "max_clips": 3,
        "include_subtitles": True,   # 👈 Key parameter
    }, indent=2))
    
    # Performance comparison info
    print("\n⚡ PERFORMANCE COMPARISON")
    print("-" * 70)
    print("Without subtitles:")
    print("  ✓ ~10-15% faster pipeline")
    print("  ✓ Skips caption generation step")
    print("  ✓ Smaller output files")
    print("  ✓ Recommended for batch processing")
    print()
    print("With subtitles:")
    print("  ✓ Includes emoji captions at bottom")
    print("  ✓ Standard rendering time")
    print("  ✓ Better for social media engagement")
    print("  ✓ More polished look")
    
    # Configuration info
    print("\n⚙️  CONFIGURATION")
    print("-" * 70)
    print("Default behavior (in .env):")
    print("  INCLUDE_SUBTITLES_BY_DEFAULT=false")
    print()
    print("API parameter (per-request):")
    print('  "include_subtitles": true|false')
    print()
    print("API parameter overrides config setting!")
    
    print("\n" + "="*70)
    print("✅ Feature demonstration complete")
    print("="*70)


if __name__ == "__main__":
    demo()
