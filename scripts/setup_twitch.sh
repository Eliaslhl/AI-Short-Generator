#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
#  Phase 2c Setup: Twitch API Integration
# ═══════════════════════════════════════════════════════════════════════

echo "📺 Phase 2c Setup: Twitch API Integration"
echo "=========================================="
echo ""

# Step 1: Get Twitch Credentials
echo "1️⃣ Getting Twitch OAuth Credentials"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Go to https://dev.twitch.tv/console/apps"
echo "1. Click 'Create Application'"
echo "2. Fill in:"
echo "   - Name: AI-Shorts-Generator (or your app name)"
echo "   - OAuth Redirect URL: http://localhost:8000/auth/twitch/callback"
echo "   - Category: Application Integration"
echo "3. Accept terms and create"
echo "4. Click 'Manage' → Copy 'Client ID' and 'Client Secret'"
echo ""

read -p "Enter TWITCH_CLIENT_ID: " client_id
read -sp "Enter TWITCH_CLIENT_SECRET: " client_secret
echo ""

# Step 2: Update .env
echo ""
echo "2️⃣ Updating .env file"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Create backup
cp backend/.env backend/.env.backup

# Update .env (use sed for cross-platform)
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' "s/TWITCH_CLIENT_ID=$/TWITCH_CLIENT_ID=$client_id/" backend/.env
    sed -i '' "s/TWITCH_CLIENT_SECRET=$/TWITCH_CLIENT_SECRET=$client_secret/" backend/.env
else
    # Linux
    sed -i "s/TWITCH_CLIENT_ID=$/TWITCH_CLIENT_ID=$client_id/" backend/.env
    sed -i "s/TWITCH_CLIENT_SECRET=$/TWITCH_CLIENT_SECRET=$client_secret/" backend/.env
fi

echo "✅ Credentials saved to backend/.env"
echo ""

# Step 3: Test Twitch Client
echo "3️⃣ Testing Twitch Client"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

python3 << 'TESTEOF'
import sys
sys.path.insert(0, '.')

from backend.services.twitch_client import create_twitch_client

print("Testing Twitch client connection...")
client = create_twitch_client()

# Test: Get user by login
user = client.get_user_by_login("twitch")
if user:
    print(f"✅ Twitch API working! User ID: {user['id']}")
else:
    print("⚠️ Could not fetch test user (may need valid credentials)")

TESTEOF

echo ""
echo "4️⃣ Setup Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✅ Phase 2c: Twitch API Integration Ready!"
echo ""
echo "Next steps:"
echo "  1. Test video download: python tests/test_twitch_download.py"
echo "  2. Start API server: make back"
echo "  3. Try /api/generate/twitch/advanced endpoint with a VOD URL"
echo ""
