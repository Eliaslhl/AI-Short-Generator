#!/usr/bin/env python3
"""simulate_stripe_webhook.py
Simule un événement checkout.session.completed signé et le POSTe vers /auth/stripe/webhook.
Ensuite vérifie que l'utilisateur de test a bien son champ `plan` mis à jour.

Usage:
    python3 simulate_stripe_webhook.py
"""

import json
import time
import hmac
import hashlib
import sqlite3
import urllib.request
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
ENV_PATH = os.path.join(PROJECT_ROOT, ".env")
DB_PATH = os.path.join(PROJECT_ROOT, "data", "app.db")
WEBHOOK_URL = "http://127.0.0.1:8000/auth/stripe/webhook"
TEST_USER_EMAIL = "test+stripe5@example.com"

# 1) Charger .env
env = {}
if not os.path.exists(ENV_PATH):
    print(f".env introuvable à {ENV_PATH}")
    sys.exit(1)

with open(ENV_PATH, "r") as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"')

STRIPE_WEBHOOK_SECRET = env.get("STRIPE_WEBHOOK_SECRET")
if not STRIPE_WEBHOOK_SECRET:
    print("⚠️  STRIPE_WEBHOOK_SECRET introuvable dans .env")
    sys.exit(1)

# 2) Récupérer user_id depuis la DB
if not os.path.exists(DB_PATH):
    print(f"DB introuvable à {DB_PATH}")
    sys.exit(1)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("SELECT id FROM users WHERE email = ?", (TEST_USER_EMAIL,))
r = cur.fetchone()
if not r:
    print(f"⚠️  Utilisateur {TEST_USER_EMAIL} introuvable dans la BD ({DB_PATH})")
    conn.close()
    sys.exit(1)
user_id = r[0]
print("User id trouvé :", user_id)

# 3) Construire payload
payload = {
    "type": "checkout.session.completed",
    "data": {
        "object": {
            "metadata": {"user_id": user_id, "plan": "PRO"},
            "customer": "cus_test_sim",
            "subscription": "sub_test_sim",
        }
    }
}
payload_json = json.dumps(payload, separators=(',', ':'))

# 4) Calculer signature
timestamp = str(int(time.time()))
signed_payload = timestamp + "." + payload_json
sig = hmac.new(STRIPE_WEBHOOK_SECRET.encode(), signed_payload.encode(), hashlib.sha256).hexdigest()
sig_header = f"t={timestamp},v1={sig}"
print("Signature header:", sig_header)

# 5) POST
req = urllib.request.Request(WEBHOOK_URL, data=payload_json.encode('utf-8'), headers={"Content-Type": "application/json", "stripe-signature": sig_header})
print("Envoi vers", WEBHOOK_URL, "...")
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        body = resp.read().decode('utf-8')
        print('HTTP', resp.status)
        print(body)
except Exception as e:
    print('Erreur requête:', e)
    conn.close()
    sys.exit(1)

# 6) Vérifier en DB
cur.execute("SELECT id,email,plan,subscription_type FROM users WHERE id = ?", (user_id,))
print('DB user row:', cur.fetchone())
conn.close()
