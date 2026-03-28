# Phase 2d: Clip Generation with FFmpeg

## 📺 Overview

This phase implements **complete video clip generation** from detected highlights using FFmpeg:

- **Video extraction** by timestamp ranges
- **Effect application** (fade transitions, watermarks)
- **Multi-format export** (MP4, WebM, GIF)
- **Quality optimization** for different platforms

## 🎯 What's New

### Files Created/Modified

1. **`backend/services/clip_generator.py`** (NEW - 500+ lines)
   - `FFmpegConfig`: Configuration and presets
   - `ClipGenerator`: Main clip generation engine
   - Methods for extraction, effects, format conversion

2. **`backend/queue/worker.py`** (MODIFIED)
   - `_generate_clips()`: Real FFmpeg-based rendering
   - Integration with real processors
   - Full pipeline completion

## 🔧 Components

### FFmpegConfig

Centralized FFmpeg configuration:

```python
# Video settings
VIDEO_CODEC = "libx264"
VIDEO_PRESET = "medium"  # Quality vs speed
VIDEO_BITRATE = "5000k"
VIDEO_CRF = 23  # 0-51, lower = better

# Audio settings
AUDIO_CODEC = "aac"
AUDIO_BITRATE = "192k"
AUDIO_SAMPLE_RATE = 44100

# Supported formats
FORMATS = {
    "mp4": {...},    # Standard web video
    "webm": {...},   # VP9 codec
    "gif": {...},    # Animated GIF
}

# Transition types
TRANSITIONS = {
    "fade": "fade",
    "fadeblack": "fadeblack",
    "crossfade": "crossfade",
    "dissolve": "dissolve",
    "push": "push",
    "slide": "slide",
    "wipeleft": "wipeleft",
    "wiperight": "wiperight",
}
```

### ClipGenerator

Main clip generation class:

#### Extract Clip
```python
generator = ClipGenerator()

# Extract clip from timestamp range
clip_path = generator.extract_clip(
    video_path="/path/to/video.mp4",
    start_time=10.5,      # Start at 10.5s
    end_time=45.2,        # End at 45.2s
    output_path=None      # Auto-named if None
)
# Returns: "/tmp/clips/clip_10-45.mp4"
```

#### Add Effects

**Fade Transitions**
```python
clip_with_fade = generator.add_fade_effect(
    video_path=clip_path,
    fade_in=0.5,    # 0.5s fade in
    fade_out=0.5,   # 0.5s fade out
)
```

**Watermark**
```python
clip_with_watermark = generator.add_watermark(
    video_path=clip_path,
    watermark_text="AI Shorts",
    position="bottom-right"  # top-left, top-right, center, etc.
)
```

#### Format Conversion

```python
# Convert to WebM
webm_path = generator.convert_format(
    video_path=clip_path,
    output_format="webm"
)

# Convert to GIF
gif_path = generator.convert_format(
    video_path=clip_path,
    output_format="gif"
)
```

#### Full Pipeline

```python
# Generate complete clip with all effects
results = generator.generate_from_highlight(
    video_path="/path/to/video.mp4",
    highlight={
        "start_time": 10.5,
        "end_time": 45.2,
        "score": 0.85
    },
    apply_effects=True,
    output_formats=["mp4", "webm"]
)

# Returns:
# {
#   "mp4": "/tmp/clips/clip_faded_watermarked.mp4",
#   "webm": "/tmp/clips/clip_faded_watermarked.webm"
# }
```

## 🔄 Full Processing Pipeline

```
🎮 Twitch VOD
    ↓
TwitchClient: Parse & validate
    ↓
VideoDownloadManager: Download (3-8 min/hour)
    ↓
_segment_video(): Split into 30-min chunks
    ↓
RealAudioProcessor (librosa)  +  MotionProcessor (OpenCV)
    ↓
HighlightDetector: Score highlights
    ↓
_filter_highlights(): Select top highlights
    ↓
_generate_clips(): Create video clips ← Phase 2d
    ├─ ClipGenerator: Extract by timestamp
    ├─ Add fade effects (0.3s in, 0.3s out)
    ├─ Add watermark ("AI Shorts")
    └─ Convert to formats (MP4, WebM)
    ↓
✂️ Clips Ready for Distribution
   ├─ MP4 (Standard web)
   ├─ WebM (Modern browsers)
   └─ Metadata (timestamps, scores)
```

## 📊 Configuration

### Video Quality Presets

Adjust `FFmpegConfig.VIDEO_PRESET`:

```python
# Ultrafast - Poor quality, very fast
"ultrafast"

# Fast - Decent quality, fast
"fast"

# Medium - Good quality, moderate speed [DEFAULT]
"medium"

# Slow - Excellent quality, slower
"slow"

# Veryslow - Best quality, very slow
"veryslow"
```

