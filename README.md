# AI Shorts Generator

> Transform any long YouTube video into **viral short clips** — SaaS app with auth, plans, and a full AI pipeline.

---

## 🎯 Features

| Feature | Tech |
|---|---|
| YouTube download | `yt-dlp` |
| Audio transcription | `Faster-Whisper` (local) |
| Viral scoring | Custom NLP scoring engine |
| Hook generation | `Ollama` → `Groq` (free cloud) → rule-based fallback |
| Emoji captions | Built-in keyword dictionary |
| B-roll matching | Local file library |
| Video rendering | `MoviePy` + `ffmpeg` |
| 9:16 portrait format | Automatic crop / pad |
| Auth (JWT + Google OAuth) | FastAPI + SQLAlchemy |
| Plans (Free / Pro) | Stripe integration |
| Password reset | Gmail SMTP via fastapi-mail |
| React frontend | Vite + TypeScript + Tailwind CSS v4 |

---

## 🗂 Project Structure

```
ai-shorts-generator/
├── backend/
│   ├── main.py                       # FastAPI entry point
│   ├── config.py                     # Centralised settings
│   ├── database.py                   # SQLAlchemy async setup
│   ├── api/
│   │   └── routes.py                 # /api/generate, /api/status
│   ├── auth/
│   │   └── router.py                 # JWT, Google OAuth, password reset
│   ├── models/
│   │   └── user.py                   # User, Job, PasswordResetToken
│   ├── services/
│   │   ├── youtube_service.py        # yt-dlp download
│   │   ├── transcription_service.py  # Faster-Whisper
│   │   ├── clip_selector.py          # Segment merging & scoring
│   │   ├── hook_service.py           # Ollama → Groq → rule-based
│   │   ├── email_service.py          # Password reset emails
│   │   ├── emoji_caption_service.py  # Styled captions
│   │   └── broll_service.py          # B-roll matching
│   ├── video/
│   │   └── video_editor.py           # MoviePy rendering pipeline
│   └── ai/
│       ├── viral_scoring.py          # Multi-factor viral score
│       └── keyword_extractor.py      # spaCy + regex fallback
├── frontend-react/                   # React + Vite + TypeScript
│   ├── src/
│   │   ├── pages/                    # Landing, Login, Register, Generator…
│   │   ├── context/AuthContext.tsx   # JWT auth state
│   │   └── api/index.ts              # Axios API client
│   └── package.json
├── scripts/
│   ├── create_pro_user.py            # Create a Pro test user
│   └── test_email.py                 # Test SMTP config
├── data/
│   ├── videos/                       # Downloaded source videos
│   ├── clips/                        # Generated short clips
│   └── broll/                        # B-roll library
├── Makefile                          # Dev shortcuts
├── requirements.txt
└── .env                              # Environment variables
```

---

## ⚙️ Prerequisites

