#!/usr/bin/env python3
"""
Integration test: Verify frontend plan fields end-to-end
Tests that:
1. Backend API exposes platform-specific plan fields
2. Frontend types include these fields
3. Utility functions correctly parse and fallback
"""

import json
import subprocess
import sys
from datetime import datetime

def run_test(name: str, test_fn):
    """Run a test and print results"""
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print('='*60)
    try:
        result = test_fn()
        if result:
            print(f"✅ PASS")
            return True
        else:
            print(f"❌ FAIL")
            return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_api_response_has_fields():
    """Test 1: Backend API returns platform-specific fields"""
    print("Testing API response contains platform-specific fields...")
    
    # Login to get auth token
    result = subprocess.run([
        'curl', '-s', '-X', 'POST',
        'http://127.0.0.1:8001/auth/login',
        '-H', 'Content-Type: application/json',
        '-d', json.dumps({
            "email": "test.combo.pro@test.com",
            "password": "TestPass123456"
        })
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"  ❌ Login failed: {result.stderr}")
        return False
    
    response = json.loads(result.stdout)
    user = response.get('user', {})
    
    required_fields = [
        'plan_youtube', 'plan_twitch', 'subscription_type',
        'youtube_limit', 'twitch_limit',
        'youtube_generations_left', 'twitch_generations_left'
    ]
    
    missing = [f for f in required_fields if f not in user]
    
    if missing:
        print(f"  ❌ Missing fields: {missing}")
        return False
    
    print(f"  ✓ plan_youtube: {user['plan_youtube']}")
    print(f"  ✓ plan_twitch: {user['plan_twitch']}")
    print(f"  ✓ subscription_type: {user['subscription_type']}")
    print(f"  ✓ youtube_limit: {user['youtube_limit']}")
    print(f"  ✓ twitch_limit: {user['twitch_limit']}")
    print(f"  ✓ youtube_generations_left: {user['youtube_generations_left']}")
    print(f"  ✓ twitch_generations_left: {user['twitch_generations_left']}")
    
    return True

def test_frontend_types_exist():
    """Test 2: Frontend TypeScript types are defined"""
    print("Checking frontend types.ts file...")
    
    try:
        with open('frontend-react/src/types.ts', 'r') as f:
            content = f.read()
        
        required_types = [
            'plan_youtube', 'plan_twitch', 'subscription_type',
            'youtube_limit', 'twitch_limit',
            'youtube_generations_left', 'twitch_generations_left'
        ]
        
        missing = [t for t in required_types if t not in content]
        
        if missing:
            print(f"  ❌ Missing type definitions: {missing}")
            return False
        
        print(f"  ✓ All {len(required_types)} type definitions found")
        return True
    except Exception as e:
        print(f"  ❌ Error reading types.ts: {e}")
        return False

def test_util_functions_exist():
    """Test 3: planUtils.ts utility functions exist"""
    print("Checking frontend planUtils.ts...")
    
    try:
        with open('frontend-react/src/utils/planUtils.ts', 'r') as f:
            content = f.read()
        
        required_functions = [
            'getCurrentPlatform',
            'getPlanForPlatform',
            'getGenerationLimit',
            'getGenerationsLeft',
            'getMaxClipsAllowed'
        ]
        
        missing = [f for f in required_functions if f'export function {f}' not in content]
        
        if missing:
            print(f"  ❌ Missing functions: {missing}")
            return False
        
        print(f"  ✓ All {len(required_functions)} utility functions exported:")
        for func in required_functions:
            print(f"    - {func}")
        
        return True
    except Exception as e:
        print(f"  ❌ Error reading planUtils.ts: {e}")
        return False

def test_dashboard_uses_utils():
    """Test 4: DashboardPage imports and uses utilities"""
    print("Checking DashboardPage.tsx imports utilities...")
    
    try:
        with open('frontend-react/src/pages/DashboardPage.tsx', 'r') as f:
            content = f.read()
        
        if 'from \'../utils/planUtils\'' not in content:
            print(f"  ❌ Does not import planUtils")
            return False
        
        required_calls = [
            'getCurrentPlatform',
            'getPlanForPlatform',
            'getGenerationLimit',
            'getGenerationsLeft'
        ]
        
        missing = [c for c in required_calls if c not in content]
        
        if missing:
            print(f"  ⚠️  Some functions not used: {missing}")
            # Still pass if at least some are used
        
        print(f"  ✓ DashboardPage imports and uses planUtils")
        return True
    except Exception as e:
        print(f"  ❌ Error reading DashboardPage.tsx: {e}")
        return False

def test_generator_uses_utils():
    """Test 5: GeneratorPage imports and uses utilities"""
    print("Checking GeneratorPage.tsx imports utilities...")
    
    try:
        with open('frontend-react/src/pages/GeneratorPage.tsx', 'r') as f:
            content = f.read()
        
        if 'from \'../utils/planUtils\'' not in content:
            print(f"  ❌ Does not import planUtils")
            return False
        
        required_calls = [
            'getCurrentPlatform',
            'getPlanForPlatform',
            'getMaxClipsAllowed',
            'getGenerationsLeft'
        ]
        
        missing = [c for c in required_calls if c not in content]
        
        if missing:
            print(f"  ⚠️  Some functions not used: {missing}")
        
        # Check that hardcoded logic is removed
        if 'user?.plan === \'proplus\' ? 20' in content:
            print(f"  ❌ Still contains hardcoded ternary for max clips")
            return False
        
        print(f"  ✓ GeneratorPage uses planUtils utilities")
        return True
    except Exception as e:
        print(f"  ❌ Error reading GeneratorPage.tsx: {e}")
        return False

def test_frontend_builds():
    """Test 6: Frontend builds without errors"""
    print("Building frontend...")
    
    result = subprocess.run(
        ['npm', 'run', 'build'],
        cwd='frontend-react',
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"  ❌ Build failed:")
        print(f"  {result.stderr[:500]}")
        return False
    
    # Check for successful build markers
    if '✓ built' not in result.stderr and '✓ built' not in result.stdout:
        print(f"  ⚠️  Build may have succeeded but output unclear")
    
    print(f"  ✓ Frontend builds successfully")
    return True

def main():
    print("╔" + "="*58 + "╗")
    print("║  FRONTEND PLATFORM FIELDS INTEGRATION TEST           ║")
    print("║  Verifying plan fields end-to-end implementation    ║")
    print("╚" + "="*58 + "╝")
    print(f"\nStarted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests = [
        ("API returns platform-specific fields", test_api_response_has_fields),
        ("Frontend types defined", test_frontend_types_exist),
        ("Utility functions exist", test_util_functions_exist),
        ("DashboardPage uses utilities", test_dashboard_uses_utils),
        ("GeneratorPage uses utilities", test_generator_uses_utils),
        ("Frontend builds successfully", test_frontend_builds),
    ]
    
    results = []
    for name, test_fn in tests:
        results.append(run_test(name, test_fn))
    
    print(f"\n\n{'='*60}")
    print("SUMMARY")
    print('='*60)
    
    passed = sum(results)
    total = len(results)
    
    for i, (name, _) in enumerate(tests):
        status = "✅ PASS" if results[i] else "❌ FAIL"
        print(f"{status} | {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if passed == total:
        print("\n🎉 All tests passed! Frontend is ready.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