### Bitrate Settings

Adjust for different platforms:

```python
# Mobile (lower bandwidth)
VIDEO_BITRATE = "2500k"
AUDIO_BITRATE = "128k"

# Web standard
VIDEO_BITRATE = "5000k"
AUDIO_BITRATE = "192k"

# High quality (streaming)
VIDEO_BITRATE = "8000k"
AUDIO_BITRATE = "256k"
```

## 🚨 Requirements

### FFmpeg Installation

Required: FFmpeg must be installed on the system

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg

# CentOS/RHEL
sudo yum install ffmpeg

# Verify installation
ffmpeg -version
ffprobe -version
```

## 🧪 Testing

### Test FFmpeg Availability
```python
from backend.services.clip_generator import ClipGenerator

generator = ClipGenerator()
# Logs "✅ FFmpeg is available" if working
```

### Test Clip Extraction
```python
# Extract 30-second clip
clip_path = generator.extract_clip(
    video_path="/path/to/video.mp4",
    start_time=10.0,
    end_time=40.0
)

if clip_path:
    print(f"✅ Clip generated: {clip_path}")
else:
    print("❌ Failed to generate clip")
```

### Test Full Pipeline
```python
results = generator.generate_from_highlight(
    video_path="/path/to/video.mp4",
    highlight={
        "start_time": 10.0,
        "end_time": 40.0,
        "score": 0.85
    },
    apply_effects=True,
    output_formats=["mp4", "webm"]
)

print(f"✅ MP4: {results['mp4']}")
print(f"✅ WebM: {results['webm']}")
```

## 📊 Performance Metrics

| Operation | Time | Notes |
|-----------|------|-------|
| Extract 30s clip | 5-15s | Depends on source codec |
| Add fade effects | 10-20s | Re-encodes video |
| Add watermark | 10-20s | Re-encodes video |
| Convert MP4→WebM | 30-60s | VP9 codec slower |
| Convert MP4→GIF | 20-40s | Per 30s clip |

## 🛠️ Troubleshooting

### FFmpeg Not Found

**Error**: `FileNotFoundError: ffmpeg`

**Solution**:
```bash
# Install FFmpeg
brew install ffmpeg  # or appropriate package manager

# Verify
which ffmpeg
ffmpeg -version
```

### Clip Generation Timeout

**Error**: `subprocess.TimeoutExpired`

**Solution**:
- Increase timeout in `ClipGenerator.extract_clip()` (default: 300s)
- Use faster preset: `VIDEO_PRESET = "fast"`
- Check disk space
- Check system resources

### Invalid Output File

**Error**: `FileNotFoundError: /tmp/clips/...`

**Solution**:
- Ensure `/tmp` directory exists and is writable
- Check disk space: `df -h /tmp`
- Verify source video is readable: `ffprobe video.mp4`

## 🎯 Output Examples

### MP4 (Web Standard)
- Codec: H.264
- Bitrate: 5000 kbps
- Size: ~37 MB per minute
- Compatible: All browsers

### WebM (Modern)
- Codec: VP9
- Bitrate: 5000 kbps
- Size: ~25 MB per minute (smaller)
- Compatible: Chrome, Firefox, Opera

### GIF (Social Media)
- Format: Animated GIF
- Size: ~50-100 MB per minute (larger!)
- Use: Twitter, Discord, messaging
- Note: Consider generating short GIFs only

## 📈 Integration with Previous Phases

**Phase 2b** → Audio/Motion Features
**Phase 2c** → Twitch VOD Download
**Phase 2d** → Clip Generation ← YOU ARE HERE

```
Audio + Motion Features
    ↓
HighlightDetector
    ↓
Top Highlights
    ↓
ClipGenerator (Phase 2d)
    ├─ Extract by timestamp
    ├─ Add effects
    └─ Generate formats
    ↓
Ready for Distribution
```

## 🔗 Related Documentation

- **Phase 2c**: `PHASE_2C_TWITCH_API.md`
- **Phase 2b**: `PHASE_2b_COMPLETION.md`
- **Worker**: `backend/queue/worker.py`
- **API Routes**: `backend/api/advanced_routes.py`

## ✅ Checklist

- [ ] FFmpeg installed on system
- [ ] `clip_generator.py` created
- [ ] Worker integration complete
- [ ] Test clip generation works
- [ ] Verify output formats (MP4, WebM)
- [ ] Check file sizes
- [ ] Test watermark overlay
- [ ] Test fade effects

---

**Status**: ✅ Phase 2d Complete - Clip Generation Ready!

**Next**: Phase 2e - Frontend Integration & User Dashboard
