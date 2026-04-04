#!/bin/bash

# ============================================================================
# DuckDNS Setup Script for macOS - Home Proxy Configuration
# ============================================================================
# This script:
# 1. Creates a DuckDNS subdomain (requires token from duckdns.org)
# 2. Sets up automatic IP refresh via cron job
# 3. Tests connectivity
# 4. Provides Railway configuration

set -e

echo "🚀 DuckDNS Setup for Home Proxy (macOS)"
echo "========================================"

# Step 1: Get DuckDNS Token
echo ""
echo "1️⃣  DuckDNS Token Setup"
echo "  Go to https://www.duckdns.org and create an account"
echo "  Copy your token from the dashboard"
read -p "Enter your DuckDNS token: " DUCKDNS_TOKEN

if [ -z "$DUCKDNS_TOKEN" ]; then
    echo "❌ Token cannot be empty"
    exit 1
fi

# Step 2: Get desired subdomain
echo ""
echo "2️⃣  DuckDNS Subdomain"
read -p "Enter desired subdomain (e.g., 'my-proxy'): " DUCKDNS_SUBDOMAIN

if [ -z "$DUCKDNS_SUBDOMAIN" ]; then
    echo "❌ Subdomain cannot be empty"
    exit 1
fi

DUCKDNS_URL="${DUCKDNS_SUBDOMAIN}.duckdns.org"

# Step 3: Create cron job for auto-refresh (every 5 minutes)
echo ""
echo "3️⃣  Setting up auto-refresh cron job (every 5 minutes)"

CRON_CMD="/usr/bin/curl -s 'https://www.duckdns.org/update?domains=${DUCKDNS_SUBDOMAIN}&token=${DUCKDNS_TOKEN}&verbose=true' > /tmp/duckdns_update.log 2>&1"

# Create a shell script for the cron job
CRON_SCRIPT_PATH="$HOME/.duckdns_update.sh"
cat > "$CRON_SCRIPT_PATH" << 'EOF'
#!/bin/bash
DUCKDNS_TOKEN="$1"
DUCKDNS_SUBDOMAIN="$2"
/usr/bin/curl -s "https://www.duckdns.org/update?domains=${DUCKDNS_SUBDOMAIN}&token=${DUCKDNS_TOKEN}&verbose=true" > /tmp/duckdns_update.log 2>&1
EOF

chmod +x "$CRON_SCRIPT_PATH"

# Add cron job (remove old one first if exists)
crontab -l 2>/dev/null | grep -v "duckdns_update" | crontab - || true
(crontab -l 2>/dev/null || true; echo "*/5 * * * * $CRON_SCRIPT_PATH \"$DUCKDNS_TOKEN\" \"$DUCKDNS_SUBDOMAIN\"") | crontab -

echo "✅ Cron job installed: $CRON_SCRIPT_PATH"
echo "   Updates every 5 minutes"

# Step 4: Initial update
echo ""
echo "4️⃣  Performing initial DuckDNS update..."
RESPONSE=$(curl -s "https://www.duckdns.org/update?domains=${DUCKDNS_SUBDOMAIN}&token=${DUCKDNS_TOKEN}&verbose=true")
echo "   Response: $RESPONSE"

# Step 5: Wait and resolve
echo ""
echo "5️⃣  Waiting for DNS propagation (10 seconds)..."
sleep 10

PUBLIC_IP=$(curl -s https://api.ipify.org)
RESOLVED_IP=$(dig +short "${DUCKDNS_URL}" @8.8.8.8 | tail -n1)

echo "   Your public IP: $PUBLIC_IP"
echo "   DuckDNS resolved: $RESOLVED_IP"

if [ "$PUBLIC_IP" == "$RESOLVED_IP" ]; then
    echo "✅ DNS resolution successful!"
else
    echo "⚠️  DNS may take a moment to propagate. Retrying in 30 seconds..."
    sleep 30
    RESOLVED_IP=$(dig +short "${DUCKDNS_URL}" @8.8.8.8 | tail -n1)
    echo "   DuckDNS resolved: $RESOLVED_IP"
fi

# Step 6: Test Tinyproxy connection
echo ""
echo "6️⃣  Testing Tinyproxy connection via DuckDNS..."
read -p "Enter Tinyproxy auth user (default: railwayproxy): " PROXY_USER
PROXY_USER=${PROXY_USER:-railwayproxy}

read -sp "Enter Tinyproxy auth password: " PROXY_PASS
echo ""

PROXY_URL="http://${PROXY_USER}:${PROXY_PASS}@${DUCKDNS_URL}:53128"

TEST_RESULT=$(curl -s -x "$PROXY_URL" https://api.ipify.org 2>&1)
echo "   Proxy returned IP: $TEST_RESULT"

if [ "$TEST_RESULT" == "$PUBLIC_IP" ]; then
    echo "✅ Proxy working! Your egress IP matches."
else
    echo "⚠️  Could not verify proxy. Check firewall/port forwarding."
fi

# Step 7: Configuration summary
echo ""
echo "=========================================="
echo "✅ DuckDNS Setup Complete!"
echo "=========================================="
echo ""
echo "📋 Railway Configuration:"
echo "   Set these environment variables:"
echo ""
echo "   YTDLP_PROXY_URL=http://${PROXY_USER}:${PROXY_PASS}@${DUCKDNS_URL}:53128"
echo ""
echo "📋 Local Testing:"
echo "   curl -x 'http://${PROXY_USER}:${PROXY_PASS}@${DUCKDNS_URL}:53128' https://api.ipify.org"
echo ""
echo "📋 Cron Job:"
echo "   Location: $CRON_SCRIPT_PATH"
echo "   Frequency: Every 5 minutes"
echo "   Logs: /tmp/duckdns_update.log"
echo ""
echo "📋 Verify DNS:"
echo "   dig ${DUCKDNS_URL}"
echo "   nslookup ${DUCKDNS_URL}"
echo ""
echo "⏰ Notes:"
echo "   • DNS may take 10-60 seconds to propagate"
echo "   • Cron will auto-update your IP every 5 minutes"
echo "   • Verify Tinyproxy is running: lsof -i :53128"
echo ""
