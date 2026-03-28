# 🔌 Guide d'intégration - Prochaines étapes

## ✅ Complété

- ✅ Queue abstraction (RQ + Celery)
- ✅ Highlight detection algorithm
- ✅ Worker task processor
- ✅ API endpoints
- ✅ Documentation architecture

## ⏳ À faire maintenant

### **Phase 1: Intégration API** (5-10 min)

1. **Mettre à jour `backend/main.py`**

```python
# Ajouter ces imports
from backend.api.advanced_routes import advanced_router

# Ajouter cette ligne après les autres include_router()
app.include_router(advanced_router, prefix="/api", tags=["advanced"])
```

### **Phase 2: Dépendances** (2 min)

Ajouter à `backend/requirements.txt`:

```
redis>=4.5.0
rq>=1.13.0          # ou "celery>=5.3.0" si tu préfères Celery
numpy>=1.24.0
librosa>=0.10.0     # Pour audio analysis
ffmpeg-python>=0.2.1
```

### **Phase 3: Configuration** (2 min)

Créer ou mettre à jour `backend/.env`:

```env
# Queue Configuration
QUEUE_BACKEND=rq                     # "rq" ou "celery"
REDIS_URL=redis://localhost:6379/0

# Processing Configuration
CHUNK_DURATION=1800                  # 30 minutes
WINDOW_SIZE=15                       # 15 seconds
WINDOW_OVERLAP=0.5                   # 50% overlap

# Scoring Configuration
AUDIO_WEIGHT=0.5
MOTION_WEIGHT=0.2
TEXT_WEIGHT=0.3
MIN_SCORE_THRESHOLD=0.3
MERGE_THRESHOLD=2.0
```

### **Phase 4: Démarrer les services** (3 min)

```bash
# Terminal 1: Redis (si pas encore actif)
redis-server

# Terminal 2: Worker (adapte selon QUEUE_BACKEND)
# Avec RQ:
rq worker

# Avec Celery:
# celery -A backend.queue.worker worker --loglevel=info

# Terminal 3: FastAPI
cd backend
uvicorn main:app --reload --port 8000
```

### **Phase 5: Test** (2 min)

```bash
# Test POST (start processing)
curl -X POST http://localhost:8000/api/generate/twitch/advanced \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.twitch.tv/videos/123456789",
    "max_clips": 5,
    "language": "en"
  }'

# Test GET (check status)
curl -X GET http://localhost:8000/api/status/twitch/{job_id}

# Test DELETE (cancel)
curl -X DELETE http://localhost:8000/api/jobs/{job_id}
```

---

## 🎯 Implementation Priority

### Must-have (ASAP):
1. ✅ Queue integration
2. ✅ API routes
3. ⏳ Requirements.txt
4. ⏳ .env configuration
5. ⏳ Redis startup script
6. ⏳ Worker startup script

### Should-have (Next):
1. ⏳ Real Twitch VOD download (currently mock)
2. ⏳ Real audio extraction (currently mock)
3. ⏳ Real video segmentation (currently mock)
4. ⏳ Real clip generation (currently mock)

### Nice-to-have (Later):
1. ⏳ Whisper transcription integration
2. ⏳ S3 storage for clips
3. ⏳ Database persistence
4. ⏳ Admin dashboard
5. ⏳ Monitoring/logging

---

## 📝 Current TODOs in code

All marked with `# TODO` in source files:

**backend/queue/worker.py**:
```python
# TODO: Implement real video download
# TODO: Implement real video segmentation
# TODO: Implement real transcription
# TODO: Implement real clip generation using FFmpeg
# TODO: Implement real clip upload
# TODO: Implement database persistence
```

**backend/services/highlight_detector.py**:
```python
# TODO: Replace mock audio with real librosa extraction
# TODO: Replace mock features with real computation
# TODO: Add error handling for edge cases
# TODO: Add logging for debugging
```

---

## 🚀 One-command startup (future)

```bash
# After full implementation, use Docker Compose:
docker-compose up
```

---

## 📊 Next Architecture Decisions

**You need to decide:**

1. **Queue Backend**: RQ or Celery?
   - RQ (simpler, Redis-only) ← Recommended for now
   - Celery (more features, needs broker)

2. **Transcription Service**:
   - OpenAI Whisper (cloud) - costs $
   - Local Whisper (free, uses disk/CPU)
   - Twitch chat integration (if available)

3. **Storage**:
   - Local filesystem (simple)
   - S3 (scalable, costs $)
   - GCS (alternative to S3)

4. **Database**:
   - SQLite (dev only)
   - PostgreSQL (recommended)
   - MongoDB (if NoSQL preferred)

---

## ✨ Ready to integrate?

Let me know when you want to:
1. Run the integration commands
2. Add specific implementations
3. Set up Docker setup
4. Add testing suite

**Recommendation**: Start with **RQ** (simpler than Celery) and mock implementations are already in place to allow testing without real data.
