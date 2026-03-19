# Changements : Auto-Refresh-and-Retry pour les cookies YouTube

## Résumé

Implémentation d'une logique d'auto-rafraîchissement automatique des cookies YouTube quand yt-dlp échoue avec "Sign in to confirm you're not a bot". Le backend détecte l'erreur, lance le script Playwright refresher, et réessaye immédiatement avec les nouveaux cookies — tout dans le même job/processus.

## Fichiers modifiés

### 1. **backend/services/youtube_service.py**
   - **Modification majeure** : ajout de logique auto-refresh-and-retry dans deux blocs de gestion d'erreur (politique "on_error" + fallback général).
   - Quand "Sign in to confirm..." détecté :
     1. Vérifie si `YOUTUBE_ENABLE_AUTO_REFRESH=true`.
     2. Lance le script refresher avec env vars (`YOUTUBE_BROWSER_PROFILE_DIR`, `YOUTUBE_AUTO_REFRESH_OUT`, etc.).
     3. Parse la ligne WROTE pour extraire le SHA et taille (safe logging).
     4. Réessaye yt-dlp avec le fichier cookies actualisé.
   - Si retry réussit : retourne le résultat.
   - Si retry échoue : lève l'erreur originale + suggestions utilisateur.

## Fichiers ajoutés

### 1. **scripts/refresh.env.example**
   - Template d'environnement pour configurer l'auto-refresh.
   - Variables clés :
     - `YOUTUBE_ENABLE_AUTO_REFRESH=true`
     - `YOUTUBE_BROWSER_PROFILE_DIR=/data/youtube_profile`
     - `YOUTUBE_AUTO_REFRESH_OUT=/tmp/yt_cookies.txt`
     - `YOUTUBE_AUTO_REFRESH_HEADLESS=true`
     - `YOUTUBE_AUTO_REFRESH_CANARY=<url>` (optionnel)

### 2. **scripts/refresh_oneoff.sh**
   - Wrapper bash pour exécuter le refresher en one-off.
   - Charge l'env depuis `scripts/refresh.env` (si présent).
   - Exécute le refresher, parse le WROTE line.
   - Optionnellement teste avec yt-dlp canary.
   - Retourne le chemin du fichier cookies ou erreur.

### 3. **scripts/test_autorefresh_logic.py**
   - Tests de validation :
     - Existence et compilation des fichiers clés.
     - Parsing du format WROTE line.
     - Présence du wrapper one-off et du template env.
   - Exécuter : `python3 scripts/test_autorefresh_logic.py`

### 4. **scripts/test_autorefresh_e2e.sh**
   - Test end-to-end simulant le flux complet : refresh → parse → test yt-dlp canary.
   - Exécuter : `bash scripts/test_autorefresh_e2e.sh`

### 5. **scripts/AUTOREFRESH_DEPLOYMENT.md**
   - Documentation complète en français :
     - Vue d'ensemble du système.
     - Étapes d'activation en production.
     - Guide de test local.
     - Dépannage et bonnes pratiques.
     - FAQ.

## Flux logique

```
yt-dlp première tentative
        ↓ échoue avec "Sign in..."
        ↓
Backend détecte le pattern
        ↓
YOUTUBE_ENABLE_AUTO_REFRESH=true ?
        ├─ OUI → lance refresher Playwright
        │          ├─ WROTE line parsée → cookies rafraîchis ✓
        │          └─ réessaye yt-dlp avec nouveaux cookies
        │              ├─ Succès → retourne résultat
        │              └─ Échec → retourne erreur
        └─ NON → retourne erreur avec suggestions utilisateur
```

## Activation immédiate

```bash
# 1. Copier et configurer l'env
cp scripts/refresh.env.example scripts/refresh.env
# Éditer YOUTUBE_BROWSER_PROFILE_DIR vers le chemin du profil Playwright loggué

# 2. Test local
python3 scripts/test_autorefresh_logic.py
bash scripts/test_autorefresh_e2e.sh

# 3. Déploiement
git add scripts/refresh.env.example scripts/refresh_oneoff.sh \
        scripts/test_autorefresh_logic.py scripts/test_autorefresh_e2e.sh \
        scripts/AUTOREFRESH_DEPLOYMENT.md backend/services/youtube_service.py
git commit -m "feat: auto-refresh-and-retry for YouTube cookies on 'Sign in' error"
git push origin main

# 4. En production
# Définir en env :
# YOUTUBE_ENABLE_AUTO_REFRESH=true
# YOUTUBE_BROWSER_PROFILE_DIR=/data/youtube_profile
# YOUTUBE_AUTO_REFRESH_OUT=/tmp/yt_cookies.txt
# YOUTUBE_AUTO_REFRESH_HEADLESS=true
```

## Sécurité

- ✓ Aucun contenu de cookies loggé.
- ✓ Seulement taille + SHA256 en logs (pour audit de cohérence).
- ✓ Rate-limit : un seul retry auto-refresh par erreur détectée.
- ✓ Timeout : 180 secondes max pour le refresher (pas de hang infini).

## Vérification

Tests inclus :

```bash
# Validation
python3 scripts/test_autorefresh_logic.py

# E2E (avec profil Playwright loggué)
bash scripts/test_autorefresh_e2e.sh
```

## Rollback

Si besoin de désactiver :

```bash
# Unset ou set à false:
unset YOUTUBE_ENABLE_AUTO_REFRESH
# ou
export YOUTUBE_ENABLE_AUTO_REFRESH=false

# Le backend repassera au mode impersonation seul.
```

## Notes

- **Profil persistant** : recommandé pour robustesse. Pré-loggez une seule fois avec le navigateur, puis réutilisez le profil.
- **Canary** : testez les cookies immédiatement après refresh (optionnel mais utile pour diagnostiquer).
- **Affinité IP** : refresh + retry exécutés depuis le même job/conteneur → garantit même IP/contexte réseau.
