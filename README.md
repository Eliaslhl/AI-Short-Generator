# AI Shorts Generator

> Transform any long YouTube video into **10 viral short clips** — 100 % locally, no paid API needed.

---

## 🎯 Features

| Feature | Tech |
|---|---|
| YouTube download | `yt-dlp` |
| Audio transcription | `Faster-Whisper` (local) |
| Viral scoring | Custom NLP scoring engine |
| Hook generation | `Ollama` (llama3 / mistral) — with rule-based fallback |
| Emoji captions | Built-in keyword dictionary |
| B-roll matching | Local file library |
| Video rendering | `MoviePy` + `ffmpeg` |
| 9:16 portrait format | Automatic crop / pad |
| Web interface | FastAPI + vanilla HTML/CSS/JS |

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
