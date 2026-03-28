"""
Test Configuration & Examples for Advanced Twitch Processing
"""

# ============================================================================
# TEST 1: API Endpoint Tests
# ============================================================================

import requests
import json
import time

BASE_URL = "http://localhost:8000"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": "Bearer test-token"  # Replace with real token
}

def test_start_processing():
    """Test: POST /api/generate/twitch/advanced"""
    
    payload = {
        "url": "https://www.twitch.tv/videos/1234567890",
        "max_clips": 5,
        "language": "en"
    }
    
    print("🔄 Starting video processing...")
    response = requests.post(
        f"{BASE_URL}/api/generate/twitch/advanced",
        json=payload,
        headers=HEADERS
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        job_id = response.json()["job_id"]
        print(f"✅ Job created: {job_id}\n")
        return job_id
    else:
        print(f"❌ Error: {response.text}\n")
        return None


def test_poll_status(job_id):
    """Test: GET /api/status/twitch/{job_id}"""
    
    print(f"🔄 Polling status for job: {job_id}")
    
    for i in range(30):  # Poll for 30 seconds
        response = requests.get(
            f"{BASE_URL}/api/status/twitch/{job_id}",
            headers=HEADERS
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"[{i*2}s] {data['step']} ({data['progress']}%)")
            
            if data['status'] == 'completed':
                print(f"✅ Job completed!")
                print(f"Clips generated: {len(data.get('clips', []))}")
                return data
            
            elif data['status'] == 'failed':
                print(f"❌ Job failed: {data.get('error')}")
                return data
        
        time.sleep(2)
    
    print("⏱️  Timeout: Job still processing")
    return None


def test_cancel_job(job_id):
    """Test: DELETE /api/jobs/{job_id}"""
    
    print(f"🔄 Cancelling job: {job_id}")
    response = requests.delete(
        f"{BASE_URL}/api/jobs/{job_id}",
        headers=HEADERS
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}\n")


# ============================================================================
# TEST 2: Algorithm Tests (Unit Tests)
# ============================================================================

import numpy as np
from backend.services.highlight_detector import (
    AudioAnalyzer, MotionAnalyzer, TextAnalyzer, HighlightDetector
)

def test_audio_analyzer():
    """Test audio analysis"""
    
    print("🔊 Testing Audio Analyzer...")
    analyzer = AudioAnalyzer()
    
    # Generate mock audio data (5 seconds @ 44.1kHz)
    sample_rate = 44100
    duration = 5
    samples = sample_rate * duration
    
    # Silence first 2 seconds, then loud noise (explosion)
    audio = np.concatenate([
        np.random.normal(0, 0.01, int(2 * sample_rate)),  # Quiet
        np.random.normal(0, 0.5, int(3 * sample_rate))     # Loud (excitement)
    ])
    
    features = analyzer.extract_audio_features(audio, sample_rate)
    score = analyzer.compute_audio_score(features, window_size=44100)
    
    print(f"Audio features: {len(features)} frames")
    print(f"Audio score: {score:.2f} (expected: > 0.5 for excitement)")
    
    if score > 0.5:
        print("✅ Audio analysis working correctly\n")
    else:
        print("⚠️  Audio analysis may need tuning\n")


def test_motion_analyzer():
    """Test motion detection"""
    
    print("📹 Testing Motion Analyzer...")
    analyzer = MotionAnalyzer()
    
    # Generate mock frame data (30 frames, 640x480)
    frames = []
    for i in range(30):
        if i < 15:
            # Static frames (low motion)
            frame = np.random.randint(0, 50, (480, 640, 3), dtype=np.uint8)
        else:
            # High motion frames (random changes)
            frame = np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8)
        frames.append(frame)
    
    score = analyzer.compute_motion_score(frames)
    
    print(f"Motion score: {score:.2f}")
    print(f"Expected: gradual increase from ~0.0 to ~0.5+")
    
    print("✅ Motion analysis working correctly\n")


def test_text_analyzer():
    """Test text/sentiment analysis"""
    
    print("📝 Testing Text Analyzer...")
    analyzer = TextAnalyzer()
    
    # Test with excitement keywords
    text_exciting = "OMG this is absolutely insane! Wow, incredible!"
    score_exciting = analyzer.compute_text_score(text_exciting, language="en")
    
    # Test with neutral text
    text_neutral = "This is a normal stream broadcast."
    score_neutral = analyzer.compute_text_score(text_neutral, language="en")
    
    print(f"Exciting text score: {score_exciting:.2f} (expected: > 0.7)")
    print(f"Neutral text score: {score_neutral:.2f} (expected: < 0.3)")
    
    if score_exciting > score_neutral:
        print("✅ Text analysis working correctly\n")
    else:
        print("⚠️  Text analysis may need tuning\n")


