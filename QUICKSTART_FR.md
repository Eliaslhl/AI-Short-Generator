# Démarrage rapide

Ce guide démarre l’API, le frontend et le worker RQ depuis la racine du dépôt.

## Prérequis

- Python 3.11+
- Node.js 18+
- Redis (pour le flux Twitch avancé)
- FFmpeg

## Installation locale

```bash
cd ai-shorts-generator
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m spacy download en_core_web_sm

cd frontend-react
npm install
cd ..
```

Créez un fichier `.env` local à partir de `.env.example`. Pour le développement :

```dotenv
APP_ENVIRONMENT=development
FRONTEND_URL=http://localhost:5173
SESSION_HASH_KEY=CHANGE_ME_WITH_A_RANDOM_VALUE
```

Ne versionnez jamais ce fichier ni des clés, cookies ou mots de passe réels.

Par défaut, le développement utilise SQLite dans `data/app.db`. Pour PostgreSQL,
définissez `DATABASE_URL` avec une URL `postgresql+asyncpg://…` et appliquez les
migrations avant de démarrer le service :

```bash
PYTHONPATH=. .venv/bin/alembic upgrade head
```

RQ utilise `REDIS_URL` et pointe par défaut vers `redis://localhost:6379/0`.
Définissez cette variable dans l’environnement du worker si vous n’utilisez pas
cette instance locale.

## Démarrer les services

Dans trois terminaux depuis la racine du dépôt :

```bash
redis-server
```

```bash
.venv/bin/rq worker
```

```bash
.venv/bin/uvicorn backend.main:app --reload --port 8000
```

Puis démarrez le frontend :

```bash
cd frontend-react
npm run dev
```

L’API est disponible sur `http://localhost:8000` et le frontend sur
`http://localhost:5173`.

## Authentification navigateur

Le navigateur utilise une session opaque dans un cookie `HttpOnly`. Il ne stocke
ni JWT ni Bearer token. Un client frontend doit utiliser `credentials: "include"`
pour les appels qui nécessitent une session.

Les requêtes mutatives authentifiées exigent une origine autorisée. Avec `curl`,
connectez-vous d’abord dans un cookie jar générique :

```bash
curl --cookie-jar cookies.txt \
  --header 'Content-Type: application/json' \
  --request POST http://localhost:8000/auth/login \
  --data '{"email":"<EMAIL>","password":"<MOT_DE_PASSE>"}'
```

Réutilisez ensuite ce fichier et envoyez l’en-tête `Origin` sur les mutations
authentifiées :

```bash
curl --cookie cookies.txt \
  --header 'Origin: http://localhost:5173' \
  --header 'Content-Type: application/json' \
  --request POST http://localhost:8000/auth/logout
```

Le contrat actuel applique l’Origin, sans en-tête CSRF séparé.

## Twitch avancé

Seules les URL VOD Twitch canoniques sont acceptées, par exemple
`<TWITCH_VOD_URL>` (`https://www.twitch.tv/videos/<id>`). Les URL de chaînes,
les domaines ressemblants, les ports non canoniques et les URL avec query ou
fragment sont refusés. Le traitement passe par RQ et consomme le quota Twitch.

```bash
curl --cookie cookies.txt \
  --header 'Origin: http://localhost:5173' \
  --header 'Content-Type: application/json' \
  --request POST http://localhost:8000/api/generate/twitch/advanced \
  --data '{"url":"<TWITCH_VOD_URL>","max_clips":5,"language":"en"}'
```

La réponse contient un `job_id`. Interrogez ensuite le job avec le même cookie :

```bash
curl --cookie cookies.txt \
  http://localhost:8000/api/status/twitch/<JOB_ID>
```

Les routes Twitch utiles sont :

- `POST /api/generate/twitch/advanced`
- `GET /api/status/twitch/{job_id}`
- `DELETE /api/jobs/{job_id}`

## Clips privés

Il n’existe pas de mount public `/clips`. Les réponses de statut donnent des URL
média privées de la forme `/api/jobs/{job_id}/clips/{clip_index}/media`.
Elles exigent le cookie de session et vérifient le propriétaire : un autre
utilisateur obtient `404`, un client anonyme `401`.

```bash
# Lecture complète ou partielle (Range)
curl --cookie cookies.txt \
  --header 'Range: bytes=0-1023' \
  http://localhost:8000/api/jobs/<JOB_ID>/clips/0/media --output clip.mp4

# HEAD et téléchargement explicite
curl --cookie cookies.txt --head \
  http://localhost:8000/api/jobs/<JOB_ID>/clips/0/media
curl --cookie cookies.txt \
  'http://localhost:8000/api/jobs/<JOB_ID>/clips/0/media?download=true' \
  --output clip.mp4
```

## Vérifications

```bash
PYTHONPATH=. .venv/bin/pytest -q
cd frontend-react && npm test -- --run && npm run build
```

La documentation interactive reflète l’API réellement montée :
`http://localhost:8000/docs`.
