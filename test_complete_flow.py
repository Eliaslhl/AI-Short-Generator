#!/usr/bin/env python3
"""
Complete registration flow test
Tests: Register -> Get Token -> Use Token -> Verify Access
"""
import requests
import json
from datetime import datetime

API_URL = "https://ai-short-generator-production.up.railway.app"

print("\n" + "=" * 70)
print("✨ COMPLETE REGISTRATION FLOW TEST")
print("=" * 70)

# Create test user
timestamp = datetime.now().strftime('%s')
test_email = f"flow-test-{timestamp}@example.com"
test_password = "FlowTest123!@"
test_username = f"flowtest_{timestamp}"

print(f"\n📝 Test User:")
print(f"  Email: {test_email}")
print(f"  Username: {test_username}")

# ─────────────────────────────────────────────────────────────────────
# STEP 1: Register
# ─────────────────────────────────────────────────────────────────────
print("\n" + "─" * 70)
print("1️⃣ REGISTER")
print("─" * 70)

try:
    register_response = requests.post(
        f"{API_URL}/auth/register",
        json={
            "email": test_email,
            "username": test_username,
            "password": test_password,
            "password_confirm": test_password,
        },
        timeout=30
    )
    
    print(f"Status: {register_response.status_code}")
    register_data = register_response.json()
    
    # Check for token
    if "access_token" not in register_data:
        print(f"❌ No access_token in response!")
        print(f"Response: {json.dumps(register_data, indent=2)}")
        exit(1)
    
    access_token = register_data["access_token"]
    print(f"✅ Registration successful!")
    print(f"   Message: {register_data.get('message')}")
    print(f"   Token: {access_token[:50]}...")
    
except Exception as e:
    print(f"❌ Registration failed: {e}")
    exit(1)

# ─────────────────────────────────────────────────────────────────────
# STEP 2: Use Token to Get User Info
# ─────────────────────────────────────────────────────────────────────
print("\n" + "─" * 70)
print("2️⃣ GET USER INFO (using token)")
print("─" * 70)

try:
    me_response = requests.get(
        f"{API_URL}/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10
    )
    
    if me_response.status_code != 200:
        print(f"❌ Failed to get user info: {me_response.status_code}")
        print(f"Response: {me_response.text}")
        exit(1)
    
    user_data = me_response.json()
    print(f"✅ User info retrieved!")
    print(f"   ID: {user_data.get('id')}")
    print(f"   Email: {user_data.get('email')}")
    print(f"   Plan: {user_data.get('plan')}")
    print(f"   Can Generate: {user_data.get('can_generate')}")
    print(f"   Free Generations Left: {user_data.get('free_generations_left')}")
    
except Exception as e:
    print(f"❌ Failed to get user info: {e}")
    exit(1)

# ─────────────────────────────────────────────────────────────────────
# STEP 3: Verify Token Works (Try an API call)
# ─────────────────────────────────────────────────────────────────────
print("\n" + "─" * 70)
print("3️⃣ VERIFY TOKEN (get history)")
print("─" * 70)

try:
    history_response = requests.get(
        f"{API_URL}/api/history",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10
    )
    
    if history_response.status_code != 200:
        print(f"❌ Failed to access protected endpoint: {history_response.status_code}")
        exit(1)
    
    print(f"✅ Token verified! Can access protected endpoints")
    print(f"   History: {history_response.json()}")
    
except Exception as e:
    print(f"❌ Failed to verify token: {e}")
    exit(1)

# ─────────────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("✅ COMPLETE FLOW SUCCESSFUL!")
print("=" * 70)
print("\n📊 Test Results:")
print(f"  ✅ User registered: {test_email}")
print(f"  ✅ JWT token received and valid")
print(f"  ✅ Token works for authenticated requests")
print(f"  ✅ User can access API immediately")

print("\n🎉 Registration flow is working perfectly!")
print("   Users should be auto-logged-in after registration.")
print("\n" + "=" * 70 + "\n")
