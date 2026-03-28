# Quick Reference: Phase 2c - Twitch API Integration

## 🎯 In 60 Seconds

**What**: Twitch VOD download + real audio/motion processing  
**Files**: `twitch_client.py` (350 lines)  
**Setup**: Get Twitch credentials, update `.env`  
**Status**: ✅ COMPLETE

---

## 🚀 Quick Start

### 1. Get Credentials
```bash
# Go to https://dev.twitch.tv/console/apps
# Create app → Get Client ID & Secret
```

### 2. Update Environment
```bash
# Edit backend/.env
TWITCH_CLIENT_ID=your_id
TWITCH_CLIENT_SECRET=your_secret
```

### 3. Test It
```bash
cd ai-shorts-generator
python3 -c "from backend.services.twitch_client import TwitchClient; \
c = TwitchClient(); \
print(c.parse_twitch_url('https://twitch.tv/videos/123456789'))"
```

---

## 📦 Components at a Glance

| Component | Purpose | Key Methods |
|-----------|---------|------------|
| **TwitchAuthManager** | OAuth2 | `get_app_access_token()`, `get_auth_headers()` |
| **TwitchClient** | API Operations | `get_user_by_login()`, `get_vods()`, `get_vod_by_id()`, `parse_twitch_url()` |
| **VideoDownloadManager** | Download | `download_twitch_vod()`, `get_video_duration()` |
| **Worker** | Integration | `_download_twitch_video()`, `_segment_video()`, `_process_chunk()` |

---

## 💻 Code Examples

### Parse URLs
```python
from backend.services.twitch_client import TwitchClient

client = TwitchClient()

urls = [
    "https://twitch.tv/videos/123456789",
    "123456789",
    "https://twitch.tv/pokimane"
]

for url in urls:
    result = client.parse_twitch_url(url)
    print(result)
    # {'type': 'vod', 'id': '123456789'}
    # {'type': 'vod', 'id': '123456789'}
    # {'type': 'channel', 'username': 'pokimane'}
```

### Get User Info
```python
user = client.get_user_by_login("pokimane")
print(user['id'])  # User ID
print(user['login'])  # Username
```

### List VODs
```python
vods = client.get_vods(
    user_id="123456789",
    limit=10,
    period="week",
    sort="views"
)
for vod in vods:
    print(f"{vod['title']} - {vod['duration']}")
```

### Download VOD
```python
from backend.services.twitch_client import create_download_manager

manager = create_download_manager()
video_path = manager.download_twitch_vod(
    video_url="https://twitch.tv/videos/123456789",
    vod_id="123456789"
)
print(video_path)  # /tmp/twitch_downloads/vod_123456789.mp4

# Get duration
duration = manager.get_video_duration(video_path)
print(f"Duration: {duration/60:.1f} minutes")
```

---

## 🔄 Full Pipeline

```
POST /api/generate/twitch/advanced
  ├─ Input: {"video_url": "https://twitch.tv/videos/...", ...}
  ├─ TwitchClient: Parse & validate URL
  ├─ VideoDownloadManager: Download VOD (3-8 min/hour)
  ├─ _segment_video(): Split into 30-min chunks
  ├─ For each chunk (parallel):
  │   ├─ RealAudioProcessor: Extract audio features
  │   ├─ MotionProcessor: Extract motion features
  │   └─ HighlightDetector: Score highlights
  └─ Return: Best clips + metadata
```

---

## ⚙️ Configuration

```env
# backend/.env
TWITCH_CLIENT_ID=your_client_id
TWITCH_CLIENT_SECRET=your_client_secret
TWITCH_REDIRECT_URI=http://localhost:8000/auth/twitch/callback

VIDEO_DOWNLOAD_DIR=/tmp/twitch_downloads
MAX_VIDEO_SIZE_GB=50
```

---

## 🧪 Testing Commands

### Test imports
```bash
python3 -c "from backend.services.twitch_client import *; print('✅ Ready')"
```

### Test URL parsing
```bash
python3 << 'EOF'
from backend.services.twitch_client import TwitchClient
client = TwitchClient()
print(client.parse_twitch_url("https://twitch.tv/videos/123456789"))
EOF
```

### Test API call
```bash
curl -X POST http://localhost:8000/api/generate/twitch/advanced \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://twitch.tv/videos/XXXXXXXXX",
    "max_clips": 5,
    "language": "en"
  }'
```

---

## 🛠️ Setup Script

```bash
# Run automated setup
bash scripts/setup_twitch.sh

# Follow prompts:
# 1. Enter TWITCH_CLIENT_ID
# 2. Enter TWITCH_CLIENT_SECRET
# 3. Script updates .env and tests
```

---

## 📊 Performance

| Operation | Time |
|-----------|------|
| Token refresh | <1s |
| User lookup | 1-2s |
| VOD list (10) | 2-3s |
| 1hr VOD download | 3-8 min |
| Video duration detect | 1-2s |
| Chunk processing | 1-5 min |

---

## 🔍 Troubleshooting

| Issue | Solution |
|-------|----------|
| "401 Unauthorized" | Check credentials in `.env` |
| "Download failed" | Update yt-dlp: `pip install --upgrade yt-dlp` |
| "Duration detection failed" | Verify OpenCV: `pip install opencv-python` |
| "File not found" | Check `/tmp` has space |

---

## 📚 Full Documentation

- **Complete API**: `PHASE_2C_TWITCH_API.md`
- **Architecture**: `PHASE_2C_COMPLETE.md`
- **Source Code**: `backend/services/twitch_client.py`
- **Worker Integration**: `backend/queue/worker.py`

---

## ✅ Checklist

- [ ] Twitch app created at https://dev.twitch.tv/console/apps
- [ ] Client ID obtained
- [ ] Client Secret obtained
- [ ] `.env` updated with credentials
- [ ] Import test passed
- [ ] URL parsing test passed
- [ ] Download test passed (if VOD available)
- [ ] Full pipeline working

---

## 🎯 Next: Phase 2d

Clip generation with FFmpeg:
- Render clips from highlights
- Combine audio + video
- Add effects/transitions
- Export multiple formats

---

**Status**: ✅ Phase 2c Complete  
**Ready**: Yes, after credentials setup  
**Next**: Phase 2d - Clip Generation
