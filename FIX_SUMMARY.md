## 🚨 URGENT PROD FIX – Complete Summary

**Status**: ✅ Code committed and pushed to `main` (commit: bc614e0)  
**Date**: 2026-04-01  
**Impact**: Critical — Google OAuth broken in production

---

## 🔴 Problem

### Error 1: NotNullViolationError on Google OAuth
```
sqlalchemy.dialects.postgresql.asyncpg.IntegrityError: 
null value in column "plan" of relation "users" violates not-null constraint
```

**Root Cause**:
- The `users.plan` column is `NOT NULL` in production PostgreSQL
- **No server-side default** was defined
- Google OAuth callback INSERT statement **omitted** the `plan` column
- Result: Every new Google login → 502 Bad Gateway

### Error 2: Alembic "Multiple head revisions"
```
ERROR: Multiple head revisions are present for given argument 'head'
```

**Root Cause**:
- Migration history has divergent branches (at least 2 heads)
- This blocks `alembic upgrade head` from working
- Schema drift can occur

---

## ✅ Solution (2 parts)

### Part 1: Code Hotfix – `backend/auth/router.py`

**Change**: Include `plan='free'` in the raw SQL INSERT for new users

**Before**:
```python
res = await db.execute(
    text(
        "INSERT INTO users (id, email, google_id, full_name, avatar_url, is_verified, is_active, created_at)"
        " VALUES (:id, :email, :gid, :full, :avatar, true, true, now()) RETURNING id"
    ),
    {
        "id": new_id,
        "email": email,
        "gid": google_id,
        "full": full_name,
        "avatar": avatar_url,
    },
)
```

**After**:
```python
res = await db.execute(
    text(
        "INSERT INTO users (id, email, google_id, full_name, avatar_url, plan, is_verified, is_active, created_at)"
        " VALUES (:id, :email, :gid, :full, :avatar, :plan, true, true, now()) RETURNING id"
    ),
    {
        "id": new_id,
        "email": email,
        "gid": google_id,
        "full": full_name,
        "avatar": avatar_url,
        "plan": "free",  # ← ADD THIS
    },
)
```

**Rationale**:
- Defensive programming: raw SQL bypasses ORM defaults
- Explicit `plan='free'` ensures INSERT succeeds even if DB column is NOT NULL
- Provides immediate relief for the 502 error

### Part 2: Database Migration – `alembic/versions/20260401_fix_plan_not_null_and_merge_heads.py`

**Changes**:
1. **Adds server default** to `users.plan` column
2. **Unifies Alembic heads** to resolve "Multiple head revisions" error

**Migration SQL** (executed in `upgrade()`):
```sql
ALTER TABLE users
ALTER COLUMN plan SET DEFAULT 'free'::plan;
```

**Benefits**:
- Future INSERTs can omit `plan` and still get the default
- Resolves ambiguity in Alembic history
- Makes schema more robust

---

## 📋 Deployment Checklist

### Phase 1: Code Deployment ✅ DONE
- [x] Commit `backend/auth/router.py` + migration file
- [x] Push to `origin/main`
- [x] Verify no conflicts or rollback needed

### Phase 2: Production Execution (TO DO)

1. **Pull latest code** in prod environment
   ```bash
   cd /path/to/ai-shorts-generator
   git pull origin main
   ```

2. **Activate venv and run migrations**
   ```bash
   source .venv/bin/activate
   .venv/bin/alembic upgrade head
   ```
   
   Expected output:
   ```
   INFO  [alembic.runtime.migration] Running upgrade ... rev20260401_fix_plan
   ✓ Set plan column default to 'free' (Alembic merge head fix)
   ```

3. **Verify migration applied**
   ```bash
   .venv/bin/alembic current
   # Expected: rev20260401_fix_plan
   ```

4. **Check database state**
   ```bash
   psql "$DATABASE_URL" -c "SELECT column_default FROM information_schema.columns WHERE table_name='users' AND column_name='plan';"
   # Expected: 'free'::plan
   ```

5. **Restart FastAPI/Uvicorn**
   ```bash
   # Restart your Docker container or systemd service
   # Ensure new code from backend/auth/router.py is loaded
   ```

6. **Smoke test** (test manually or via curl)
   ```bash
   # Visit: https://your-prod.com/auth/google
   # Log in with a test Google account (new)
   # Verify redirect to /auth/callback?token=...
   # Verify no 502 error
   ```

---

## 📊 Files Changed

| File | Change | Type |
|------|--------|------|
| `backend/auth/router.py` | Add `plan='free'` to INSERT | Modification |
| `alembic/versions/20260401_fix_plan_not_null_and_merge_heads.py` | New migration | Creation |

---

## 🔍 Verification Commands

After deployment, run:

```bash
# 1. Check Alembic state
.venv/bin/alembic current
.venv/bin/alembic heads  # Should show exactly 1 head

# 2. Check DB column
psql "$DATABASE_URL" -c "\\d users"  # Verify plan column has default

# 3. Test user creation via Google OAuth (manual or automated test)
# Expected: new user row with plan='free'

# 4. Check recent logs
# Should show NO NotNullViolationError for Google OAuth
```

---

## ⚠️ Rollback Plan (if needed)

If something goes wrong, rollback:

```bash
# Downgrade migration
.venv/bin/alembic downgrade -1

# Revert code to previous commit
git revert --no-edit bc614e0
# or simply redeploy the previous commit

# Restart services
# Smoke test again
```

---

## 📝 Notes

- **No data loss**: This fix only adds defaults, does not modify existing rows
- **Backward compatible**: Existing users are unaffected
- **Safe migration**: Uses `ALTER TABLE ... ALTER COLUMN ... SET DEFAULT` (PostgreSQL standard)
- **Temporary vs. permanent**: The code hotfix is a quickfix; the migration is the permanent solution

---

## 🔗 Related Files

- `PROD_FIX_PLAN_20260401.md` — Detailed explanation and FAQ
- `DEPLOY_INSTRUCTIONS.sh` — Step-by-step deployment guide
- GitHub commit: `bc614e0`

---

**Questions?** Check the logs or reach out to the dev team.