| Tool | Install | Notes |
|---|---|---|
| Python 3.11 | [python.org](https://www.python.org) | Required for backend |
| Node.js 18+ | [nodejs.org](https://nodejs.org) | Required for frontend |
| **FFmpeg 8.0+** | `brew install ffmpeg` | **REQUIRED** for clip generation (libx264, libvpx-vp9, aac codecs needed) |
| Ollama *(optional)* | [ollama.com](https://ollama.com) | Optional: local LLM for hooks |

**Verify FFmpeg installation:**
```bash
# Check FFmpeg is available
ffmpeg -version

# Verify required encoders (libx264, libvpx-vp9, aac)
./scripts/check_ffmpeg.sh
```

---

## 🚀 Quick Start

### 1. Clone & setup Python

```bash
git clone https://github.com/Eliaslhl/AI-Short-Generator.git
cd ai-shorts-generator
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python3.11 -m spacy download en_core_web_sm
```

### 2. Setup frontend

```bash
cd frontend-react
npm install
cd ..
```

### 3. Configure `.env`

Copy and fill in the required values:

```dotenv
FRONTEND_URL=http://localhost:5173
SECRET_KEY=your-random-secret-key

# Email (Gmail App Password)
MAIL_USERNAME=you@gmail.com
MAIL_PASSWORD=xxxx-xxxx-xxxx-xxxx
MAIL_FROM=you@gmail.com
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_STARTTLS=true
MAIL_SSL_TLS=false
MAIL_SUPPRESS_SEND=false

# Groq — free cloud LLM fallback (https://console.groq.com)
GROQ_API_KEY=gsk_...

# Stripe (optional)
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_PRO_PRICE_ID=
```

### 4. Launch

```bash
# Backend (port 8000)
make back

# Frontend (port 5173)
make front
```

Or both at once:

```bash
make back & make front
```

Open **http://localhost:5173** in your browser.

---

## 🤖 Hook Generation — Fallback Chain

Hooks are generated with a 3-level fallback:

```
1. Ollama (local)  →  zero cost, needs Ollama running
2. Groq (cloud)    →  free tier, needs GROQ_API_KEY
3. Rule-based      →  always works, no API needed
```

---

## ⚡ Pipeline

```
YouTube URL
    │
    ▼
[1] yt-dlp          → Download video (best MP4 ≤ 1080p)
    │
    ▼
[2] Faster-Whisper  → Transcribe audio to text + timestamps
    │
    ▼
[3] Clip Selector   → Merge segments → Score → Pick top N
    │                   viral_score = numbers + emotion + questions
    │                              + length + density + duration
    ▼
[4] Hook Generator  → Ollama → Groq → rule-based
    │
    ▼
[5] Caption Builder → Emoji mapping + EMPHASIS + line splitting
    │
    ▼
[6] B-roll Matcher  → keyword → /data/broll/<topic>.mp4
    │
    ▼
[7] Video Editor    → Cut → Crop 9:16 → Hook overlay
                    → Caption overlay → B-roll PiP → Export MP4
```

---

## 🔧 Configuration (`.env`)

| Variable | Default | Description |
|---|---|---|
| `WHISPER_MODEL` | `base` | `tiny` / `base` / `small` / `medium` / `large` |
| `WHISPER_DEVICE` | `cpu` | `cpu` or `cuda` |
| `WHISPER_LANGUAGE` | `en` | `""` for auto-detect |
| `OLLAMA_MODEL` | `llama3` | or `mistral` |
| `GROQ_API_KEY` | — | Free at [console.groq.com](https://console.groq.com) |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Groq model to use |
| `MAX_CLIPS` | `10` | Default max clips per job |
| `MIN_CLIP_DURATION` | `15` | Minimum clip duration (seconds) |
| `MAX_CLIP_DURATION` | `45` | Maximum clip duration (seconds) |

---

## 🛠 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/generate` | Start a generation job |
| `GET` | `/api/status/{job_id}` | Poll job progress |
| `POST` | `/auth/register` | Create an account |
| `POST` | `/auth/login` | Get JWT token |
| `POST` | `/auth/forgot-password` | Send reset email |
| `POST` | `/auth/reset-password` | Set new password |
| `GET` | `/docs` | Swagger UI |

---

## 🧪 Useful Scripts

```bash
# Create a Pro test user (pro@test.com / prouser123)
.venv/bin/python3.11 -m scripts.create_pro_user

# Test email sending
.venv/bin/python3.11 scripts/test_email.py

# Test Groq hook generation
.venv/bin/python3.11 -m scripts.test_forgot_password
```

---

## 🐛 Troubleshooting

| Problem | Solution |
|---|---|
| `ffmpeg not found` | `brew install ffmpeg` |
| Ollama connection refused | Run `ollama serve` — app uses Groq/fallback automatically |
| No clips generated | Video too short or music-only |
| `spaCy model missing` | `.venv/bin/python3.11 -m spacy download en_core_web_sm` |
| Email not received | Check spam — or verify Gmail App Password in `.env` |
| Groq hook not working | Check `GROQ_API_KEY` in `.env` |

---

## 📄 License

MIT – use freely, modify, distribute.


---

## 🗂 Project Structure

```
ai-shorts-generator/
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── config.py                # Centralised settings
│   ├── api/
│   │   └── routes.py            # API endpoints
│   ├── services/
│   │   ├── youtube_service.py   # yt-dlp download
│   │   ├── transcription_service.py  # Faster-Whisper
│   │   ├── clip_selector.py     # Segment merging & scoring
│   │   ├── hook_service.py      # Ollama hook generation
│   │   ├── emoji_caption_service.py  # Styled captions
│   │   └── broll_service.py     # B-roll matching
│   ├── video/
│   │   ├── video_editor.py      # MoviePy rendering pipeline
│   │   └── subtitle_renderer.py # SRT / ASS export
│   └── ai/
│       ├── viral_scoring.py     # Multi-factor viral score
│       └── keyword_extractor.py # spaCy + regex fallback
├── frontend/
│   ├── index.html               # Single-page app
│   ├── style.css                # Dark glassmorphism UI
│   └── script.js                # Polling + clip rendering
├── data/
│   ├── videos/                  # Downloaded source videos
│   ├── clips/                   # Generated short clips
│   └── broll/                   # Your B-roll library
├── requirements.txt
├── setup.sh                     # One-time setup
└── run.sh                       # Start the server
```

---

## ⚙️ Prerequisites

| Tool | Install |
|---|---|
| Python 3.9+ | [python.org](https://www.python.org) |
| ffmpeg | `brew install ffmpeg` / `apt install ffmpeg` |
| Ollama *(optional)* | [ollama.com](https://ollama.com) |

---

## 🚀 Quick Start

### 1. Clone & setup

```bash
git clone <repo-url>
cd ai-shorts-generator
bash setup.sh
```

The setup script will:
- Create a `.venv` virtual environment
- Install all Python packages
- Download the spaCy English model
- Create a default `.env` file

### 2. (Optional) Start Ollama

```bash
# Pull a model (one-time)
ollama pull llama3     # or: ollama pull mistral

# Start the server (runs on port 11434 by default)
ollama serve
```

> ℹ️ If Ollama is not running, the app automatically falls back to a rule-based hook generator. All other features work without Ollama.

### 3. Run the server

```bash
bash run.sh
```

### 4. Open the app

Navigate to **http://localhost:8000** in your browser.

---

## 🎬 Usage

1. Paste any YouTube URL into the input field
2. Click **Generate Shorts**
3. Watch the progress bar as the pipeline runs
4. Download your clips when done

---

## ⚡ Pipeline

```
YouTube URL
    │
    ▼
[1] yt-dlp          → Download video (best MP4 ≤ 1080p)
    │
    ▼
[2] Faster-Whisper  → Transcribe audio to text + timestamps
    │
    ▼
[3] Clip Selector   → Merge segments → Score → Pick top 10
    │                   viral_score = numbers + emotion + questions
    │                              + length + density + duration
    ▼
[4] Hook Generator  → Ollama LLM → viral hook sentence per clip
    │
    ▼
[5] Caption Builder → Emoji mapping + EMPHASIS + line splitting
    │
    ▼
[6] B-roll Matcher  → keyword → /data/broll/<topic>.mp4
    │
    ▼
[7] Video Editor    → Cut → Crop 9:16 → Hook overlay
                    → Caption overlay → B-roll PiP → Export MP4
```

---

## 🔧 Configuration

Edit `.env` to override defaults:

```dotenv
OLLAMA_MODEL=llama3          # or mistral
WHISPER_MODEL=base           # tiny | base | small | medium | large
WHISPER_DEVICE=cpu           # cpu | cuda
WHISPER_LANGUAGE=en          # or "" for auto-detect
MAX_CLIPS=10
MIN_CLIP_DURATION=15         # seconds
MAX_CLIP_DURATION=45         # seconds
```

---

## 📚 Adding B-roll

Drop short MP4 clips into `/data/broll/` named after their topic:

```
data/broll/
├── technology.mp4
├── money.mp4
├── space.mp4
├── health.mp4
└── nature.mp4
```

The `broll_service.py` will automatically match keywords from transcript segments to these files.

---

## 🛠 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/generate` | Start a generation job |
| `GET` | `/api/status/{job_id}` | Poll job progress |
| `GET` | `/api/clips/{job_id}` | List finished clips |
| `GET` | `/clips/{job_id}/{file}` | Download a clip file |
| `GET` | `/docs` | Interactive Swagger UI |

### POST /api/generate

```json
// Request
{ "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ" }

// Response
{ "job_id": "a1b2c3d4", "message": "Job started." }
```

### GET /api/status/{job_id}

```json
{
  "job_id": "a1b2c3d4",
  "status": "processing",   // pending | processing | done | error
  "progress": 65,
  "step": "Rendering clip 3/10…",
  "clips": []
}
```

---

## 🐛 Troubleshooting

| Problem | Solution |
|---|---|
| `ffmpeg not found` | Install ffmpeg and make sure it's on your PATH |
| `Ollama connection refused` | Run `ollama serve` or the app uses fallback hooks |
| `No clips generated` | Video may be too short or heavily music-only |
| `spaCy model missing` | Run `python -m spacy download en_core_web_sm` |
| `Font not found` (MoviePy) | Install Arial or change `FONT` in `video_editor.py` |
| Clips are portrait with bars | Normal — source is landscape, auto-cropped to 9:16 |

---

## 📄 License

MIT – use freely, modify, distribute.