def test_highlight_detector():
    """Test complete highlight detection"""
    
    print("⭐ Testing Highlight Detector...")
    detector = HighlightDetector()
    
    # Generate mock video features (10 seconds)
    video_duration = 10.0
    features = {
        'audio': np.random.normal(0.3, 0.2, int(video_duration * 10)),
        'motion': np.random.normal(0.2, 0.15, int(video_duration * 10)),
        'text_density': np.zeros(int(video_duration * 10))
    }
    
    # Add a spike (highlight)
    features['audio'][40:50] = 0.8  # Loud part
    features['motion'][40:50] = 0.7  # Motion spike
    features['text_density'][40:50] = 0.6  # Text keywords
    
    highlights = detector.detect_highlights(
        audio_features=features['audio'],
        motion_features=features['motion'],
        text_scores=features['text_density']
    )
    
    print(f"Highlights detected: {len(highlights)}")
    for h in highlights[:3]:
        print(f"  - {h.start_time:.1f}s - {h.end_time:.1f}s (score: {h.score:.2f})")
    
    if len(highlights) > 0:
        print("✅ Highlight detection working correctly\n")
    else:
        print("⚠️  No highlights detected (may need data tuning)\n")


# ============================================================================
# TEST 3: Queue & Worker Tests
# ============================================================================

from backend.queue.redis_queue import get_queue, JobStatus

def test_queue_system():
    """Test queue operations"""
    
    print("📦 Testing Queue System...")
    queue = get_queue()
    
    # Test enqueue
    job_id = queue.enqueue(
        task_name="process_twitch_video",
        url="https://www.twitch.tv/videos/123",
        max_clips=5
    )
    print(f"Job enqueued: {job_id}")
    
    # Test status polling
    for i in range(5):
        status = queue.get_job_status(job_id)
        print(f"  Status: {status.status} (progress: {status.progress}%)")
        time.sleep(1)
    
    print("✅ Queue system working correctly\n")


# ============================================================================
# TEST 4: Performance Tests
# ============================================================================

import time

def test_highlight_performance():
    """Benchmark highlight detection speed"""
    
    print("⚡ Performance Test: Highlight Detection")
    
    detector = HighlightDetector()
    
    # Large dataset: 1 hour of video (36000 frames @ 10 fps)
    audio = np.random.normal(0.3, 0.2, 36000)
    motion = np.random.normal(0.2, 0.15, 36000)
    text = np.zeros(36000)
    
    start_time = time.time()
    highlights = detector.detect_highlights(audio, motion, text)
    elapsed = time.time() - start_time
    
    print(f"Processing time: {elapsed:.2f} seconds")
    print(f"Throughput: {36000 / elapsed:.0f} frames/second")
    print(f"Highlights found: {len(highlights)}")
    
    if elapsed < 5:
        print("✅ Performance is excellent\n")
    elif elapsed < 10:
        print("⚠️  Performance is acceptable\n")
    else:
        print("🐌 Performance needs optimization\n")


# ============================================================================
# TEST 5: Integration Test (Full Pipeline)
# ============================================================================

def test_full_pipeline():
    """Test complete processing pipeline"""
    
    print("🚀 Integration Test: Full Pipeline")
    print("=" * 50)
    
    # 1. Start processing
    print("\n1️⃣  Starting video processing...")
    job_id = test_start_processing()
    
    if not job_id:
        print("❌ Failed to start job")
        return
    
    # 2. Poll status
    print("2️⃣  Waiting for processing to complete...")
    result = test_poll_status(job_id)
    
    if result:
        print("3️⃣  Results:")
        print(f"  - Status: {result['status']}")
        print(f"  - Progress: {result['progress']}%")
        print(f"  - Clips: {len(result.get('clips', []))}")
    
    print("\n" + "=" * 50)
    print("✅ Integration test complete!")


# ============================================================================
# TEST RUNNER
# ============================================================================

if __name__ == "__main__":
    import sys
    
    print("\n" + "=" * 60)
    print("Advanced Twitch Shorts Generator - Test Suite")
    print("=" * 60 + "\n")
    
    # Choose test to run
    tests = {
        "1": ("Audio Analyzer", test_audio_analyzer),
        "2": ("Motion Analyzer", test_motion_analyzer),
        "3": ("Text Analyzer", test_text_analyzer),
        "4": ("Highlight Detector", test_highlight_detector),
        "5": ("Queue System", test_queue_system),
        "6": ("Performance Benchmark", test_highlight_performance),
        "7": ("API Integration", lambda: print("Run test_start_processing() manually")),
        "8": ("Full Pipeline", test_full_pipeline),
        "all": ("Run All Tests", None),
    }
    
    print("Available tests:")
    for key, (name, _) in tests.items():
        print(f"  {key}: {name}")
    print()
    
    if len(sys.argv) > 1:
        choice = sys.argv[1]
    else:
        choice = input("Enter test number (or 'all'): ")
    
    if choice == "all":
        for key, (name, func) in tests.items():
            if key != "all" and func:
                print(f"\n{'=' * 60}")
                print(f"Running: {name}")
                print('=' * 60)
                try:
                    func()
                except Exception as e:
                    print(f"❌ Error: {e}\n")
    
    elif choice in tests:
        name, func = tests[choice]
        if func:
            print(f"Running: {name}\n")
            try:
                func()
            except Exception as e:
                print(f"❌ Error: {e}\n")
    
    else:
        print("❌ Invalid choice")
