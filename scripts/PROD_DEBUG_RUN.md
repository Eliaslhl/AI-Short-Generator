## Comment exécuter un one‑off de diagnostic pour YT cookies et yt-dlp

Ce document explique comment activer le debug, exécuter le one‑off et désactiver le debug.

1) (Temporaire) Activer la sortie de debug côté backend

 - Dans votre UI Railway / déploiement, ajoutez ou définissez la variable d'environnement:
   - `YOUTUBE_COOKIES_DEBUG=true`

 - Redéployez le service (ou redémarrez) si nécessaire.

2) Exécuter le one‑off (dans le même service/environnement où les variables `YOUTUBE_COOKIES_B64_PART_*` sont définies)

 - Ouvrez un shell one‑off (Railway / ou un conteneur équivalent) puis, depuis la racine du projet, exécutez :

```bash
# Rendre le script exécutable (si nécessaire)
chmod +x scripts/run_prod_ytdlp_oneoff.sh

# Exécuter le one-off (remplacez l'URL par celle du job ou utilisez YTDLP_URL env)
./scripts/run_prod_ytdlp_oneoff.sh "https://www.youtube.com/watch?v=8qjxrIHuJgc&t=3s"

# Le script va:
# - reconstruire /tmp/youtube_cookies.txt depuis les variables d'env (ou fallback secrets/youtube_cookies.b64)
# - afficher size+sha256
# - lancer yt-dlp et écrire les logs dans /tmp/yt-dlp-oneoff.log
# - afficher la queue/fin du log (tail)
```

3) Examiner les résultats

 - Dans les logs du backend (ou la sortie du one‑off), récupérez la ligne `WROTE ... sha256=...`.
 - Comparez le sha256 avec votre copie locale (commande `sha256sum` ou `shasum -a 256`).

4) Après vérification

 - Désactivez `YOUTUBE_COOKIES_DEBUG` (unset ou false) et redéployez.

5) Si `yt-dlp` renvoie toujours `Sign in to confirm you’re not a bot`:

 - Vérifiez que les cookies ne sont pas expirés.
 - Essayez d'exporter à nouveau les cookies depuis votre navigateur et rechargez les variables d'env.
 - Considérez l'utilisation d'une IP/proxy résidentiel ou d'une session liée à la même région IP.
