#!/bin/bash
# ============================================================================
# Sync Twitch Credentials from Railway to Local .env
# ============================================================================
# This script copies Twitch API credentials from Railway production environment
# and adds them to your local .env file for local development
# ============================================================================

set -e

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Railway → Local Twitch Credentials Sync${NC}"
echo "=============================================="
echo ""

# Check if railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo -e "${RED}❌ railway CLI not found${NC}"
    echo ""
    echo "Install it with:"
    echo "  npm i -g @railway/cli"
    echo "  OR"
    echo "  brew install railway"
    echo ""
    exit 1
fi

# Check if we're connected to Railway
echo -e "${YELLOW}🔍 Checking Railway connection...${NC}"
if ! railway whoami > /dev/null 2>&1; then
    echo -e "${RED}❌ Not logged into Railway${NC}"
    echo ""
    echo "Login with:"
    echo "  railway login"
    echo ""
    exit 1
fi

echo -e "${GREEN}✓ Connected to Railway${NC}"
echo ""

# Get the credentials from Railway
echo -e "${YELLOW}📡 Fetching credentials from Railway...${NC}"
TWITCH_CLIENT_ID=$(railway variable get TWITCH_CLIENT_ID 2>/dev/null || echo "")
TWITCH_CLIENT_SECRET=$(railway variable get TWITCH_CLIENT_SECRET 2>/dev/null || echo "")

if [ -z "$TWITCH_CLIENT_ID" ] || [ -z "$TWITCH_CLIENT_SECRET" ]; then
    echo -e "${RED}❌ Could not fetch credentials from Railway${NC}"
    echo ""
    echo "Possible reasons:"
    echo "  1. You're not in the right Railway project"
    echo "  2. The variables are not set on Railway"
    echo "  3. You don't have permission to view them"
    echo ""
    echo "To check Railway variables:"
    echo "  railway variable list"
    echo ""
    exit 1
fi

# Backup current .env
cp ".env" ".env.backup.$(date +%s)"
echo -e "${GREEN}✓ Backup created${NC}"

# Remove old credentials if they exist
sed -i '' '/^TWITCH_CLIENT_ID=/d' ".env"
sed -i '' '/^TWITCH_CLIENT_SECRET=/d' ".env"

# Add credentials
cat >> ".env" << EOF

# ── Twitch API (Synced from Railway) ───────────────
TWITCH_CLIENT_ID=${TWITCH_CLIENT_ID}
TWITCH_CLIENT_SECRET=${TWITCH_CLIENT_SECRET}
EOF

echo -e "${GREEN}✓ Credentials added to .env${NC}"
echo ""

# Show confirmation
if grep -q "TWITCH_CLIENT_ID=$TWITCH_CLIENT_ID" ".env"; then
    echo -e "${GREEN}🎉 Sync successful!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Restart the backend: make backend"
    echo "  2. Try fetching Twitch VODs from the frontend"
    echo ""
else
    echo -e "${RED}❌ Sync verification failed${NC}"
    exit 1
fi
