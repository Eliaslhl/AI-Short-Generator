Guide: yt-dlp JS/EJS solver configuration
=========================================

Ce document explique les options introduites pour contrôler quand et comment
l'application demande à `yt-dlp` d'utiliser un runtime JavaScript et de
récupérer des composants EJS (External JavaScript solver).

Pourquoi ?
----------
Certaines pages YouTube nécessitent l'exécution d'un petit morceau de JavaScript
(pour résoudre un challenge, vérifier un token, etc.). Sans résoudre ce
challenge, `yt-dlp` ne peut pas récupérer les manifests vidéo/audio et ne
renvoie que des images storyboard (sb0..sb3). Fournir des cookies n'est pas
toujours suffisant ; il faut parfois exécuter le solveur JS.

Variables d'environnement
-------------------------
- `YTDLP_ENABLE_JS` — Comment activer la résolution JS. Valeurs possibles :
  - `always` : toujours passer `--js-runtimes` et `--remote-components`.
  - `when_cookies` : n'activer que si `YOUTUBE_COOKIES_FILE` ou
    `YOUTUBE_COOKIES_B64` est présent (valeur par défaut).
  - `on_error` : essayer sans flags, puis réessayer avec flags si une erreur
    liée au challenge JS est détectée.

- `YTDLP_JS_RUNTIMES` — Liste de runtimes à passer à `--js-runtimes` (ex: `node`).
- `YTDLP_REMOTE_COMPONENTS` — Ex: `ejs:npm` pour permettre à `yt-dlp` de
  récupérer le solveur EJS depuis npm.

Recommandations
---------------
- En production, `when_cookies` est un bon compromis de sécurité/flexibilité.
- Si votre environnement n'autorise pas le téléchargement de composants
  distants, pré-provisionnez la distribution EJS et utilisez `on_error` ou
  `always` selon vos contraintes.

Exemple `.env` (déjà dans `.env.example`)
----------------------------------------
YTDLP_ENABLE_JS=when_cookies
YTDLP_JS_RUNTIMES=node
YTDLP_REMOTE_COMPONENTS=ejs:npm

