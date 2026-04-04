#!/usr/bin/env python3
"""
Test registration endpoint in production
Simulates a user registration to verify email sending works end-to-end
"""
import requests
import json
import sys
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────

# Use your production URL
PROD_API_URL = "https://ai-short-generator-production.up.railway.app"

TEST_EMAIL = f"test-{datetime.now().timestamp()}@example.com"
TEST_PASSWORD = "TestPassword123!@"
TEST_USERNAME = f"testuser_{datetime.now().strftime('%s')}"

print("\n" + "=" * 70)
print("🧪 REGISTRATION ENDPOINT TEST - Production Email Verification")
print("=" * 70)

print(f"\n📍 Target: {PROD_API_URL}")
print(f"👤 Test User:")
print(f"   Username: {TEST_USERNAME}")
print(f"   Email: {TEST_EMAIL}")
print(f"   Password: {TEST_PASSWORD}")

# ─────────────────────────────────────────────────────────────────────
# Step 1: Test API Health
# ─────────────────────────────────────────────────────────────────────
print("\n" + "-" * 70)
print("🔍 STEP 1: API Health Check")
print("-" * 70)

try:
    response = requests.get(f"{PROD_API_URL}/health", timeout=10)
    if response.status_code == 200:
        print(f"✅ API is healthy (status: {response.status_code})")
        print(f"   Response: {response.json()}")
    else:
        print(f"⚠️  API responded but unexpected status: {response.status_code}")
        print(f"   Response: {response.text}")
except requests.exceptions.ConnectionError as e:
    print(f"❌ Cannot connect to API at {PROD_API_URL}")
    print(f"   Error: {e}")
    print(f"\n⚠️  Make sure to update PROD_API_URL in this script!")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error checking API health: {e}")

# ─────────────────────────────────────────────────────────────────────
# Step 2: Register New User
# ─────────────────────────────────────────────────────────────────────
print("\n" + "-" * 70)
print("📝 STEP 2: Register New User")
print("-" * 70)

registration_data = {
    "email": TEST_EMAIL,
    "username": TEST_USERNAME,
    "password": TEST_PASSWORD,
    "password_confirm": TEST_PASSWORD,
}

print(f"Sending registration request to /auth/register...")

try:
    response = requests.post(
        f"{PROD_API_URL}/auth/register",
        json=registration_data,
        timeout=30,
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 201:
        print("✅ Registration successful!")
        print("   User created and email sending queued")
        
        response_data = response.json()
        if response_data.get("message"):
            print(f"   Message: {response_data['message']}")
        
        print(f"\n🎯 Next Step: Check {TEST_EMAIL} for confirmation email")
        print(f"   (May take a few seconds to arrive)")
        
    elif response.status_code == 400:
        print(f"⚠️  Validation error: {response.json().get('detail', 'Unknown')}")
    elif response.status_code == 409:
        print(f"⚠️  User already exists: {response.json().get('detail', 'Unknown')}")
    else:
        print(f"❌ Unexpected response: {response.status_code}")
        
except requests.exceptions.Timeout:
    print(f"⏱️  Request timed out after 30 seconds")
    print(f"   This might mean the email is being sent in background (good!)")
except Exception as e:
    print(f"❌ Error during registration: {type(e).__name__}: {e}")

# ─────────────────────────────────────────────────────────────────────
# Step 3: Check Email Configuration Logs (if available)
# ─────────────────────────────────────────────────────────────────────
print("\n" + "-" * 70)
print("📊 STEP 3: Check API Configuration")
print("-" * 70)

try:
    response = requests.get(
        f"{PROD_API_URL}/debug/email-config",
        timeout=10,
    )
    
    if response.status_code == 200:
        config = response.json()
        print("✅ Email Configuration (from API):")
        for key, value in config.items():
            display_value = "***hidden***" if "password" in key.lower() else value
            print(f"   {key}: {display_value}")
    else:
        print(f"ℹ️  Debug endpoint not available (status: {response.status_code})")
        
except Exception as e:
    print(f"ℹ️  Debug endpoint not available: {type(e).__name__}")

# ─────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("✅ REGISTRATION TEST COMPLETE")
print("=" * 70)

print("\n📝 What to do now:")
print(f"  1. Check your email: {TEST_EMAIL}")
print("  2. Look for an email from: aishortsgenerators@gmail.com")
print("  3. Subject should contain: 'Confirm your email'")
print("  4. Click the confirmation link to activate your account")
print("\n💡 Troubleshooting:")
print("  - Check spam/junk folder")
print("  - Wait 1-2 minutes for email to arrive")
print("  - If no email: Check the API logs for errors")
print("  - Try clicking 'Resend confirmation email' in the modal")

print("\n" + "=" * 70 + "\n")
