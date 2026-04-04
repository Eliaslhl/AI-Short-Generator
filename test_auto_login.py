#!/usr/bin/env python3
"""
Simple registration test - checks if auto-login works after registration
"""
import requests
import json
from datetime import datetime

API_URL = "https://ai-short-generator-production.up.railway.app"

print("\n" + "=" * 70)
print("🚀 REGISTRATION TEST - Auto-Login Check")
print("=" * 70)

# Create test user
test_user = f"test{datetime.now().strftime('%s')}"
test_email = f"{test_user}@example.com"
test_password = "TestPassword123!@"

print(f"\nTest User:")
print(f"  Username: {test_user}")
print(f"  Email: {test_email}")
print(f"  Password: {test_password}")

# Register
print("\n" + "-" * 70)
print("📝 Registering user...")
print("-" * 70)

try:
    response = requests.post(
        f"{API_URL}/auth/register",
        json={
            "email": test_email,
            "username": test_user,
            "password": test_password,
            "password_confirm": test_password,
        },
        timeout=30
    )
    
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")
    
    # Check if we got access_token
    if "access_token" in result:
        print("\n✅ AUTO-LOGIN TOKEN RECEIVED!")
        print(f"Token: {result['access_token'][:50]}...")
        
        # Try to use the token to get user info
        print("\n" + "-" * 70)
        print("🔍 Testing auto-login token...")
        print("-" * 70)
        
        me_response = requests.get(
            f"{API_URL}/auth/me",
            headers={"Authorization": f"Bearer {result['access_token']}"},
            timeout=10
        )
        
        if me_response.status_code == 200:
            user_info = me_response.json()
            print("✅ TOKEN WORKS! User info retrieved:")
            print(f"   Email: {user_info.get('email')}")
            print(f"   Username: {user_info.get('username')}")
            print(f"   Is Verified: {user_info.get('is_verified')}")
        else:
            print(f"❌ Token invalid: {me_response.status_code}")
    else:
        print("\n⚠️ No auto-login token in response (email verification might still be enabled)")
    
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 70 + "\n")
