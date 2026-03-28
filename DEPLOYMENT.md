# 🚀 Production Deployment Guide

## Deployment Options

### Option 1: Docker Compose (Development → Staging)

```bash
# Build images
docker-compose build

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api worker_1 worker_2

# Scale workers
docker-compose up -d --scale worker=5

# Shutdown
docker-compose down
```

### Option 2: Kubernetes (Enterprise)

```bash
# Apply manifests
kubectl apply -f k8s/

# Check deployments
kubectl get deployments
kubectl get pods
kubectl logs -f deployment/worker

# Scale workers
kubectl scale deployment worker --replicas=10
```

### Option 3: Cloud Platforms

#### **Azure Container Instances**
```bash
# Create resource group
az group create --name videoshort-rg --location eastus

# Create registry
az acr create --resource-group videoshort-rg \
  --name videoshortacr --sku Basic

# Push images
docker tag videoshort:api videoshortacr.azurecr.io/api:latest
az acr build --registry videoshortacr --image api:latest .

# Deploy
az container create --resource-group videoshort-rg \
  --name api \
  --image videoshortacr.azurecr.io/api:latest \
  --registry-login-server videoshortacr.azurecr.io
```

#### **AWS ECS**
```bash
# Create cluster
aws ecs create-cluster --cluster-name videoshort

# Create task definition
aws ecs register-task-definition --cli-input-json file://task-definition.json

# Create service
aws ecs create-service --cluster videoshort \
  --service-name api \
  --task-definition api:1 \
  --desired-count 2
```

#### **Google Cloud Run**
```bash
# Build and push
gcloud builds submit --tag gcr.io/PROJECT_ID/api

# Deploy
gcloud run deploy api \
  --image gcr.io/PROJECT_ID/api \
  --platform managed \
  --region us-central1
```

---

## Environment Configuration

### Production (.env)

```env
# Security
JWT_SECRET=your-super-secret-key-here
ALLOWED_ORIGINS=https://yourdomain.com

# Database
DATABASE_URL=postgresql://user:password@db.example.com/videoshort

# Redis (managed service)
REDIS_URL=redis://redis.c123.ng.0001.use1.cache.amazonaws.com:6379/0

# Queue
QUEUE_BACKEND=rq
CELERY_BROKER_URL=redis://redis.c123.ng.0001.use1.cache.amazonaws.com:6379/0

# Processing
CHUNK_DURATION=1800
WORKERS_COUNT=8
MAX_QUEUE_SIZE=1000

# Scoring
AUDIO_WEIGHT=0.5
MOTION_WEIGHT=0.2
TEXT_WEIGHT=0.3

# Storage
STORAGE_TYPE=s3  # or "gcs", "local"
S3_BUCKET=videoshort-clips
S3_REGION=us-east-1
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...

# API Keys
TWITCH_CLIENT_ID=...
TWITCH_CLIENT_SECRET=...
OPENAI_API_KEY=...  # For Whisper transcription

# Monitoring
SENTRY_DSN=https://...@sentry.io/...
LOG_LEVEL=INFO
```

---

## Monitoring & Logging

### Prometheus Metrics

```yaml
# Add to FastAPI
from prometheus_client import Counter, Histogram
import time

request_count = Counter('requests_total', 'Total requests')
request_duration = Histogram('request_duration_seconds', 'Request duration')
jobs_processed = Counter('jobs_processed_total', 'Total jobs processed')
jobs_failed = Counter('jobs_failed_total', 'Total failed jobs')
queue_depth = Gauge('queue_depth', 'Current queue depth')
```

### ELK Stack Logging

```python
# backend/logging_config.py
import logging
from pythonjsonlogger import jsonlogger

handler = logging.FileHandler('logs/app.log')
formatter = jsonlogger.JsonFormatter()
handler.setFormatter(formatter)
logger = logging.getLogger()
logger.addHandler(handler)
```

### Health Checks

```python
# backend/api/health.py
@app.get("/health")
async def health():
    redis_ok = await check_redis()
    queue_ok = await check_queue()
    return {
        "status": "healthy" if redis_ok and queue_ok else "unhealthy",
        "redis": "ok" if redis_ok else "error",
        "queue": "ok" if queue_ok else "error"
    }
```

