# 🏗️ Architecture Backend Avancée - Twitch Shorts Generator

## 📋 Vue d'ensemble

Système de traitement **asynchrone** et **parallèle** pour générer des shorts à partir de vidéos Twitch longues (2-6h+).

```
┌─────────────────────────────────────────────────────────┐
│                    API Frontend (React)                 │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  POST /api/generate/twitch/advanced                    │
│  GET  /api/status/twitch/{job_id}                      │
│  DELETE /api/jobs/{job_id}                             │
│                                                         │
├─────────────────────────────────────────────────────────┤
│              FastAPI Main Application                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────┐  ┌──────────────────────────────┐ │
│  │   Redis Queue   │  │   Job Status Tracker         │ │
│  │   (RQ/Celery)   │  │   In-Memory + Redis          │ │
│  └─────────────────┘  └──────────────────────────────┘ │
│                                                         │
├─────────────────────────────────────────────────────────┤
│              Worker Pool (Background Tasks)             │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  Worker 1    │  │  Worker 2    │  │  Worker N    │ │
│  │              │  │              │  │              │ │
│  │ ┌──────────┐ │  │ ┌──────────┐ │  │ ┌──────────┐ │ │
│  │ │ Chunk    │ │  │ │ Chunk    │ │  │ │ Chunk    │ │ │
│  │ │Process   │ │  │ │ Process  │ │  │ │ Process  │ │ │
│  │ └──────────┘ │  │ └──────────┘ │  │ └──────────┘ │ │
│  │              │  │              │  │              │ │
│  │ ┌──────────┐ │  │ ┌──────────┐ │  │ ┌──────────┐ │ │
│  │ │Highlight │ │  │ │Highlight │ │  │ │Highlight │ │ │
│  │ │Detector  │ │  │ │Detector  │ │  │ │Detector  │ │ │
│  │ └──────────┘ │  │ └──────────┘ │  │ └──────────┘ │ │
│  │              │  │              │  │              │ │
│  │ ┌──────────┐ │  │ ┌──────────┐ │  │ ┌──────────┐ │ │
│  │ │ Clip     │ │  │ │ Clip     │ │  │ │ Clip     │ │ │
│  │ │Generator │ │  │ │Generator │ │  │ │Generator │ │ │
│  │ └──────────┘ │  │ └──────────┘ │  │ └──────────┘ │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 🔄 Flux de traitement complet

### 1. **Initiation (Frontend → API)**

```
1. Utilisateur: POST /api/generate/twitch/advanced
   {
     "url": "https://www.twitch.tv/videos/123456789",
     "max_clips": 5,
     "language": "en"
   }

2. API crée un job_id unique
3. Job enqueué dans Redis queue
4. Retour au frontend avec job_id pour polling
```

### 2. **Traitement parallèle (Worker Pool)**

```
Pour chaque chunk (30 min):
  ├─ Extraction vidéo/audio
  ├─ Segmentation en frames
  ├─ Extraction audio
  ├─ Transcription (Whisper)
  ├─ Détection highlights
  │  ├─ Analyse audio (volume, pics)
  │  ├─ Analyse motion (frame diffs)
  │  ├─ Analyse texte (keywords)
  │  └─ Score combiné = 0.5*audio + 0.2*motion + 0.3*text
  ├─ Génération clips
  └─ Upload vers stockage
```

### 3. **Agrégation & Scoring final**

```
Après tous les chunks:
  ├─ Fusion tous highlights
  ├─ Filtre par score (threshold: 30%)
  ├─ Merge proches (~2sec)
  ├─ Ranking global
  ├─ Sélection top N clips
  └─ Retour au frontend
```

---

## 📦 Structure des fichiers

```
backend/
├── queue/
│   ├── __init__.py
│   ├── redis_queue.py         ← Queue abstraction (RQ + Celery)
│   └── worker.py              ← Main worker tasks
│
├── services/
│   └── highlight_detector.py  ← Scoring algorithm
│
└── api/
    └── advanced_routes.py     ← API endpoints
