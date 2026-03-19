# Auto-Refresh des Cookies YouTube — Guide de déploiement

## Vue d'ensemble

Le système détecte automatiquement quand yt-dlp échoue avec l'erreur **"Sign in to confirm you're not a bot"** (cookies expirés ou invalides) et :

1. Lance le script Playwright `refresh_youtube_cookies.py` pour regénérer un fichier cookies.txt valide.
2. **Réessaye immédiatement** yt-dlp avec les nouveaux cookies, **dans le même job/processus** (garantit affinité réseau/IP).
3. Retourne le résultat au client — **sans intervention manuelle**.

Cette approche élimine le besoin de relancer manuellement le refresher toutes les quelques jours.

---

## Architecture

### Composants

| Fichier | Rôle |
|---------|------|
| `scripts/refresh_youtube_cookies.py` | Script Playwright qui exporte les cookies du navigateur en format Netscape ; imprime une ligne safe `WROTE <path> size=<bytes> sha256=<hex>`. |
| `scripts/refresh_oneoff.sh` | Wrapper bash : lance le refresher, parse la sortie, optionnellement exécute un canary yt-dlp. |
| `scripts/refresh.env.example` | Template d'environnement à copier et adapter. |
| `backend/services/youtube_service.py` | Modifié pour intégrer auto-refresh-and-retry dans les deux chemins de gestion d'erreur (politique "on_error" + fallback). |
| `scripts/test_autorefresh_logic.py` | Tests de validation. |

### Flux en production

```
1. API reçoit une demande de téléchargement yt-dlp
   ↓
2. Première tentative yt-dlp (avec cookies existants ou impersonation)
   ↓
3. yt-dlp échoue → "Sign in to confirm..."
   ↓
4. Backend détecte erreur "Sign in" → lance auto-refresh
   ↓
5. Playwright refresher génère nouveaux cookies (WROTE line)
   ↓
6. Backend réessaye yt-dlp avec nouveaux cookies
   ↓
7. Succès ✓ → retourne métadonnées
   ou
   Échec → retourne erreur originale (user must provide cookies ou résoudre autre problème)
```

---

## Activation en production

### 1. Installer Playwright et les navigateurs

Dans votre image Docker ou avant de déployer :

```bash
python3 -m pip install -r scripts/requirements-playwright.txt
python3 -m playwright install
```

Vérifiez que vous avez assez d'espace disque (~1 GB pour les navigateurs).

### 2. Préparer un profil persistant (optionnel mais recommandé)

Un **profil persistant** contient les cookies stockés du navigateur et peut être réutilisé entre les runs. C'est plus robuste qu'une connexion interactive.

#### Option A : Pre-login une seule fois (local)

```bash
# Sur une machine avec interface graphique:
python3 -u scripts/refresh_youtube_cookies.py \
  --out /tmp/youtube_cookies.txt \
  --profile ~/youtube_profile \
  # (pas de --headless ; un navigateur s'ouvrira)
```

Attendez que le navigateur s'affiche → naviguez sur YouTube → connectez-vous avec votre compte Google.
Fermez le navigateur. Le profil `~/youtube_profile` contient maintenant les cookies persistants.

Puis, transférez ce profil vers un stockage persistant dans votre production (ex: volume Docker, S3, base de données).

#### Option B : Profil en mémoire (plus simple, moins robuste)

Si vous ne pré-loggez qu'une fois :

```bash
python3 -u scripts/refresh_youtube_cookies.py \
  --out /tmp/youtube_cookies.txt \
  # (pas de --profile ; utilise une session ephémère)
```

Un navigateur s'ouvre → loggez-vous → fermez. Les cookies sont écrits et prêts.

### 3. Configurer les variables d'environnement

Définissez les variables dans votre service de déploiement (Railway, Heroku, etc.) :

