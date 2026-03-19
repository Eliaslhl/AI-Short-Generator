# Changements – Auto-Refresh YouTube Cookies

## Résumé

Implémentation d'un système automatique de rafraîchissement des cookies YouTube via Playwright.

**Objectif**: Quand les cookies YouTube expirent et que `yt-dlp` échoue avec "Sign in to confirm you're not a bot", le backend:
1. Détecte l'erreur automatiquement
2. Lance le script Playwright refresher pour exporter de nouveaux cookies
3. Réessaye immédiatement le téléchargement
4. Zéro intervention manuelle

## Fichiers Modifiés

### backend/services/youtube_service.py
- **Ajout**: Fonction `_auto_refresh_and_retry_download()` pour orchestrer le rafraîchissement + retry
- **Ajout**: Cache de rate-limit `_AUTOREFRESH_RATELIMIT_CACHE` (1 tentative par job par heure)
- **Modification**: Deux blocs d'erreur ("Sign in to confirm...") maintenant appellent la fonction auto-refresh avant de lever une exception
- **Imports**: Ajout de `time` et `Optional` (pour la gestion du rate-limit)

### backend/api/routes.py
- **Ajout**: Endpoint `POST /api/debug/refresh-cookies` pour tester manuellement le rafraîchissement
  - Exécute le script Playwright
  - Retourne les diagnostics sûrs (size + sha256, pas les cookies)
  - Utile pour diagnostiquer les problèmes sans attendre l'expiration naturelle des cookies

## Fichiers Ajoutés

### scripts/setup_youtube_profile.py
Script interactif pour préparer un profil Playwright persistant avec session YouTube authentifiée.

```bash
python3 scripts/setup_youtube_profile.py --profile ~/.youtube_browser_profile
```

Guidé interactivement: ouvre un navigateur, tu te connectes à YouTube, le script exporte les cookies.

### scripts/COOKIES_README.md
Documentation complète sur:
- Configuration du système
- Utilisation des scripts
- Dépannage
- Déploiement en production

### scripts/REFRESH_README.md (existant, maintenant complété)
Documentation du script refresher Playwright et du wrapper one-off.

### scripts/refresh_oneoff.sh (créé précédemment)
Wrapper qui orchestre:
1. Chargement de l'env depuis `scripts/refresh.env`
2. Exécution du refresher Playwright
3. Optionnel: test canary yt-dlp
4. Parsing et affichage des diagnostics sûrs

### scripts/refresh.env.example (créé précédemment)
Modèle d'environnement à personnaliser et utiliser pour les one-offs.

## Comportement Nouveau en Production

### Cas Nominal (cookies valides)
```
1. Utilisateur: lance un téléchargement
2. Backend: charge les cookies depuis env
3. yt-dlp: succès, vidéo téléchargée
```

### Cas Nouveau (cookies expirés)
```
1. Utilisateur: lance un téléchargement
2. Backend: charge les cookies depuis env
3. yt-dlp: échoue avec "Sign in to confirm you're not a bot"
4. Backend (AUTO):
   a. Détecte l'erreur "Sign in"
   b. Lance le script Playwright refresher (si auto-refresh enabled)
   c. Parse la ligne WROTE (size + sha256)
   d. Réessaye yt-dlp avec nouveaux cookies
5. Résultat: succès (no manual intervention)
```

### Erreur de Rate-Limit
```
- Si un job a déjà tenté une auto-refresh < 1 heure avant
- La deuxième tentative est bloquée (rate-limit)
- Message: "Auto-refresh was rate-limited. Cookies may have expired; try again in Xs."
```

## Variables d'Environnement

### Nouvelles (optionnelles, recommandées)
- `YOUTUBE_ENABLE_AUTO_REFRESH=true|false` (défaut: false) — active l'auto-refresh automatique
- `YOUTUBE_BROWSER_PROFILE_DIR=/path/to/profile` — profil Playwright persistant avec session YouTube
- `YOUTUBE_AUTO_REFRESH_OUT=/path/to/cookies.txt` (défaut: `/tmp/yt_cookies_autorefresh.txt`) — où écrire les cookies rafraîchis
- `YOUTUBE_AUTO_REFRESH_HEADLESS=true|false` (défaut: true) — lancer le navigateur en headless
- `YOUTUBE_AUTO_REFRESH_CANARY=https://...` (optionnel) — vidéo pour valider les cookies après refresh