```

---

## 🎯 Algorithme de scoring des highlights

### Score Formula
```
highlight_score = (0.5 × audio_score) + (0.2 × motion_score) + (0.3 × text_score)
```

### 1. **Audio Score** (50% weight)

Détecte l'excitation via:
- **Volume (RMS)**: Force moyenne du signal
- **Pics (Spikes)**: Changements soudains d'intensité

```
audio_score = (0.6 × volume_normalized) + (0.4 × spike_intensity)
```

**Exemple**: Cris, rires, musique forte → score élevé

### 2. **Motion Score** (20% weight)

Détecte les moments visuels intenses:
- **Frame Difference**: Changement rapide d'images
- **Scene Cuts**: Transitions abruptes

```
motion_score = avg(frame_difference_rate)
```

**Exemple**: Gameplay intense, mouvements rapides → score élevé

### 3. **Text Score** (30% weight)

Détecte via keywords et sentiment:
- **Excitement keywords**: "OMG", "Incroyable", "Wow"
- **Negative keywords**: "Sorry", "Fail" (pénalité)

```
text_score = (excitement_density × 0.7) - (negative_density × 0.3)
```

**Exemple**: "OMG this is insane!" → score élevé

### Thresholds & Filtering

```
1. Détection: score > 30% (threshold minimum)
2. Filtering: score > 40% (threshold final)
3. Merging: segments proches < 2sec fusionnés
```

---

## 🔧 Configuration

### Environment Variables

```bash
# Queue backend
QUEUE_BACKEND=rq                          # "rq" ou "celery"
REDIS_URL=redis://localhost:6379/0        # Redis connection

# Processing
CHUNK_DURATION=1800                        # 30 minutes
WINDOW_SIZE=15                             # 15 seconds per analysis
WINDOW_OVERLAP=0.5                         # 50% overlap

# Scoring
AUDIO_WEIGHT=0.5
MOTION_WEIGHT=0.2
TEXT_WEIGHT=0.3
MIN_SCORE_THRESHOLD=0.3                   # 30% minimum
MERGE_THRESHOLD=2.0                       # 2 seconds merge distance
```

---

## 🚀 Installation & Démarrage

### 1. **Dépendances**

```bash
pip install redis rq celery python-dotenv
```

### 2. **Redis Server**

```bash
# MacOS
brew install redis
redis-server

# Docker
docker run -d -p 6379:6379 redis:latest
```

### 3. **Worker Process**

```bash
# Avec RQ
rq worker

# Avec Celery
celery -A backend.queue.worker worker --loglevel=info
```

### 4. **FastAPI Main**

```bash
uvicorn backend.main:app --reload
```

---

## 📊 UI Progress Updates

### Exemple de progression en temps réel

```json
{
  "job_id": "abc-123",
  "status": "processing",
  "progress": 35,
  "step": "Processing chunk 2/8...",
  "details": {
    "phase": "highlight_detection",
    "chunks_completed": 1,
    "chunks_total": 8,
    "highlights_found": 12,
    "clips_generated": 3
  }
}
```

### Phases du processus

1. **Download** (0-10%): `"Downloading video..."`
2. **Segmentation** (10-20%): `"Segmenting into chunks..."`
3. **Processing** (20-75%): `"Processing chunk X/Y..."`
4. **Filtering** (75-85%): `"Filtering highlights..."`
5. **Generation** (85-95%): `"Generating clips..."`
6. **Finalization** (95-100%): `"Complete!"`

---

## 🧪 Testing

### Test endpoint

```bash
# Start processing
curl -X POST http://localhost:8000/api/generate/twitch/advanced \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.twitch.tv/videos/123456789",
    "max_clips": 5,
    "language": "en"
  }'

# Response:
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "progress": 0,
  "step": "Queued for processing..."
}

# Get status (polling)
curl -X GET http://localhost:8000/api/status/twitch/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer {token}"

# Cancel job
curl -X DELETE http://localhost:8000/api/jobs/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer {token}"
```

---

## ⚡ Performance Optimizations

### 1. **Chunking parallèle**
- Divise vidéo en 30-min chunks
- Chaque worker traite 1 chunk indépendamment
- Scalable: ajouter workers = plus fast

### 2. **Streaming vs download**
- Pas de full download
- Stream par chunks
- Réduit RAM/disk usage

### 3. **Garbage collection**
- Chunks supprimés après traitement
- Cache highlights en Redis
- Cleanup automatique

### 4. **Scoring optimisé**
- Calcul incrémenta par fenêtre
- Cache des transcriptions
- Pas de re-traitement

---

## 🔐 Sécurité

✅ **Authentification**: Tous les endpoints nécessitent `get_current_user`
✅ **Rate limiting**: Limiter jobs par utilisateur
✅ **Timeout**: Kill jobs après 6h
✅ **File size limits**: Max 2GB par vidéo
✅ **Storage cleanup**: Auto-delete après 48h

---

## 📈 Métriques

À tracker:
- Temps moyen par chunk
- Score distribution des highlights
- Clips générés / utilisateur / mois
- Queue depth et latence
- Worker utilization

---

## 🎓 Prochaines étapes

1. **Implémentation Whisper** pour transcription en temps réel
2. **Cache Redis** pour résultats intermédiaires
3. **Stockage S3** pour clips générés
4. **Dashboard** pour admin (queue status, workers)
5. **Multi-language keywords** expansion
6. **Emotional detection** (voice analysis)

---

**✅ Architecture production-ready et scalable!**
