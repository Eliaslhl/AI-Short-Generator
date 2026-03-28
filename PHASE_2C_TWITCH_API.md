# Phase 2c: Twitch API Integration

## 📺 Overview

This phase implements complete Twitch VOD download and metadata retrieval using:
- **Twitch API** for OAuth2 and VOD information
- **yt-dlp** for reliable video download
- **OpenCV** for video duration detection
- **Worker integration** for seamless processing

## 🎯 What's New

### Files Created/Modified

1. **`backend/services/twitch_client.py`** (NEW - 350+ lines)
   - `TwitchAuthManager`: OAuth2 token management
   - `TwitchClient`: Twitch API operations
   - `VideoDownloadManager`: VOD download and metadata

2. **`backend/queue/worker.py`** (MODIFIED)
   - `_download_twitch_video()`: Download VOD from Twitch
   - `_segment_video()`: Real video segmentation with duration detection
   - Integrated with real audio/motion processors

3. **`backend/.env`** (MODIFIED)
   - Added Twitch API credentials
   - Added download configuration

## 🔐 Setup: Getting Twitch Credentials

### Option A: Automated Setup
```bash
cd ai-shorts-generator
bash scripts/setup_twitch.sh
```

### Option B: Manual Setup

1. **Create Twitch Developer Application**
   - Go to https://dev.twitch.tv/console/apps
   - Click "Create Application"
   - Fill in:
     - **Name**: AI-Shorts-Generator
     - **OAuth Redirect URL**: `http://localhost:8000/auth/twitch/callback`
     - **Category**: Application Integration
   - Accept ToS and Create

2. **Get Credentials**
   - Click "Manage" on your app
   - Copy **Client ID** and **Client Secret**

3. **Update `.env`**
   ```env
   TWITCH_CLIENT_ID=your_client_id
   TWITCH_CLIENT_SECRET=your_client_secret
   TWITCH_REDIRECT_URI=http://localhost:8000/auth/twitch/callback
   ```

## 📚 API Reference

### TwitchAuthManager

Manages OAuth2 tokens with automatic refresh:

```python
from backend.services.twitch_client import TwitchAuthManager

auth = TwitchAuthManager()
token = auth.get_app_access_token()  # Auto-refreshes if expired
headers = auth.get_auth_headers()     # Get headers for API requests
```

### TwitchClient

Main Twitch API operations:

#### Get User by Login
```python
client = TwitchClient()
user = client.get_user_by_login("username")
# Returns: {
#   "id": "123456789",
#   "login": "username",
#   "profile_image_url": "...",
#   ...
# }
```

#### Get User's VODs
```python
vods = client.get_vods(
    user_id="123456789",
    limit=10,
    period="week",      # all, day, week, month
    sort="views"        # time, trending, views
)
# Returns: List of VOD dicts with metadata
```

#### Get VOD by ID
```python
vod = client.get_vod_by_id("vod_id")
# Returns: {
#   "id": "123456789",
#   "title": "Epic Gaming Session",
#   "description": "...",
#   "duration": "03h45m12s",
#   "created_at": "2024-03-27T...",
#   "url": "https://twitch.tv/videos/123456789",
#   ...
# }
```

#### Parse Twitch URLs
```python
# Supports multiple URL formats
urls = [
    "https://twitch.tv/videos/123456789",
    "https://www.twitch.tv/videos/123456789",
    "123456789",
    "https://twitch.tv/username",
    "https://twitch.tv/clip/clip_name",
]

for url in urls:
    parsed = client.parse_twitch_url(url)
    # Returns: {
    #   "type": "vod" | "clip" | "channel",
    #   "id": "...",        # For vod/clip
    #   "username": "..."   # For channel
    # }
```

### VideoDownloadManager

Handles VOD download and file operations:

```python
manager = VideoDownloadManager(output_dir="/tmp/twitch_downloads")

# Download VOD
video_path = manager.download_twitch_vod(
    video_url="https://twitch.tv/videos/123456789",
    vod_id="123456789"
)
# Returns: "/tmp/twitch_downloads/vod_123456789.mp4"

# Get video duration
duration_seconds = manager.get_video_duration(video_path)
# Returns: 13512.5 (3.75 hours)
```

## 🔄 Processing Flow

```
POST /api/generate/twitch/advanced
  ↓
_download_twitch_video()
  ├─ Parse Twitch URL
  ├─ Get VOD metadata (optional)
  └─ Download with yt-dlp → /tmp/vod_*.mp4
  ↓
_segment_video()
  ├─ Get duration with OpenCV
  ├─ Calculate chunks (30 min default)
  └─ Create chunk metadata
  ↓
_process_chunk()  [for each chunk]
  ├─ RealAudioProcessor (librosa)
  │   ├─ RMS energy
  │   ├─ Spike detection
  │   ├─ MFCC features
  │   └─ Spectral features
  ├─ MotionProcessor (OpenCV)
  │   ├─ Frame differences
  │   ├─ Scene detection
  │   └─ Optical flow
  └─ HighlightDetector
      └─ Combines features → Highlight scores
  ↓
Best highlights selected → Clips generated
```

