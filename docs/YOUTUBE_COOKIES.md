Guide d'intégration des cookies YouTube pour la production
=========================================================

Ce document explique comment fournir des cookies YouTube à l'application afin que `yt-dlp` puisse télécharger des vidéos bloquées par une vérification "Sign in to confirm you're not a bot".

Résumé
------
- Deux options supportées par l'application :
  1. `YOUTUBE_COOKIES_FILE` : chemin vers un fichier cookies.txt (préféré en production).
  2. `YOUTUBE_COOKIES_B64` : contenu du fichier cookies.txt encodé en base64 (utile pour CI / serverless).
- Le code se charge de détecter `YOUTUBE_COOKIES_FILE` en priorité, puis `YOUTUBE_COOKIES_B64` (écrit un fichier temporaire et le supprime après usage).

Sécurité
--------
- Les cookies sont des secrets de session. Traitez-les comme des credentials : stockez-les dans un gestionnaire de secrets (Kubernetes Secret, Docker secret, AWS Secrets Manager, Azure Key Vault, etc.).
- Ne commitez jamais de cookies dans Git.
- Restreignez l'accès au fichier (chmod 600) et limitez les droits des processus qui peuvent le lire.

Exporter les cookies depuis le navigateur
----------------------------------------
(Instructions générales — si besoin, indiquez votre navigateur et je fournis un pas-à-pas précis)

Chrome / Chromium:
1. Installer une extension d'export de cookies (par ex. "cookies.txt", "Get cookies.txt" ou "EditThisCookie").
2. Connectez-vous à YouTube.
3. Ouvrez l'extension et exportez les cookies pour le domaine `youtube.com` -> sauvegardez `cookies.txt`.

Firefox:
- Même principe : installez l'addon "cookies.txt" / "Export Cookies" et exportez le fichier.

Option 1 — Monter un fichier de cookies (recommandé)
---------------------------------------------------
- Placez votre `cookies.txt` dans un store de secrets puis montez-le dans le conteneur.

Docker Compose exemple:

```yaml
version: '3.7'
services:
  app:
    image: your-image:latest
    environment:
      - YOUTUBE_COOKIES_FILE=/run/secrets/youtube_cookies.txt
    secrets:
      - youtube_cookies
secrets:
  youtube_cookies:
    file: ./secrets/youtube_cookies.txt
```

Dans ce modèle, `./secrets/youtube_cookies.txt` contient le fichier exporté. Le conteneur verra la variable d'env `YOUTUBE_COOKIES_FILE` pointant vers le fichier monté.

Kubernetes (exemple)
--------------------
1) Créer un Secret (ici via `kubectl`):

```bash
kubectl create secret generic youtube-cookies --from-file=cookies.txt=./cookies.txt
```

2) Monter le secret en volume et définir la variable d'environnement dans le Deployment:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-shorts-app
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ai-shorts
  template:
    metadata:
      labels:
        app: ai-shorts
    spec:
      containers:
      - name: app
        image: your-image:latest
        env:
        - name: YOUTUBE_COOKIES_FILE
          value: /var/secrets/youtube/cookies.txt
        volumeMounts:
        - name: youtube-cookies
          mountPath: /var/secrets/youtube
          readOnly: true
      volumes:
      - name: youtube-cookies
        secret:
          secretName: youtube-cookies
```

Option 2 — Variable base64 (utile pour CI / serverless)
-----------------------------------------------------
Si votre plateforme ne permet pas de monter de fichier, encodez le contenu en base64 et injectez `YOUTUBE_COOKIES_B64`.

Exemple de génération base64 (macOS / Linux):

```bash
# assume cookies.txt exist
export YOUTUBE_COOKIES_B64="$(python3 -c 'import base64,sys;print(base64.b64encode(open("cookies.txt","rb").read()).decode())')"
```

Le code écrit un fichier temporaire décodé et le supprimera après usage.

Commande de test locale
-----------------------
Depuis la racine du dépôt, testez le téléchargement (script de test embarqué):

```bash
export PYTHONPATH="$(pwd)"
export YOUTUBE_COOKIES_FILE="/chemin/vers/cookies.txt"   # ou YOUTUBE_COOKIES_B64=...
python3 - <<'PY'
from backend.services.youtube_service import download_video
p,t = download_video("https://www.youtube.com/watch?v=_GKJcB91Hus","testjob", audio_only=False)
print("Downloaded:", p, "title:", t)
PY
```

Opérations et monitoring
------------------------
- Surveillez les logs : lorsque `yt-dlp` demande des cookies, l'application émettra un message explicite indiquant que l'intervention est requise.
- En cas d'échecs répétés, alertez l'opérateur pour renouveler/mettre à jour les cookies.

Notes légales / ToS
-------------------
- Vérifiez que vous avez le droit de télécharger ou réutiliser le contenu (politiques YouTube / droit d'auteur). Cette solution facilite l'accès technique mais n'autorise pas l'usage illégal.

Besoin d'aide pas-à-pas ?
------------------------
- Dites-moi quel navigateur (Chrome/Firefox) et je vous fournis les étapes détaillées pour exporter `cookies.txt`.
- Je peux aussi ajouter un petit utilitaire CLI au repo pour convertir automatiquement un `cookies.txt` en base64 prêt à coller dans un secret manager.

