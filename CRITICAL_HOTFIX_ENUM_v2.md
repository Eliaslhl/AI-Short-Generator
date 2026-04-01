# 🚨 CRITICAL HOTFIX v2 – ENUM Casting Issue

## Status: 🚀 PUSHED (commit: d3fd3e5)

---

## New Problem Found in Prod

```
InvalidTextRepresentationError: invalid input value for enum plan: "free"
```

**Root Cause**:
- PostgreSQL `plan` column is defined as **ENUM** type
- String value `'free'` cannot be inserted directly into an ENUM column
- Requires explicit casting: `'free'::plan` (not just `'free'`)
- ENUM type itself may not exist or be misconfigured

---

## Critical Fixes Applied

### 1. Code Fix – `backend/auth/router.py`
Changed INSERT statement from:
```sql
VALUES (:id, :email, :gid, :full, :avatar, :plan, ...)
```

To:
```sql
VALUES (:id, :email, :gid, :full, :avatar, :plan::plan, ...)
                                                ^^^^^^^^
                                          Explicit ENUM cast
```

### 2. Database Migration – TWO new migrations

**Migration 1**: `20260401_emergency_enum_fix.py`
- Creates `plan` ENUM type if missing
- Ensures `users.plan` column has correct ENUM type
- Sets server default to `'free'::plan`

**Migration 2**: `20260401_merge_all_heads.py`
- Merges all divergent migration heads into **single unified head**
- Fixes "Multiple head revisions" Alembic error

---

## Deploy in Prod NOW ⏱️

### Step 1: Pull Latest Code
```bash
cd /path/to/ai-shorts-generator
git pull origin main
# Should show: d3fd3e5 CRITICAL: Fix plan ENUM casting...
```

### Step 2: Run Alembic Migrations
```bash
source .venv/bin/activate

# Run migrations
.venv/bin/alembic upgrade head

# You should see:
# INFO [alembic.runtime.migration] Running upgrade rev20260401_emergency_enum_fix
# INFO [alembic.runtime.migration] Running upgrade rev20260401_merge_all_heads
```

### Step 3: Verify
```bash
# Check current migration
.venv/bin/alembic current
# Expected: rev20260401_merge_all_heads

# Check single head (not "Multiple")
.venv/bin/alembic heads
# Expected: rev20260401_merge_all_heads (head)

# Check plan column in DB
psql "$DATABASE_URL" -c "\d users" | grep plan
# Should show: plan | plan (plan type, not text)

# Verify enum type exists
psql "$DATABASE_URL" -c "SELECT typname FROM pg_type WHERE typname='plan';"
# Expected output: plan
```

### Step 4: Restart FastAPI
```bash
# Restart Docker container or systemd service
# Ensures new backend/auth/router.py code is loaded
```

### Step 5: Smoke Test
```bash
# Test Google OAuth login
# Visit: https://your-prod-domain.com/auth/google
# Log in with new Google account
# Should create user without 502 error
```

---

## Why This Happened

1. **Multiple migrations** diverged the history (hence "Multiple head revisions")
2. **ENUM type never created** properly in production
3. **Raw SQL INSERT** tried to insert string into ENUM column without casting
4. PostgreSQL strict type checking rejected the value

---

## Key Changes in This Release

| File | Change |
|------|--------|
| `backend/auth/router.py` | ✏️ Add `::plan` ENUM cast |
| `alembic/.../20260401_emergency_enum_fix.py` | ✨ Create/fix ENUM type |
| `alembic/.../20260401_merge_all_heads.py` | ✨ Merge migration branches |

---

## Post-Deployment Verification

```bash
# 1. No more "Multiple head revisions" error
.venv/bin/alembic heads
# → Shows exactly 1 head

# 2. ENUM type exists
SELECT enum_range(NULL::plan);
# → Shows array of valid values: [free, standard, pro, proplus]

# 3. Google OAuth works
# New user creation via Google should succeed

# 4. Logs clean (no InvalidTextRepresentation errors)
# Check container logs for any ENUM-related errors
```

---

## Rollback (if needed)

```bash
# Downgrade 2 migrations
.venv/bin/alembic downgrade -2

# Revert code changes
git revert --no-edit d3fd3e5

# Restart services
```

---

**Deployment Time**: ~5 minutes  
**Risk Level**: ⚠️ CRITICAL but safe (only adds/fixes schema, no data loss)  
**Impact**: 🎯 Fixes 502 errors on Google OAuth login
