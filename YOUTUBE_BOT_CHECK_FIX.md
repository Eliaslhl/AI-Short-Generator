# YouTube Bot-Check Error - Production Fix

## Problem

En production, tu reçois cette erreur:
```
Error: yt-dlp failed after bot-check fallbacks (Bot-check persisted after impersonation/JS fallback attempts.)
and auto-refresh failed: Bot-check detected and auto-refresh is disabled. 
Please configure valid YouTube cookies.
```

## Root Cause

1. YouTube sur datacenter IPs demande une vérification bot
2. Les fallbacks échouent car les dépendances sont manquantes
3. L'auto-refresh n'est PAS activé en production
4. Pas de cookies YouTube configurés

## Solution ✅

### Step 1: Ajouter Playwright aux dependencies

`requirements.txt` a été mis à jour avec:
```
playwright>=1.40.0        # Required for YOUTUBE_ENABLE_AUTO_REFRESH
```

### Step 2: Activer Auto-Refresh en Production

Dans ton configuration Railway, ajoute ces variables d'environnement:

```env
YOUTUBE_ENABLE_AUTO_REFRESH=true
YOUTUBE_AUTO_REFRESH_HEADLESS=true
YOUTUBE_AUTO_REFRESH_OUT=/tmp/yt_cookies_refreshed.txt
```

### Step 3: Déployer

```bash
# 1. Installer la nouvelle dépendance localement
pip install playwright>=1.40.0

# 2. Installer les navigateurs Playwright
playwright install chromium

# 3. Commit et push les changements
git add requirements.txt backend/api/advanced_routes.py
git commit -m "🔧 Add Playwright for YouTube auto-refresh and fix queue imports"
git push origin main
```

## How It Works

Avec `YOUTUBE_ENABLE_AUTO_REFRESH=true`:

1. Lors du premier téléchargement YouTube:
   - yt-dlp tente le téléchargement normal
   - Si bot-check → erreur
   - `refresh_youtube_cookies.py` s'exécute automatiquement
   - Playwright lance un navigateur headless
   - Accède à YouTube et obtient des cookies valides
   - Les cookies sont cachés et réutilisés
   - Retry du téléchargement avec les nouveaux cookies ✅

2. Les cookies refreshés sont réutilisés pour:
   - Tous les téléchargements suivants
   - Pendant 1 heure avant prochain refresh (rate-limited)

## Alternative: Manual Cookies (If Auto-Refresh Fails)

Si l'auto-refresh échoue, tu peux exporter manuellement les cookies:

### Sur ta machine locale (avec YouTube ouvert):

```bash
# 1. Exporte les cookies via extension EditThisCookie
# Ou utilise cookies.txt si ton navigateur l'exporte

# 2. Encode en base64
cat cookies.txt | base64 | pbcopy

# 3. Crée la variable d'environnement en Railway:
YOUTUBE_COOKIES_B64="<contenu_base64>"

# Ou si la base64 est trop grande, utilise des parties:
YOUTUBE_COOKIES_B64_PART_1="<partie_1>"
YOUTUBE_COOKIES_B64_PART_2="<partie_2>"
# etc.
```

## Troubleshooting

### Erreur: "Playwright not found"

```bash
# Dans le conteneur, besoin d'ajouter les browsers:
playwright install chromium
```

Tu peux aussi créer un script post-build:
```dockerfile
# Dockerfile
RUN pip install -r requirements.txt
RUN playwright install chromium
```

### Erreur: "Auto-refresh timeout"

Augmente le timeout (default 180s):
```env
YOUTUBE_AUTO_REFRESH_TIMEOUT=300
```

### Erreur: "Browser profile not found"

Si tu veux utiliser un profil existant pour les cookies:
```env
YOUTUBE_BROWSER_PROFILE_DIR=/path/to/chrome/profile
```

### Valider les cookies après refresh

```env
YOUTUBE_AUTO_REFRESH_CANARY=https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

Le script testera sur cette vidéo après refresh.

## Environment Variables Summary

| Variable | Value | Required | Purpose |
|----------|-------|----------|---------|
| `YOUTUBE_ENABLE_AUTO_REFRESH` | `true` | ✅ | Activer le refresh auto des cookies |
| `YOUTUBE_AUTO_REFRESH_HEADLESS` | `true` | ⚠️ | Headless mode (rec. pour prod) |
| `YOUTUBE_AUTO_REFRESH_OUT` | `/tmp/yt_cookies_refreshed.txt` | ❌ | Où sauver les cookies refreshés |
| `YOUTUBE_COOKIES_B64` | `<base64>` | ❌ | Cookies manuels (override auto) |
| `YOUTUBE_BROWSER_PROFILE_DIR` | `/path/to/profile` | ❌ | Profile Chrome/Chromium custom |

## Files Modified

1. **requirements.txt**
   - Added: `playwright>=1.40.0`
   - Purpose: Enable YouTube cookie auto-refresh

2. **backend/api/advanced_routes.py**
   - Fixed: `backend.queue` → `backend.task_queue` imports
   - Reason: Avoid stdlib queue module shadowing

## Next Steps

1. ✅ Deploy updated `requirements.txt` to Railway
2. ✅ Set env vars in Railway dashboard
3. ✅ Trigger a redeploy
4. ✅ Test YouTube download again
5. ✅ Monitor logs for "YTC AUTOREFRESH" messages

## Testing Locally

```bash
# Activer auto-refresh localement
export YOUTUBE_ENABLE_AUTO_REFRESH=true
export YOUTUBE_AUTO_REFRESH_HEADLESS=true

# Lancer un téléchargement
python test_payment_flow.py --plan PRO --platform youtube

# Ou directement via l'API:
curl -X POST http://localhost:8080/api/generate \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=...", "platform": "youtube"}'
```

## Logs to Expect

Si ça marche, tu devrais voir:
```
[YTC AUTOREFRESH] wrote /tmp/yt_cookies_refreshed.txt size=4521 sha256=abc123...
Using YouTube cookies for download (file=/tmp/yt_cookies_refreshed.txt, temp=True)
Running yt-dlp for job xxx: https://www.youtube.com/watch?v=...
```

## Reference

- [yt-dlp Bot-Check FAQ](https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp)
- [Playwright Documentation](https://playwright.dev/python/)
- [YouTube Cookies Export Guide](docs/YOUTUBE_COOKIES.md)