```bash
# Activer l'auto-refresh
YOUTUBE_ENABLE_AUTO_REFRESH=true

# Chemin vers le profil persistant (doit être persiste ou ré-initialisé)
YOUTUBE_BROWSER_PROFILE_DIR=/data/youtube_profile
# ou un volume Docker: /mnt/profiles/youtube

# Où écrire le fichier cookies (accessible par yt-dlp)
YOUTUBE_AUTO_REFRESH_OUT=/tmp/yt_cookies_refreshed.txt
# ou: /data/youtube_cookies.txt (si sur volume persistant)

# Mode headless (true en prod, false si debug)
YOUTUBE_AUTO_REFRESH_HEADLESS=true

# (Optionnel) Canary : vidéo connue pour tester les cookies après refresh
YOUTUBE_AUTO_REFRESH_CANARY=https://www.youtube.com/watch?v=recHgNtlUjc

# NE PAS définir YOUTUBE_COOKIES_B64 ou PART_* — laisse auto-refresh être appelé.
```

### 4. Déployer

```bash
git add scripts/refresh_youtube_cookies.py scripts/refresh_oneoff.sh \
         scripts/refresh.env.example scripts/test_autorefresh_logic.py \
         scripts/requirements-playwright.txt backend/services/youtube_service.py

git commit -m "feat: auto-refresh-and-retry for YouTube cookies on 'Sign in' error"

git push origin main
```

---

## Test local (avant production)

### Test 1 : Validation de base

```bash
python3 scripts/test_autorefresh_logic.py
```

Doit afficher : `All tests passed! Auto-refresh logic is ready.`

### Test 2 : Exécution du refresher

```bash
# Avec profil pre-loggé
python3 -u scripts/refresh_youtube_cookies.py \
  --out /tmp/test_cookies.txt \
  --profile ~/youtube_profile \
  --headless \
  --canary "https://www.youtube.com/watch?v=recHgNtlUjc"
```

Attendez la ligne :
```
WROTE /tmp/test_cookies.txt size=386836 sha256=e634c16fd8f8b7dc35176ecb80f8510f9393d745c60cc7c1f039c717bc0ee672
CANARY OK
```

### Test 3 : Vérifier que yt-dlp peut utiliser les cookies

```bash
yt-dlp --cookies /tmp/test_cookies.txt \
       --no-warnings --skip-download --dump-json \
       "https://www.youtube.com/watch?v=recHgNtlUjc" | head -20
```

Doit retourner du JSON avec les métadonnées vidéo.

### Test 4 : Simuler erreur "Sign in" → auto-refresh → retry

Pour vérifier que le backend appellera correctement auto-refresh, vous pouvez :

1. Lancer le service avec env auto-refresh activé.
2. Appeler l'endpoint de téléchargement avec une URL YouTube.
3. Vérifier dans les logs qu'aucune erreur "Sign in" ne persiste (elle devrait être récupérée par auto-refresh).

Example simple :

```bash
# Terminal 1 : start service
export YOUTUBE_ENABLE_AUTO_REFRESH=true
export YOUTUBE_BROWSER_PROFILE_DIR=/Users/elias/youtube_profile
export YOUTUBE_AUTO_REFRESH_HEADLESS=true
python3 -m backend.main  # ou votre commande de démarrage du service

# Terminal 2 : appel test
curl -X POST http://localhost:8000/download \
  -H "Content-Type: application/json" \
  -d '{"youtube_url": "https://www.youtube.com/watch?v=recHgNtlUjc", "job_id": "test_123"}'
```

Vérifiez les logs du service pour :
- `[YTC AUTOREFRESH] refreshed cookies: size=... sha256=...` ← auto-refresh a réussi
- Pas d'erreur "Sign in" finale ← retry a réussi

---

## Dépannage

### Problème : "refresh script not found"

- Vérifiez que `scripts/refresh_youtube_cookies.py` est présente dans le répertoire deploié.
- Chemin relatif doit être `<repo>/scripts/refresh_youtube_cookies.py`.

### Problème : "Auto-refresh script failed"

- Vérifiez que Playwright et les navigateurs sont installés : `python3 -m playwright install`.
- Vérifiez les logs d'erreur (stderr du refresher) — souvent : profil invalide, navigateur locked, timeout.

### Problème : "WROTE line produced but file not found"

- Vérifiez que `YOUTUBE_AUTO_REFRESH_OUT` est accessible en écriture par le processus.
- Vérifiez les permissions du répertoire.

### Problème : Canary échoue mais WROTE réussit