### Existantes (toujours supportées)
- `YOUTUBE_COOKIES_B64` ou `YOUTUBE_COOKIES_B64_PART_*` — cookies en base64
- `YOUTUBE_COOKIES_FILE` — chemin à un fichier cookies.txt
- `YOUTUBE_COOKIES_DEBUG` — log safe diagnostics (size + sha256)

## Workflow Recommandé en Prod

1. **Une fois (setup)**: Créer un profil Playwright avec session authentifiée
   ```bash
   python3 scripts/setup_youtube_profile.py --profile /data/youtube_profile
   ```
   Résultat: profil contenant les cookies et la session YouTube

2. **Déploiement**: Inclure Playwright dans l'image Docker
   ```dockerfile
   RUN pip install -r scripts/requirements-playwright.txt && \
       python3 -m playwright install
   ```

3. **Env vars**: Configurer le profil et activer l'auto-refresh
   ```bash
   YOUTUBE_ENABLE_AUTO_REFRESH=true
   YOUTUBE_BROWSER_PROFILE_DIR=/data/youtube_profile
   YOUTUBE_AUTO_REFRESH_OUT=secrets/youtube_cookies.txt
   YOUTUBE_AUTO_REFRESH_HEADLESS=true
   ```

4. **Rotation initiale**: Fournir des cookies valides (via env ou fichier)
   ```bash
   # Ou utiliser le profil créé à l'étape 1
   ```

5. **Maintenance**: Auto-refresh gère le renouvellement automatique quand cookies expirent ✓

## Diagnostics & Tests

### Test manuel du refresh (via endpoint debug)
```bash
curl -X POST http://localhost:8080/api/debug/refresh-cookies

# Résponse (succès):
{
  "status": "success",
  "diagnostic": "WROTE /tmp/cookies.txt size=386836 sha256=e634c16f...",
  "profile_dir": "/data/youtube_profile",
  "output_path": "/tmp/youtube_cookies.txt"
}
```

### Logs en production (à chercher)
```
[YTC AUTO-REFRESH] cookies refreshed: ... size=... sha256=...
Bot-check detected; attempting auto-refresh and retry for job <id>
Retrying yt-dlp with refreshed cookies for job <id>
```

## Sécurité & Bonnes Pratiques

✅ **Aucun contenu de cookies dans les logs** — seul size + sha256
✅ **Rate-limit activé** — max 1 refresh par job par heure
✅ **Profil persistant** — réutilise la session authentifiée
✅ **Headless par défaut** — pas d'interface graphique en prod
✅ **Timeout 180s** — évite les attentes infinies

⚠️ **Profil doit être persistant** — sinon refresh échouera (recréation nécessaire)
⚠️ **IP affinity** — refresher + yt-dlp tournent dans le même job (garanti)

## Checklist Déploiement

- [ ] Code poussé (`main` branch)
- [ ] Docker image inclut Playwright + navigateurs
- [ ] Profil Playwright préparé (`setup_youtube_profile.py`)
- [ ] Profil monté/accessible en prod (persistent volume)
- [ ] Env vars configurées (`YOUTUBE_ENABLE_AUTO_REFRESH=true`, etc.)
- [ ] Cookies initiaux fournis (base64 ou fichier)
- [ ] Test: lancer une génération, vérifier les logs
- [ ] Attendre expiration des cookies (~2-5 jours), vérifier auto-refresh se déclenche

## Exemple Complet (Local)

```bash
# 1. Setup profile
python3 scripts/setup_youtube_profile.py --profile ~/.youtube_profile --out ~/.youtube_cookies.txt
# (log in manually when browser opens)

# 2. Test refresher
python3 scripts/refresh_youtube_cookies.py --profile ~/.youtube_profile --out /tmp/test_cookies.txt

# 3. Test yt-dlp with refreshed cookies
yt-dlp --cookies /tmp/test_cookies.txt --skip-download https://www.youtube.com/watch?v=dQw4w9WgXcQ

# 4. Test one-off wrapper
cp scripts/refresh.env.example scripts/refresh.env
# edit scripts/refresh.env: set YOUTUBE_BROWSER_PROFILE_DIR
bash scripts/refresh_oneoff.sh
```

## À Ne Pas Oublier

- Le profil Playwright doit **rester persistant** entre les redémarrages
- Les cookies exportés du profil ont une **durée de vie limitée** (quelques jours à semaines)
- Le refresher a besoin de **Playwright + navigateurs** installés
- Pour tester le refresh manuellement: `curl -X POST /api/debug/refresh-cookies`
