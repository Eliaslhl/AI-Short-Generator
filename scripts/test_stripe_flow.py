#!/usr/bin/env python3
"""
Simple automation to test Stripe checkout -> webhook -> user plan update flow locally.

Usage:
  python scripts/test_stripe_flow.py --api-url http://localhost:8000 --email test@example.com --password pass1234 --price-id price_xxx

Requirements:
  pip install requests

Notes:
  - Run `stripe listen --forward-to localhost:8000/auth/stripe/webhook` in another terminal before paying.
  - Use Stripe test card 4242 4242 4242 4242 to complete payment in the browser.
"""

import argparse
import os
import sys
import time
import requests


def register(api_url, email, password):
    url = f"{api_url}/auth/register"
    res = requests.post(url, json={"email": email, "password": password})
    if res.status_code == 200 or res.status_code == 201:
        print(f"[OK] Registered {email}")
        return True
    else:
        # if already exists, that's ok
        print(f"[WARN] Register returned {res.status_code}: {res.text}")
        return False


def login(api_url, email, password):
    url = f"{api_url}/auth/login"
    res = requests.post(url, json={"email": email, "password": password})
    if res.status_code != 200:
        print(f"[ERR] Login failed: {res.status_code} {res.text}")
        return None
    data = res.json()
    token = data.get("access_token") or data.get("token") or data.get("accessToken")
    if not token and isinstance(data, dict):
        # some implementations return {'detail': '...'} on failure
        # or return {'access_token': '...'} on success
        token = data.get("access_token")
    if not token:
        # try common shape: {'token': '...'}
        for k in ("access_token", "token", "accessToken"):
            if k in data:
                token = data[k]
                break
    if not token:
        print(f"[ERR] Could not find access token in login response: {data}")
        return None
    print("[OK] Logged in, token acquired")
    return token


def create_checkout(api_url, token, price_id):
    url = f"{api_url}/auth/stripe/checkout"
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.post(url, headers=headers, json={"price_id": price_id})
    if res.status_code != 200:
        print(f"[ERR] Create checkout failed: {res.status_code} {res.text}")
        return None
    data = res.json()
    checkout_url = (
        data.get("checkout_url") or data.get("url") or data.get("session_url")
    )
    print(f"[OK] Checkout URL: {checkout_url}")
    return checkout_url


def get_me(api_url, token):
    url = f"{api_url}/auth/me"
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        print(f"[ERR] /auth/me returned {res.status_code}: {res.text}")
        return None
    return res.json()


def poll_for_plan_change(api_url, token, current_plan, timeout=120, interval=3):
    print(f"Polling /auth/me up to {timeout}s for plan change (from {current_plan})...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        me = get_me(api_url, token)
        if me:
            plan = me.get("plan") or me.get("plan")
            if plan and plan != current_plan:
                print(f"[OK] Plan changed: {plan}")
                return me
            else:
                print(f"waiting... current plan={plan}")
        time.sleep(interval)
    print("[TIMEOUT] Plan did not change in time")
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--api-url", default=os.getenv("API_URL", "http://localhost:8000")
    )
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--price-id", required=True)
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()

    api_url = args.api_url.rstrip("/")
    email = args.email
    password = args.password
    price_id = args.price_id

    register(api_url, email, password)
    token = login(api_url, email, password)
    if not token:
        sys.exit(1)

    me = get_me(api_url, token)
    current_plan = None
    if isinstance(me, dict):
        current_plan = me.get("plan")
    print(f"Current plan: {current_plan}")

    checkout_url = create_checkout(api_url, token, price_id)
    if not checkout_url:
        sys.exit(1)

    print(
        "Open the checkout URL in your browser and complete payment (test card 4242...)"
    )
    print(checkout_url)

    result = poll_for_plan_change(api_url, token, current_plan, timeout=args.timeout)
    if result:
        print("Success — user updated:")
        print(result)
    else:
        print("Failed to detect plan change — check stripe listen and backend logs.")


if __name__ == "__main__":
    main()
