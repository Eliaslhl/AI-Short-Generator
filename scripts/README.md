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
