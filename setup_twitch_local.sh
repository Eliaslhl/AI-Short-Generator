#!/bin/bash
# ============================================================================
# Local Development Setup for Twitch Integration
# ============================================================================
# This script fixes the .env file for local Twitch VOD download support
#
# Prerequisites:
# 1. Go to https://dev.twitch.tv/console/apps
# 2. Create an Application
# 3. Copy your Client ID and Client Secret
# 4. Run this script: ./setup_twitch_local.sh
# ============================================================================

set -e

ENV_FILE=".env"

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🎬 Twitch Local Setup${NC}"
echo "================================"
echo ""

# Check if .env exists
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}❌ Error: .env file not found${NC}"
    exit 1
fi

# Check if TWITCH credentials are already set
if grep -q "TWITCH_CLIENT_ID=" "$ENV_FILE" && [ -n "$(grep 'TWITCH_CLIENT_ID=' "$ENV_FILE" | cut -d'=' -f2)" ]; then
    echo -e "${GREEN}✓ Twitch credentials already configured${NC}"
    echo ""
    read -p "Do you want to update them? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping update."
        exit 0
    fi
fi

# Prompt for credentials
echo -e "${YELLOW}Please provide your Twitch API credentials:${NC}"
echo "Get them from: https://dev.twitch.tv/console/apps"
echo ""

read -p "Enter TWITCH_CLIENT_ID: " CLIENT_ID
read -p "Enter TWITCH_CLIENT_SECRET: " CLIENT_SECRET

if [ -z "$CLIENT_ID" ] || [ -z "$CLIENT_SECRET" ]; then
    echo -e "${RED}❌ Error: Credentials cannot be empty${NC}"
    exit 1
fi

# Backup original .env
cp "$ENV_FILE" "${ENV_FILE}.backup.$(date +%s)"
echo -e "${GREEN}✓ Backup created: ${ENV_FILE}.backup.*${NC}"

# Remove old credentials if they exist
sed -i '' '/^TWITCH_CLIENT_ID=/d' "$ENV_FILE"
sed -i '' '/^TWITCH_CLIENT_SECRET=/d' "$ENV_FILE"

# Add new credentials
echo "" >> "$ENV_FILE"
echo "# ── Twitch API ────────────────────────────────────────────────" >> "$ENV_FILE"
echo "TWITCH_CLIENT_ID=$CLIENT_ID" >> "$ENV_FILE"
echo "TWITCH_CLIENT_SECRET=$CLIENT_SECRET" >> "$ENV_FILE"

echo -e "${GREEN}✓ Twitch credentials added to .env${NC}"
echo ""

# Verify
if grep -q "TWITCH_CLIENT_ID=$CLIENT_ID" "$ENV_FILE"; then
    echo -e "${GREEN}✓ Configuration verified${NC}"
    echo ""
    echo -e "${GREEN}🎉 Setup complete!${NC}"
    echo ""
    echo "You can now:"
    echo "1. Start the backend: make backend"
    echo "2. Try fetching Twitch VODs from the frontend"
    echo ""
else
    echo -e "${RED}❌ Error: Configuration verification failed${NC}"
    exit 1
fi
