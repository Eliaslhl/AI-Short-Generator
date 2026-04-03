#!/usr/bin/env python3
"""
Test script to verify security headers are properly set.
Run with: python scripts/test_security_headers.py
"""

import asyncio
import httpx
from typing import Dict

# API base URL (adjust if needed)
API_URL = "http://localhost:8000"

# Expected security headers
REQUIRED_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-XSS-Protection": "1; mode=block",
    "X-Frame-Options": "SAMEORIGIN",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Content-Security-Policy": None,  # Just check if present
    "Permissions-Policy": None,  # Just check if present
    "Strict-Transport-Security": None,  # Just check if present
}


async def test_security_headers() -> None:
    """Test that all required security headers are present."""
    print("🔒 Testing Security Headers...\n")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_URL}/health")
            
            print(f"✓ API Status: {response.status_code}")
            print(f"✓ URL: {response.url}\n")
            
            headers = response.headers
            
            # Check each required header
            passed = 0
            failed = 0
            
            for header_name, expected_value in REQUIRED_HEADERS.items():
                if header_name in headers:
                    value = headers[header_name]
                    
                    if expected_value is None:
                        # Just checking if header exists
                        print(f"✅ {header_name}: PRESENT")
                        if len(value) < 60:
                            print(f"   Value: {value}\n")
                        else:
                            print(f"   Value: {value[:60]}...\n")
                        passed += 1
                    elif headers[header_name] == expected_value:
                        # Header exists with correct value
                        print(f"✅ {header_name}: CORRECT")
                        print(f"   Value: {value}\n")
                        passed += 1
                    else:
                        # Header exists but value doesn't match
                        print(f"⚠️  {header_name}: MISMATCH")
                        print(f"   Expected: {expected_value}")
                        print(f"   Got: {value}\n")
                        failed += 1
                else:
                    # Header missing
                    print(f"❌ {header_name}: MISSING\n")
                    failed += 1
            
            # Summary
            print("=" * 60)
            print(f"📊 Results: {passed} passed, {failed} failed")
            
            if failed == 0:
                print("✅ All security headers are correctly configured!")
            else:
                print(f"⚠️  {failed} security header(s) need attention")
            
            print("=" * 60)
            
            # Additional info
            print("\n📝 Additional Headers Found:")
            excluded_headers = {
                "content-length", "content-type", "date",
                "server", "vary", "connection", "transfer-encoding"
            }
            
            for name, value in headers.items():
                if name.lower() not in [h.lower() for h in REQUIRED_HEADERS.keys()] \
                   and name.lower() not in excluded_headers:
                    if len(value) < 60:
                        print(f"   {name}: {value}")
                    else:
                        print(f"   {name}: {value[:60]}...")
            
    except Exception as e:
        print(f"❌ Error testing security headers: {e}")
        print(f"   Make sure API is running at {API_URL}")


async def test_cors_headers() -> None:
    """Test CORS configuration."""
    print("\n\n🔐 Testing CORS Configuration...\n")
    
    try:
        async with httpx.AsyncClient() as client:
            # Test preflight request
            response = await client.options(
                f"{API_URL}/auth/me",
                headers={
                    "Origin": "http://localhost:5173",
                    "Access-Control-Request-Method": "GET",
                }
            )
            
            cors_headers = {
                "access-control-allow-origin": "http://localhost:5173",
                "access-control-allow-credentials": "true",
            }
            
            print(f"✓ Preflight Request: {response.status_code}\n")
            
            passed = 0
            for header, expected in cors_headers.items():
                value = response.headers.get(header)
                if value == expected:
                    print(f"✅ {header}: {value}")
                    passed += 1
                elif value:
                    print(f"⚠️  {header}: {value} (expected: {expected})")
                else:
                    print(f"❌ {header}: MISSING")
            
            print(f"\n✓ CORS Headers: {passed}/2 correct")
            
    except Exception as e:
        print(f"❌ Error testing CORS: {e}")


if __name__ == "__main__":
    asyncio.run(test_security_headers())
    asyncio.run(test_cors_headers())
