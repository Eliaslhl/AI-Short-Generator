# 🔥 URGENT: Orphaned Migration Reference in Production

## 🚨 Problem in Prod

Alembic failing with:
```
ERROR: Can't locate revision identified by '20260329_idempotent_add_plan_and_override_columns'
```

**Root Cause**:
- Production database `alembic_version` table has a stale entry
- It references a **migration filename** instead of a proper **revision ID**
- This orphaned reference blocks all subsequent migrations

**Why This Happened**:
- Previous deployment had migration file naming issues
- Database stored wrong reference and locked the chain

---

## ✅ Fix Deployed

**New migration**: `20260401_cleanup_orphan.py`
- Revision ID: `rev20260401_cleanup_orphan`
- Does nothing to schema (no-op migration)
- Provides clean migration chain for Alembic to proceed

This allows Alembic to bypass the orphaned reference.

---

## 📋 Deploy Steps for Production

### Step 1: Pull Latest Code
```bash
cd /path/to/ai-shorts-generator
git pull origin main
# Should show: 4102965+ CRITICAL: Fix plan ENUM casting
```

### Step 2: CRITICAL — Manually Clean Database

Before running migrations, **manually clean the orphaned entry from the database**:

```bash
# Connect to prod PostgreSQL
psql "$DATABASE_URL"

# In psql console:
SELECT * FROM alembic_version;
# Expected: You'll see entries, possibly including an orphaned filename reference

# DELETE the orphaned entry (if it exists)
DELETE FROM alembic_version WHERE version_num = '20260329_idempotent_add_plan_and_override_columns';

# Verify it's gone
SELECT * FROM alembic_version;
```

### Step 3: Run Migrations
```bash
source .venv/bin/activate
.venv/bin/alembic upgrade head
```

Expected output:
```
INFO [alembic.runtime.migration] Running upgrade rev20260401_emergency_enum_fix
INFO [alembic.runtime.migration] Running upgrade rev20260401_merge_all_heads
INFO [alembic.runtime.migration] Running upgrade rev20260401_cleanup_orphan
```

### Step 4: Verify
```bash
.venv/bin/alembic current
# Expected: rev20260401_cleanup_orphan

.venv/bin/alembic heads
# Expected: rev20260401_cleanup_orphan (head)
```

### Step 5: Restart FastAPI
```bash
# Restart container/service
```

### Step 6: Smoke Test Google OAuth
```
Visit: https://your-domain.com/auth/google
Login with new Google account
Should work without 502 error
```

---

## ⚠️ If Manual Cleanup Fails

If you can't connect to PostgreSQL or don't want to manually delete:

**Option A: Use Alembic stamp** (if DB is totally corrupted)
```bash
# Force-stamp DB to ignore broken history
.venv/bin/alembic stamp rev20260401_cleanup_orphan
```

**Option B: Restart clean** (nuclear option)
```bash
# Drop and recreate alembic_version table (loses history tracking)
psql "$DATABASE_URL" -c "DROP TABLE alembic_version;"
# Then run upgrade (will recreate table and apply all migrations)
.venv/bin/alembic upgrade head
```

**Option C: Use Railway console**
- If using Railway, you can execute SQL in their console instead of psql

---

## 📊 What Changed in Latest Push

| File | Change |
|------|--------|
| `backend/auth/router.py` | ✏️ ENUM cast `::plan` |
| `alembic/.../20260401_emergency_enum_fix.py` | ✨ Create ENUM type |
| `alembic/.../20260401_merge_all_heads.py` | ✨ Merge divergent heads |
| `alembic/.../20260401_cleanup_orphan.py` | ✨ **NEW** — Clean orphaned ref |

---

## 🎯 Expected End State After Deploy

✅ No "Multiple head revisions" error  
✅ No "Can't locate revision" error  
✅ Single Alembic head: `rev20260401_cleanup_orphan`  
✅ Google OAuth login works (no 502 errors)  
✅ `plan` ENUM type exists  
✅ `users.plan` column properly typed  

---

## ⏱️ Deployment Timeline

- Pull code: 1 min
- Manual DB cleanup: 2-3 min
- Run migrations: 2-3 min
- Restart & test: 2-3 min
- **Total: ~10 minutes**

---

**Commit**: 4102965+  
**Severity**: 🔥 CRITICAL (blocks all migrations)  
**Risk**: ✅ LOW (only cleans DB references, no data loss)
