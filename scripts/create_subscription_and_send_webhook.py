#!/usr/bin/env python3
"""Create a Stripe subscription and send a webhook (no metadata.plan) to exercise
server path that retrieves subscription via Stripe API.

Usage:
    python3 create_subscription_and_send_webhook.py
"""
import os
import json
import time
import hmac
import hashlib
import stripe
import sqlite3
import urllib.request

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
ENV_PATH = os.path.join(PROJECT_ROOT, '.env')
DB_PATH = os.path.join(PROJECT_ROOT, 'data', 'app.db')
WEBHOOK_URL = 'http://127.0.0.1:8000/auth/stripe/webhook'
TEST_USER_EMAIL = 'test+stripe5@example.com'

# load env
env = {}
with open(ENV_PATH, 'r') as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '=' in line:
            k, v = line.split('=', 1)
            env[k.strip()] = v.strip().strip('"')

STRIPE_SECRET_KEY = env.get('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET = env.get('STRIPE_WEBHOOK_SECRET')
PRICE_ID = env.get('STRIPE_YOUTUBE_PRO_MONTHLY_PRICE_ID') or env.get('STRIPE_PRO_MONTHLY_PRICE_ID')

if not STRIPE_SECRET_KEY or not STRIPE_WEBHOOK_SECRET or not PRICE_ID:
    print('Missing STRIPE_SECRET_KEY or STRIPE_WEBHOOK_SECRET or PRICE_ID in .env')
    raise SystemExit(1)

stripe.api_key = STRIPE_SECRET_KEY

# get user id from DB
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("SELECT id FROM users WHERE email = ?", (TEST_USER_EMAIL,))
row = cur.fetchone()
if not row:
    print('Test user not found in DB')
    raise SystemExit(1)
user_id = row[0]
# mark created resources so we can cleanup later
cust = None
sub = None

print('User id:', user_id)

try:
    # 1) Create Stripe customer
    cust = stripe.Customer.create(email=TEST_USER_EMAIL)
    print('Stripe customer created:', cust.id)

    # 1a) Try creating a subscription using a short trial so Stripe won't require an
    # immediate payment method. If your Stripe account still enforces payment method
    # requirements for subscriptions, adjust collection_method or add a payment
    # method via Checkout flows in test mode.
    try:
        sub = stripe.Subscription.create(
            customer=cust.id, items=[{"price": PRICE_ID}], trial_period_days=7
        )
        print('Stripe subscription created with trial:', sub.id)
    except Exception as e:
        print('Subscription creation with trial failed:', repr(e))
        # Fallback: attempt to create subscription with send_invoice collection
        try:
            sub = stripe.Subscription.create(
                customer=cust.id, items=[{"price": PRICE_ID}], collection_method='send_invoice'
            )
            print('Stripe subscription created with send_invoice:', sub.id)
        except Exception as e2:
            print('Fallback subscription creation failed:', repr(e2))
            raise

    # 3) Build webhook payload WITHOUT metadata.plan but WITH metadata.user_id and subscription
    payload = {
        'type': 'checkout.session.completed',
        'data': {
            'object': {
                'metadata': {'user_id': user_id},
                'customer': cust.id,
                'subscription': sub.id,
            }
        }
    }
    payload_json = json.dumps(payload, separators=(',', ':'))

    # 4) Sign payload
    ts = str(int(time.time()))
    signed = ts + '.' + payload_json
    sig = hmac.new(STRIPE_WEBHOOK_SECRET.encode(), signed.encode(), hashlib.sha256).hexdigest()
    sig_header = f't={ts},v1={sig}'
    print('Signature header:', sig_header)

    # 5) POST webhook
    req = urllib.request.Request(
        WEBHOOK_URL,
        data=payload_json.encode('utf-8'),
        headers={'Content-Type': 'application/json', 'stripe-signature': sig_header},
    )
    print('Posting webhook to', WEBHOOK_URL)
    with urllib.request.urlopen(req, timeout=15) as resp:
        print('HTTP', resp.status)
        print(resp.read().decode('utf-8'))

    # 6) Check DB
    cur.execute(
        "SELECT id,email,plan,subscription_type,stripe_subscription_id FROM users WHERE id = ?",
        (user_id,),
    )
    print('DB:', cur.fetchone())

finally:
    # Cleanup test Stripe objects to keep dashboard clean
    # Best-effort: cancel/delete subscription then delete customer
    try:
        if sub and getattr(sub, 'id', None):
            try:
                # Cancel at period end instead of immediate deletion to preserve
                # Stripe bookkeeping and avoid removing the customer object.
                stripe.Subscription.modify(sub.id, cancel_at_period_end=True)
                print('Marked subscription to cancel at period end:', sub.id)
            except Exception as e:
                print('Failed to mark subscription cancel_at_period_end:', repr(e))
        # Do not delete the customer immediately; leaving the test customer is
        # less destructive and preserves invoice history. If you want to remove
        # the customer, you can do that manually or enable a --delete-customer flag.
    except Exception as outer_e:
        print('Cleanup encountered an error:', repr(outer_e))
    finally:
        conn.close()