---

## Performance Tuning

### RQ Configuration

```python
# backend/queue/redis_queue.py
job_timeout = 3600  # 1 hour
result_ttl = 86400  # 24 hours
worker_ttl = 300    # 5 minutes
connection_pool_kwargs = {
    'max_connections': 50,
    'retry_on_timeout': True
}
```

### Database Optimization

```sql
-- Add indexes for faster queries
CREATE INDEX idx_job_status ON jobs(status, created_at DESC);
CREATE INDEX idx_user_jobs ON jobs(user_id, created_at DESC);
CREATE INDEX idx_video_chunks ON video_chunks(job_id, sequence);
```

### Caching Strategy

```python
# Cache frequently accessed data
@cache.cached(timeout=3600)
def get_video_metadata(video_id):
    return db.query(Video).filter_by(id=video_id).first()
```

---

## Database Schema

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE jobs (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    url VARCHAR(2048) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    step VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT
);

CREATE TABLE clips (
    id UUID PRIMARY KEY,
    job_id UUID REFERENCES jobs(id),
    start_time FLOAT,
    end_time FLOAT,
    score FLOAT,
    audio_score FLOAT,
    motion_score FLOAT,
    text_score FLOAT,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE highlights (
    id UUID PRIMARY KEY,
    job_id UUID REFERENCES jobs(id),
    chunk_index INTEGER,
    start_time FLOAT,
    end_time FLOAT,
    score FLOAT,
    reason VARCHAR(255)
);

CREATE TABLE video_chunks (
    id UUID PRIMARY KEY,
    job_id UUID REFERENCES jobs(id),
    sequence INTEGER,
    start_time FLOAT,
    end_time FLOAT,
    status VARCHAR(50),
    result_url VARCHAR(2048)
);
```

---

## CI/CD Pipeline

### GitHub Actions

```yaml
name: Deploy

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Build Docker images
        run: docker-compose build
      
      - name: Push to registry
        run: |
          docker login -u ${{ secrets.REGISTRY_USER }} -p ${{ secrets.REGISTRY_PASS }}
          docker push $IMAGE_NAME:latest
      
      - name: Deploy to production
        run: |
          kubectl set image deployment/api \
            api=$IMAGE_NAME:latest \
            --record
```

---

## Troubleshooting

### Queue Issues

```bash
# Check queue depth
rq info

# Clear failed jobs
rq empty failed

# Monitor workers
rq-dashboard --port 9181

# Check Redis
redis-cli
> INFO
> DBSIZE
> FLUSHDB  # WARNING: Clears everything
```

### Performance Issues

```bash
# Check worker bottleneck
top -p $(pgrep -f rq)

# Monitor Redis memory
redis-cli INFO memory

# Analyze slow queries
redis-cli --slowlog get 10
```

### Debugging

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Tail logs
docker logs -f videoshort_api
docker logs -f videoshort_worker_1

# SSH into container
docker exec -it videoshort_api bash
```

---

## Scaling Strategy

### Horizontal Scaling

```
Low traffic:     1 API + 2 workers
Medium traffic:  2 API + 4 workers
High traffic:    3+ API + 8+ workers
```

### Vertical Scaling

- Add more CPU/RAM to single instances
- Use larger Redis instance (m3 → m5 → m6g)
- Database replication for read scaling

### Cost Optimization

```
- Use spot instances for workers
- Auto-scale based on queue depth
- Cache aggressively
- Use CDN for clips
- Delete old clips after 30 days
```

---

## Backup & Recovery

```bash
# Backup Redis
redis-cli BGSAVE

# Backup database
pg_dump videoshort > backup.sql

# Restore
psql videoshort < backup.sql

# Create snapshots
aws ec2 create-snapshot --volume-id vol-123
```

---

## Next Steps

1. ✅ Docker Compose setup
2. ✅ Environment configuration
3. ⏳ Database setup
4. ⏳ Redis managed service (AWS ElastiCache)
5. ⏳ Monitoring dashboard
6. ⏳ Auto-scaling policies
7. ⏳ Backup automation

**Recommended for launch:**
- Start with Docker Compose on single server
- Migrate to Kubernetes when traffic > 100 req/min
- Use AWS/GCP managed services for Redis + DB
