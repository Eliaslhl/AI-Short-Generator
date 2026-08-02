# Audit préproduction — AI Shorts Generator

Date : 2026-08-03. Périmètre : auth/sessions/CSRF/CORS/ownership, quotas/retries/jobs
bloqués, médias privés/fichiers temporaires/stockage, migrations/secrets/logs/OpenAPI,
pipelines YouTube/Twitch/transcription, frontend/accessibilité/SEO/légal, configuration
production/observabilité/déploiement.

Classement : **P0** bloquant avant lancement · **P1** important, à corriger avant lancement
· **P2** à corriger rapidement après lancement · **P3** cosmétique/mineur.

## P0 — Bloquants

### P0-1 — Rate limiting non appliqué sur les routes d'authentification
`backend/main.py` crée `Limiter(default_limits=["60/minute"])` et pose `app.state.limiter`,
mais **`SlowAPIMiddleware` n'est jamais montée** (`app.add_middleware(...)` ne liste que
CORS et security headers) et **aucune route ne porte `@limiter.limit(...)`**. `default_limits`
sans middleware ni décorateur explicite n'est pas appliqué. `POST /auth/login`,
`/auth/register`, `/auth/resend-confirmation-email` n'ont donc **aucun rate limit réel**.
- **Exploitation** : brute-force/credential-stuffing illimité sur le login, spam d'inscription.
- **Statut** : corrigé, voir PR dédiée.

### P0-2 — Double remboursement de quota sur échec de rendu
`backend/api/routes.py::run_pipeline` : si `render_clip` échoue, un bloc interne rembourse
le quota puis relève l'exception (`raise`) ; le bloc `except` externe recapture cette
exception et **rembourse une seconde fois**, sans vérifier `job_record.status`.
- **Exploitation** : soumettre une vidéo qui fait systématiquement échouer `render_clip`
  rembourse 2 crédits par tentative au lieu d'1 — contournement direct de la monétisation.
- **Statut** : corrigé, voir PR dédiée.

### P0-3 — Secrets réels en clair dans `.env.clean`
`.env.clean` (non tracké par git, confirmé) contient de **vraies valeurs de production** :
`STRIPE_SECRET_KEY=sk_live_...`, `STRIPE_WEBHOOK_SECRET=whsec_...`, `GROQ_API_KEY=gsk_...`,
`SECRET_KEY=...`, un mot de passe d'application Gmail en clair.
- **Risque** : compromission si le poste est copié/sauvegardé/zippé par erreur.
- **Statut** : **non corrigeable par du code.** Action manuelle requise du propriétaire du
  compte : faire tourner (rotate) les clés Stripe/Groq/SECRET_KEY/mot de passe mail listées,
  puis vider ou supprimer `.env.clean`. Je n'ai pris aucune action sur ces identifiants —
  ce sont des identifiants de paiement/production réels.

## P1 — Important, avant lancement

| # | Constat | Fichier | Détail |
|---|---|---|---|
| P1-1 | Race condition quota (route principale) | `backend/api/routes.py` | Check-puis-incrément du quota sans `with_for_update()`, contrairement au pipeline Twitch qui le fait. Deux requêtes simultanées peuvent toutes deux passer le check. |
| P1-2 | Jobs bloqués en "processing" sans détection | `backend/api/routes.py` | Un crash process (OOM/kill) entre le passage à `"processing"` et la fin du pipeline laisse le job bloqué indéfiniment : pas de timeout, pas de tâche de nettoyage, quota jamais remboursé. |
| P1-3 | Pipeline YouTube : aucun nettoyage des fichiers temporaires | `backend/api/routes.py` (`run_pipeline`) | Contrairement à Twitch (`_cleanup_twitch_download_workspace`), la vidéo source téléchargée n'est jamais supprimée, succès ou échec — accumulation illimitée de contenu potentiellement protégé par le droit d'auteur. |
| P1-4 | Aucune rétention / purge périodique | `data/videos/`, `data/clips/` | Aucun scheduler, aucun endpoint de suppression. Croissance de stockage non bornée. |
| P1-5 | `/docs`, `/redoc`, `/openapi.json` publics en prod | `backend/main.py` | `FastAPI()` instanciée sans `docs_url=None`/`redoc_url=None`/`openapi_url=None` conditionnés à l'environnement. |
| P1-6 | Migration non réversible sur colonne NOT NULL | `alembic/versions/20260401_merge_and_fix.py` | `downgrade()` est un `pass` alors que `upgrade()` crée un type ENUM + colonne `plan NOT NULL`. |
| P1-7 | Erreurs techniques écrasées par un message générique | `backend/api/routes.py` | Toute cause d'échec (vidéo privée/supprimée/géo-bloquée, bot-check YouTube, VOD Twitch expiré) devient `"Processing failed"` — le travail de message détaillé déjà fait dans `youtube_service.py` est jeté. Cause de tickets support. |
| P1-8 | Aucune limite de durée sur la vidéo source | pipeline global | Seules les durées de *clips de sortie* sont bornées. Une vidéo de 10h fait tourner téléchargement + transcription pendant des heures sans contrôle de coût — déni de service applicatif. |
| P1-9 | Pas de tracking d'erreurs (Sentry ou équivalent) | production | Aucune intégration trouvée ; en prod, les erreurs ne sont visibles que dans les logs bruts Railway, sans alerting. |
| P1-10 | Pas de sauvegarde documentée (DB + médias) | déploiement | Aucun script/doc de backup pour la base ou `data/clips`. Filesystem Railway éphémère par défaut — à confirmer qu'un volume persistant est bien attaché côté dashboard (non vérifiable depuis le repo). |
| P1-11 | `DATABASE_URL` Postgres en prod — à confirmer | Railway (hors repo) | Le repo est correctement configuré pour Postgres via env var, mais rien ne garantit depuis le code que la variable est bien positionnée en prod ; un fallback SQLite avec plusieurs workers RQ causerait des locks/corruption. |
| P1-12 | Convention de préfixe Vite incorrecte côté frontend | `.env.example`, `LandingPage.tsx` | Les Price ID Stripe sont documentés en `REACT_APP_STRIPE_*` (convention CRA) alors que Vite n'expose que `VITE_*` — config morte, jamais lue ; les vrais Price ID sont en dur dans `LandingPage.tsx` (impact faible : ils sont conçus pour être publics, mais la doc est trompeuse). |

