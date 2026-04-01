#!/bin/bash
# ============================================================================
# PROD DEPLOYMENT GUIDE: Google OAuth + Alembic Heads Fix
# ============================================================================
# Deployment date: 2026-04-01
# Commit: bc614e0
#
# This script summarizes the steps to deploy the critical fix in production.
# ============================================================================

echo "🚀 PROD DEPLOYMENT: Google OAuth plan NOT NULL Fix"
echo "=================================================="
echo ""

# Step 1: Ensure code is pulled
echo "1️⃣  STEP 1: Pull the latest code"
echo "   cd /path/to/ai-shorts-generator"
echo "   git pull origin main"
echo ""
echo "   ✅ Ensure you see:"
echo "      - backend/auth/router.py (modified)"
echo "      - alembic/versions/20260401_fix_plan_not_null_and_merge_heads.py (new)"
echo ""

# Step 2: Run migrations
echo "2️⃣  STEP 2: Run Alembic migrations"
echo "   source .venv/bin/activate"
echo "   .venv/bin/alembic upgrade head"
echo ""
echo "   This will:"
echo "   - Resolve 'Multiple head revisions' error"
echo "   - Add server default 'free' to users.plan column"
echo "   - Ensure future INSERTs work without plan column"
echo ""

# Step 3: Verify migration applied
echo "3️⃣  STEP 3: Verify migration applied"
echo "   .venv/bin/alembic current"
echo "   # Should show: rev20260401_fix_plan"
echo ""

# Step 4: Check database state
echo "4️⃣  STEP 4: Verify database default in PostgreSQL"
echo "   psql \"\$DATABASE_URL\" -c \\"SELECT column_name, column_default, is_nullable FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'plan'\\""
echo ""
echo "   ✅ Expected output:"
echo "      column_name | column_default | is_nullable"
echo "      plan        | 'free'::plan   | NO"
echo ""

# Step 5: Restart services
echo "5️⃣  STEP 5: Restart FastAPI/Uvicorn"
echo "   # Restart your container or systemd service"
echo "   # This ensures the updated backend/auth/router.py code is loaded"
echo ""

# Step 6: Smoke test
echo "6️⃣  STEP 6: Smoke test Google OAuth"
echo "   1. Visit: https://your-prod-domain.com/auth/google"
echo "   2. Log in with a Google account that is NOT already registered"
echo "   3. Verify you are redirected to /auth/callback?token=..."
echo "   4. Verify new user is created with plan='free'"
echo ""
echo "   Check logs for any errors (should be none now)"
echo ""

# Summary
echo "================================"
echo "🎯 Summary of changes"
echo "================================"
echo ""
echo "📝 Files modified:"
echo "   - backend/auth/router.py"
echo "     └ INSERT statement now includes plan='free'"
echo ""
echo "📝 Files created:"
echo "   - alembic/versions/20260401_fix_plan_not_null_and_merge_heads.py"
echo "     └ Migration to add server default + resolve heads"
echo ""
echo "🔍 What was broken:"
echo "   - Google OAuth INSERT missing 'plan' column"
echo "   - Production DB has users.plan NOT NULL without server default"
echo "   - Alembic reported 'Multiple head revisions'"
echo ""
echo "✅ What is fixed:"
echo "   - Raw SQL INSERT now provides plan='free' explicitly"
echo "   - Server default 'free' added to ensure robustness"
echo "   - Alembic heads unified (single head: rev20260401_fix_plan)"
echo ""

echo "⏱️  Estimated deployment time: 5-10 minutes"
echo ""
echo "❓ Questions?"
echo "   See: PROD_FIX_PLAN_20260401.md"
echo ""