## 🧪 Testing

### Test Twitch Connection
```python
from backend.services.twitch_client import create_twitch_client

client = create_twitch_client()

# Test user lookup
user = client.get_user_by_login("twitch")
print(f"User ID: {user['id']}")

# Test VOD fetch
vods = client.get_vods(user['id'], limit=5)
for vod in vods:
    print(f"  - {vod['title']} ({vod['duration']})")
```

### Test VOD Download
```python
from backend.services.twitch_client import create_download_manager

manager = create_download_manager()

# Download a VOD
video_path = manager.download_twitch_vod(
    video_url="https://twitch.tv/videos/XXXXXXXXX",
    vod_id="XXXXXXXXX"
)
print(f"Downloaded: {video_path}")

# Check duration
duration = manager.get_video_duration(video_path)
print(f"Duration: {duration/60:.1f} minutes")
```

### Test Full Pipeline
```bash
# Start with example VOD URL
curl -X POST http://localhost:8000/api/generate/twitch/advanced \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://twitch.tv/videos/XXXXXXXXX",
    "max_clips": 5,
    "language": "en"
  }'
```

## 🛠️ Environment Variables

```env
# Twitch API
TWITCH_CLIENT_ID=              # Your Twitch app client ID
TWITCH_CLIENT_SECRET=          # Your Twitch app client secret
TWITCH_REDIRECT_URI=           # OAuth callback URL

# Video Download
VIDEO_DOWNLOAD_DIR=/tmp/twitch_downloads
MAX_VIDEO_SIZE_GB=50           # Max file size limit

# Processing (from Phase 2b)
CHUNK_DURATION=1800            # 30 minutes
WINDOW_SIZE=15                 # 15 seconds
WINDOW_OVERLAP=0.5             # 50%
```

## ⚙️ Configuration

### Quality Tiers

Choose download quality based on needs:

```python
# In twitch_client.py, VideoDownloadManager.download_twitch_vod()
ydl_opts = {
    "format": "best[ext=mp4]",     # Best quality
    # or: "bestvideo+bestaudio/best"  # Separate audio/video merge
    # or: "worst[ext=mp4]"            # Fastest download
}
```

### Timeout Settings

Adjust for network conditions:

```python
# In TwitchClient
response = requests.get(url, timeout=10)  # 10 seconds

# In VideoDownloadManager
ydl_opts = {
    "socket_timeout": 30,  # 30 seconds
}
```

## 🚨 Troubleshooting

### "401 Unauthorized" - Credentials Invalid
- Verify Client ID and Secret are correct
- Regenerate credentials if needed
- Check that app hasn't been deleted

### "403 Forbidden" - Missing Scopes
- Update TWITCH_SCOPES in .env
- Required scopes may depend on endpoint

### "Download Failed" - yt-dlp Issues
- Update yt-dlp: `pip install --upgrade yt-dlp`
- Check VOD is public/accessible
- Verify disk space available

### "Video duration detection failed"
- Ensure OpenCV is installed: `pip install opencv-python`
- Check file is valid MP4 format
- Try with different video file

## 📊 Performance Notes

### Download Speed
- Depends on Twitch CDN and your connection
- Typical: 5-50 MB/s
- 1 hour video ≈ 2-10 minutes download

### Segmentation
- Real-time using OpenCV duration detection
- 30-min chunks default
- Automatically handles final partial chunk

### Processing
- Parallel chunk processing via RQ
- Each chunk independently: ~1-5 min (varies)
- Audio/motion features: ~10-30 sec per chunk

## 🔗 Related Phases

- **Phase 2a**: Integrated routes and environment
- **Phase 2b**: Real audio/motion processors (librosa + OpenCV)
- **Phase 2c**: ✅ Twitch API integration (THIS)
- **Phase 2d**: Clip generation (FFmpeg)
- **Phase 2e**: Frontend integration

## 📖 Resources

- Twitch API Docs: https://dev.twitch.tv/docs/api
- yt-dlp GitHub: https://github.com/yt-dlp/yt-dlp
- OAuth2 Flow: https://dev.twitch.tv/docs/authentication/getting-tokens

## ✅ Checklist

- [ ] Twitch app created on https://dev.twitch.tv/console/apps
- [ ] Client ID and Secret obtained
- [ ] `.env` updated with credentials
- [ ] `twitch_client.py` imports successfully
- [ ] Test user lookup works
- [ ] Test VOD fetch works
- [ ] Test download works
- [ ] API endpoints tested

---

**Status**: ✅ Phase 2c Complete - Twitch Integration Ready!
