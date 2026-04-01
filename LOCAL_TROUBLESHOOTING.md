# 🛠️ Dépannage Local - Troubleshooting Guide

## Problèmes Courants en Développement Local

### 1. ❌ "Twitch API credentials not configured"

**Symptôme:**
```
POST /api/twitch/vods HTTP/1.1" 500 Internal Server Error
Twitch API credentials not configured on server (TWITCH_CLIENT_ID / TWITCH_CLIENT_SECRET)
```

**Solutions (par ordre de facilité):**

#### Option A: Sync depuis Railway (✅ EASIEST)
```bash
chmod +x sync_twitch_from_railway.sh
./sync_twitch_from_railway.sh
```

#### Option B: Configuration manuelle
Ajouter à votre `.env`:
```env
TWITCH_CLIENT_ID=your_client_id_from_twitch_console
TWITCH_CLIENT_SECRET=your_client_secret_from_twitch_console
```

Où obtenir ces valeurs: https://dev.twitch.tv/console/apps

#### Option C: Utiliser le script automatique
```bash
chmod +x setup_twitch_local.sh
./setup_twitch_local.sh
```

---

### 2. ❌ "Database error / SQLite not found"

**Symptôme:**
```
sqlalchemy.exc.ArgumentError: Could not parse SQLAlchemy URL
```

**Solution:**
Assurez-vous que votre `.env` a:
```env
DATABASE_URL=sqlite+aiosqlite:///./data/app.db
```

Vérifiez que `aiosqlite` est installé:
```bash
pip install aiosqlite
```

---

### 3. ❌ "Backend won't start / Port 8000 already in use"

**Symptôme:**
```
OSError: [Errno 48] Address already in use
```

**Solutions:**

A) Tuer le processus sur le port:
```bash
lsof -i :8000
kill -9 <PID>
```

B) Utiliser un port différent:
```bash
.venv/bin/python -m uvicorn backend.main:app --port 8001
```

C) Redémarrer complètement:
```bash
# Arrêter avec Ctrl+C
# Attendre 5 secondes
# Redémarrer
make backend
```

---

### 4. ❌ "yt-dlp / aria2 not found"

**Symptôme:**
```
ERROR: aria2c is not installed
ERROR: yt-dlp not found
```

**Solutions:**

Installer les dépendances:
```bash
# macOS
brew install yt-dlp aria2

# Linux (Ubuntu/Debian)
sudo apt-get install yt-dlp aria2

# Linux (Fedora)
sudo dnf install yt-dlp aria2
```

Vérifier l'installation:
```bash
yt-dlp --version
aria2c --version
```

---

### 5. ❌ "Google OAuth fails locally"

**Symptôme:**
```
redirect_uri_mismatch
```

**Solution:**
Assurez-vous que votre `.env` a:
```env
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
```

Et que cette URL est ajoutée dans Google OAuth Console.

---

### 6. ❌ "Download fails: ERROR: Interrupted by user"

**Symptôme:**
```
CalledProcessError: Command '[...yt-dlp...]' returned non-zero exit status 1
```

**Causes possibles:**

1. **aria2c crash**: Vérifiez `YTDLP_DOWNLOADER_ARGS`
   ```bash
   # En .env, essayez des valeurs plus conservatrices:
   YTDLP_DOWNLOADER_ARGS=aria2c:-x4 -s4 -k1M
   ```

2. **Réseau instable**: Vérifiez votre connexion internet

3. **VOD supprimée/privée**: Le VOD Twitch n'existe peut-être plus

---

### 7. ❌ "Frontend can't reach backend"

**Symptôme:**
```
CORS error / Cannot connect to http://localhost:8000
```

**Solutions:**

1. Vérifiez que le backend tourne:
   ```bash
   curl http://localhost:8000/docs
   ```

2. Vérifiez le FRONTEND_URL dans `.env`:
   ```env
   FRONTEND_URL=http://localhost:5173
   ```

3. Vérifiez le VITE_API_URL dans frontend:
   ```bash
   echo $VITE_API_URL  # Devrait être http://localhost:8000
   ```

---

### 8. ❌ "npm install fails"

**Symptôme:**
```
npm ERR! gyp ERR! build error
npm ERR! node-gyp rebuild failed
```

**Solution:**
Nettoyer et réinstaller:
```bash
cd frontend-react
rm -rf node_modules package-lock.json
npm cache clean --force
npm install
```

---

## ✅ Checklist pour démarrer localement

- [ ] `.env` est configuré correctement
- [ ] `TWITCH_CLIENT_ID` et `TWITCH_CLIENT_SECRET` sont présents
- [ ] `DATABASE_URL=sqlite+aiosqlite:///./data/app.db`
- [ ] Backend démarre: `make backend` (ou `npm run dev:backend`)
- [ ] Frontend démarre: `make frontend` (ou `npm run dev:frontend`)
- [ ] http://localhost:5173 est accessible
- [ ] http://localhost:8000/docs est accessible
- [ ] Vous pouvez vous connecter avec Google OAuth
- [ ] Vous pouvez chercher des VODs Twitch

---

## 🔍 Commandes de Diagnostic

### Vérifier les logs du backend
```bash
tail -f uvicorn.log
```

### Vérifier les variables d'environnement
```bash
echo $TWITCH_CLIENT_ID
echo $DATABASE_URL
grep "TWITCH_CLIENT" .env
```

### Tester la connexion à la DB
```bash
python -c "from backend.database import get_db; print('✓ DB Connection OK')"
```

### Tester les credentials Twitch
```bash
python -c "
import os
client_id = os.environ.get('TWITCH_CLIENT_ID')
client_secret = os.environ.get('TWITCH_CLIENT_SECRET')
if client_id and client_secret:
    print(f'✓ Twitch credentials OK')
    print(f'  Client ID: {client_id[:10]}...')
else:
    print('❌ Twitch credentials missing')
"
```

### Vérifier les services tiers
```bash
# Groq
python -c "import groq; print('✓ Groq OK')"

# yt-dlp
yt-dlp --version

# aria2
aria2c --version
```

---

## 🚀 Quick Recovery

Si rien ne marche, essayez ceci:

```bash
# 1. Nettoyer
rm -rf .venv venv data/tmp/* data/app.db
rm frontend-react/node_modules

# 2. Réinstaller
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd frontend-react
npm install
cd ..

# 3. Configurer
cp .env.clean .env
./sync_twitch_from_railway.sh  # ou ./setup_twitch_local.sh

# 4. Relancer
make backend   # Terminal 1
make frontend  # Terminal 2
```

---

## 📞 Contacter le support

Si le problème persiste:

1. Vérifiez les logs: `tail -f uvicorn.log`
2. Vérifiez les erreurs frontend: Ouvrez DevTools (F12)
3. Vérifiez `.env` n'a pas de typos
4. Essayez la "Quick Recovery" ci-dessus

---

**Dernière mise à jour:** 1er avril 2026