## P2 — À corriger rapidement après lancement

- Concurrence de jobs par utilisateur non limitée (aggrave P1-1) — `backend/api/routes.py`.
- `job_id` YouTube tronqué à 8 caractères hex (32 bits) vs UUID complet pour Twitch — `backend/services/youtube_service.py`.
- `settings.video_dir`/`clips_dir`/`video_temp_dir` sans validation qu'ils restent sous `DATA_DIR` — `backend/config.py`.
- Erreurs yt-dlp non bot-check renvoyées en anglais technique brut, jamais catégorisées — `backend/services/youtube_service.py`.
- Pas d'endpoint d'annulation de job — un utilisateur qui ferme l'onglet ne peut pas stopper le traitement en cours.
- Budget temps total non borné sur les 8 fallbacks bot-check YouTube (chacun avec son propre timeout complet) — `backend/services/youtube_service.py`.
- Pas de limite mémoire/CPU applicative (Docker/Railway) — un OOM tue tout le conteneur sans dégradation propre.
- Pas de métriques runtime (Prometheus ou équivalent).
- Smoke test post-déploiement partiel (`post_deploy_youtube_check.py` ne couvre que les cookies YouTube) et non intégré formellement au process de déploiement.
- `DashboardPage.tsx` avale silencieusement les erreurs réseau sur l'historique (`.catch(() => {})`) — l'utilisateur voit une liste vide au lieu d'un message d'erreur.
- `LoginPage.tsx` (et probablement `RegisterPage.tsx`/`ForgotPasswordPage.tsx`) : `<label>` sans `htmlFor` associé à l'`<input>` — accessibilité lecteur d'écran.
- `MentionsLegales.tsx` incomplet au regard du LCEN (pas de SIRET/forme juridique).
- Landing/Login/Register/Dashboard/Generator : pas de balises meta Helmet dédiées (hors prerender de la landing).
- `backend/services/twitch_client.py` : erreurs génériques sans distinguer VOD expiré/privé/supprimé — module potentiellement mort, à vérifier.
- Healthcheck `/health` superficiel (ne vérifie ni DB ni Redis).

## P3 — Cosmétique / mineur

- CSRF théorique sur login/register via formulaire `enctype="text/plain"` forgé — risque très atténué par CORS + JSON body, non bloquant.
- Pas de `job_timeout` explicite passé à `queue.enqueue()` (timeout RQ par défaut 180s, potentiellement trop court pour un traitement vidéo).
- Message d'erreur Twitch codé en dur à "5 minutes" alors que le timeout réel est configurable (`ytdlp_download_timeout`).
- Code mort loggant des chemins locaux dans `ClipGenerator.extract_clip`/`_convert_format` (méthodes non utilisées par le pipeline réel).
- Deux racines de migration Alembic historiques fusionnées a posteriori — pas de bug actif, historique fragile.
- Price ID Stripe (publics par nature) présents dans `.env.example` — impact faible.

## Points déjà vérifiés et correctement gérés (pas de régression trouvée)

- Sessions opaques HttpOnly, cookie `Secure` forcé en prod, préfixe `__Host-` validé au démarrage, `SameSite` cohérent.
- Validation CSRF/Origin centralisée (`require_trusted_origin_for_cookie_auth`), appliquée systématiquement via la dépendance d'auth.
- CORS strict, pas de wildcard, échec fermé si `FRONTEND_URL` invalide.
- Ownership centralisé (`job_access_service`), 404 uniforme, pas de fuite d'existence.
- Logout : révocation serveur réelle + cookie effacé.
- Retries RQ : aucune configuration `Retry` trouvée → pas de risque de double décrément par retry automatique.
- Migrations autres que celle listée en P1-6 : pas d'`ALTER`/`DROP` destructeur sans garde.
- `.gitignore` couvre bien `.env`/`.env.*`, aucune fuite de secret dans l'historique git (`git log --all` sur `.env`, `*.pem`, `*.key` : vide).
- Logging : redaction centralisée robuste (`security_logging.py`), pas de body/headers bruts loggés.
- Gestion d'erreur générique (pas de stack trace exposée au client, `debug=False`).
- Route `/debug/job/{job_id}` correctement gardée par `settings.is_development`.
- Médias privés (TOCTOU), workspace Twitch isolé, hygiène ClipGenerator : déjà durcis lors de PR précédentes, aucune régression trouvée.
- Pas d'endpoint d'upload de fichier local — rien à auditer sur ce point (le produit n'expose que des URLs).
- Pages légales présentes côté frontend (CGU, confidentialité, mentions légales, cookies) avec contenu réel.
- Pas de secret en dur côté frontend, pas de token en localStorage, Error Boundary React monté.
