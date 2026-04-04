# reconstruct_youtube_cookies.py

Petit utilitaire pour reconstruire un fichier de cookies YouTube à partir de :

- variables d'environnement `YOUTUBE_COOKIES_B64_PART_1..N`
- ou variable `YOUTUBE_COOKIES_B64`
- ou fichier de secours `secrets/youtube_cookies.b64`

Le script décode le base64, écrit un fichier (par défaut `/tmp/youtube_cookies.txt`) et affiche la taille
et le sha256 du contenu (utile pour vérification sans exposer les cookies).

Usage rapide :

```bash
python3 scripts/reconstruct_youtube_cookies.py --output /tmp/youtube_cookies.txt
```

Options :
- `--output` ou `-o` : chemin de sortie du fichier décodé (par défaut `/tmp/youtube_cookies.txt`).
- `--fallback` ou `-f` : chemin du fichier base64 de secours (par défaut `secrets/youtube_cookies.b64`).

Notes de sécurité :
- Le script n'affiche jamais le contenu des cookies, seulement la taille et le hash SHA256.
- Après vérification en production, désactivez `YOUTUBE_COOKIES_DEBUG` pour éviter d'exposer des métadonnées.

## post_deploy_youtube_check.py

Diagnostic rapide après déploiement Railway pour valider que les variables cookies ne sont pas corrompues.

Ce script vérifie :
- reconstruction `YOUTUBE_COOKIES_B64_PART_*` (ou fallback `YOUTUBE_COOKIES_B64`),
- décodage base64,
- format Netscape + présence d'entrées `youtube.com`,
- comparaison SHA256 avec `--expected-sha` (ou `YOUTUBE_COOKIES_SHA256`),
- et (optionnel) scan d'un fichier log backend pour détecter les erreurs connues.

Usage :

```bash
python3 scripts/post_deploy_youtube_check.py \
	--env-file temp/railway_youtube_cookie_parts.env \
	--expected-sha bf39253b28772a86e18ec71c8ade9e272dcc009b0240656aaa94cbb5a933b21d
```

Avec logs :

```bash
python3 scripts/post_deploy_youtube_check.py \
	--env-file temp/railway_youtube_cookie_parts.env \
	--expected-sha bf39253b28772a86e18ec71c8ade9e272dcc009b0240656aaa94cbb5a933b21d \
	--log-file /path/to/backend.log
```

# Stripe local test helper

This folder contains a small helper script to test the Stripe Checkout → webhook → user plan update flow locally.

Prerequisites
- Backend running locally (http://localhost:8000)
- Stripe CLI installed and logged in (`stripe login`)
- Run `stripe listen --forward-to localhost:8000/auth/stripe/webhook` in another terminal to forward signed webhooks
- Python 3 and `requests` installed in your environment (`pip install requests`)

Usage

1. Start backend and frontend locally.
2. Run Stripe listen and copy the `whsec_...` secret into your local env or `.env` (STRIPE_WEBHOOK_SECRET).
3. Run the script to create a test user, open checkout and poll for plan change:

```bash
python scripts/test_stripe_flow.py --api-url http://localhost:8000 --email test@example.com --password pass1234 --price-id price_xxx
```

Open the printed `checkout_url` in your browser and pay with Stripe test card `4242 4242 4242 4242`.

The script will poll `/auth/me` until the plan changes or it times out.