- Les cookies générés sont syntaxiquement corrects mais ne fonctionnent pas pour YouTube.
- Cela peut indiquer : profil expiré, session IP mismatch, cookies qui manquent des tokens de long-terme.
- **Solution** : Reconnectez-vous dans le profil (ouvrez le navigateur manuellement une fois, loggez-vous, fermez).

### Problème : "yt-dlp retry with refreshed cookies failed"

- Les nouveaux cookies aussi ne fonctionnent pas.
- Possibilités :
  1. Les cookies du profil sont obsolètes → reconnectez-vous.
  2. L'adresse IP du rafraîchissement est différente de celle de yt-dlp → assurez-vous qu'ils s'exécutent dans le même job/conteneur.
  3. YouTube a besoin de signaux supplémentaires (User-Agent custom, JS, recaptcha).

---

## Sécurité & Bonnes pratiques

1. **Jamais logger le contenu des cookies** — seulement la taille et SHA256 (comme ici).
2. **Profil persistant** doit être protégé (pas de partage public).
3. **Rate-limit** : le code auto-refresh **ne s'exécute qu'une seule fois par erreur détectée** (pas de boucles infinies).
4. **Timeouts** : auto-refresh a un timeout de 180 secondes (évite les hangs).
5. **Monitoring** : loggez le SHA256 des cookies rafraîchis pour vérifier les patterns d'expiration.

---

## Métriques à monitorer

Pour vérifier que le système fonctionne bien :

- **Nombre de détections "Sign in"** : doit être bas une fois auto-refresh activé.
- **Taux de succès du retry** : doit être >90%.
- **SHA256 des cookies** : si tous les refreshes produisent le même SHA, c'est bon (cohérence).
- **Temps d'auto-refresh** : normalement <5-10 sec (si > 30 sec, vérifiez les timeouts réseau).

Exemple log à monitorer :

```
[INFO] Detected 'Sign in to confirm...' error; attempting auto-refresh of cookies...
[INFO] Running auto-refresh: /usr/bin/python3 ...
[INFO] [YTC AUTOREFRESH] refreshed cookies: size=386836 sha256=e634c16f...
[INFO] Retrying yt-dlp with refreshed cookies: /tmp/yt_cookies_autorefresh.txt
[INFO] yt-dlp succeeded with refreshed cookies
```

---

## Rollback

Si le système pose problème :

1. Mettez à jour `YOUTUBE_ENABLE_AUTO_REFRESH=false` (ou ne la définissez pas).
2. Le backend repassera en mode fallback : impersonation uniquement.
3. Ou revenez à l'approche manuelle : fournissez `YOUTUBE_COOKIES_B64` et `YOUTUBE_COOKIES_FILE` en env.

---

## Questions fréquentes

**Q: Puis-je utiliser auto-refresh sans profil persistant?**
A: Oui, mais c'est moins robuste. Sans profil, le refresher doit re-logguer à chaque exécution (headful mode). Profil persistant est plus fiable.

**Q: Est-ce que auto-refresh ralentit les téléchargements?**
A: Seulement si une erreur "Sign in" est détectée. Le refresh ajoute ~2-5 secondes. Premières tentatives sans erreur ne sont pas affectées.

**Q: Puis-je utiliser auto-refresh + YOUTUBE_COOKIES_B64 ensemble?**
A: Oui. Si YOUTUBE_COOKIES_B64 est valide, il est utilisé. Auto-refresh n'est appelé qu'en cas d'erreur détectée. Vous pouvez passer les deux.

**Q: Comment monitorer les rafraîchissements en production?**
A: Cherchez `[YTC AUTOREFRESH]` dans les logs. Chaque refresh imprime le SHA — alertez si le SHA change brutalement (possible token expiration cycle).

---

## Prochaines étapes

1. **Testez localement** (test_autorefresh_logic.py + refresh_oneoff.sh).
2. **Déployez en staging** avec YOUTUBE_ENABLE_AUTO_REFRESH=true pour un jour.
3. **Monitoriez les logs** — vérifiez que peu d'erreurs "Sign in" persistent.
4. **Deploiement en production** : définissez les envs et déroulez.

Good luck! 🚀
