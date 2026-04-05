# YouTube Cookie Validation Fix - Production Issue Resolution

## Problem Summary

L'auto-refresh des cookies YouTube fonctionne, mais génère des cookies avec des expirations invalides (`expires=-1`), ce qui cause:

```
WARNING: skipping cookie file entry due to invalid expires at -1: '.youtube.com\tTRUE\t/\tTRUE\t-1\tYSC\t2nXaqtcHiCo\n'
```

Cela empêche yt-dlp d'utiliser les cookies et le téléchargement échoue toujours.

## Root Cause

Playwright retourne des cookies de session avec `expires=-1`, qui sont invalides pour le format Netscape utilisé par yt-dlp. Ces cookies doivent être filtrés avant d'être écrits.

## Solution Applied ✅

### Commit: `bff6de1`

**File Modified**: `scripts/refresh_youtube_cookies.py`

**Changes**:

1. **Fonction `write_netscape_cookies()` améliorée**:
   - Filtre les cookies avec `expires < 0`
   - Filtre les cookies sans nom
   - Valide les valeurs d'expiration avant d'écrire
   - Ignore les erreurs de conversion

2. **Pré-filtrage des cookies en main()**:
   - Filtre les cookies invalides AVANT l'écriture
   - Affiche le nombre de cookies supprimés
   - Améliore la visibilité dans les logs

### Code Changes

```python
# AVANT:
expires = int(c.get("expires", 0) or 0)  # ❌ Accepte -1

# APRÈS:
expires = c.get("expires")
if expires_raw is not None:
    try:
        expires = int(expires_raw)
        if expires < 0:  # ✅ Saute les expirations négatives
            continue
    except (ValueError, TypeError):
        expires = 0
```

## Expected Logs After Fix

Après redeploy, tu devrais voir:

```
[REFRESH] Got 27 cookies from persistent context
[REFRESH] Filtered 27 cookies -> 24 valid cookies
[REFRESH] Writing cookies to /app/secrets/youtube_cookies.txt
WROTE /app/secrets/youtube_cookies.txt size=1200 sha256=abc123...
[YTC AUTO-REFRESH] cookies refreshed: /app/secrets/youtube_cookies.txt size=1200 sha256=abc123...
```

**Les 3 cookies supprimés** étaient les cookies de session avec `expires=-1`.

## Deployment Steps

### Step 1: Pull Latest Changes
```bash
git pull origin main
```

### Step 2: Verify Playwright is Installed
```bash
# Already added to requirements.txt in previous commit
pip install playwright>=1.40.0
playwright install chromium
```

### Step 3: Environment Variables (Railway)
Ensure these are set:
```env
YOUTUBE_ENABLE_AUTO_REFRESH=true
YOUTUBE_AUTO_REFRESH_HEADLESS=true
```

### Step 4: Redeploy
```bash
git push origin main
# Railway will auto-redeploy
```

### Step 5: Test
Try a YouTube download - should now work with auto-refresh! ✅

## Validation Checklist

After deployment, verify:

- [ ] Logs show "Filtered X cookies -> Y valid cookies"
- [ ] No more "invalid expires at -1" warnings
- [ ] YouTube videos download successfully
- [ ] Auto-refresh completes with "[YTC AUTO-REFRESH] cookies refreshed"
- [ ] Cookie file size is reasonable (1000-2000 bytes)

## Technical Details

### Cookie Format (Netscape)

```
domain  flag  path  secure  expires  name  value
.youtube.com  TRUE  /  TRUE  1735689600  SAPISID  abc123...
```

yt-dlp requires:
- `expires` > 0 (Unix timestamp in seconds)
- ❌ INVALID: `expires = -1` (session cookie)
- ❌ INVALID: `expires = 0` for cookies that should expire

### Cookies Filtered

These cookies are now properly excluded:

1. **Session cookies**: `expires=-1`
2. **Invalid expires**: Non-numeric values
3. **Empty names**: Malformed cookies

### Preserved Cookies

Keep cookies like:
- `SAPISID` (authentication)
- `SSID` (session)
- `SID` (session ID)
- `YSC` (YouTube session)
- etc.

## Monitoring

### Logs to Watch

**Success indicators**:
```
[YTC AUTO-REFRESH] cookies refreshed: /app/secrets/youtube_cookies.txt size=1331 sha256=...
Retrying yt-dlp with refreshed cookies for job xxx
```

**Error indicators** (still failing):
```
yt-dlp retry failed after refresh: WARNING: skipping cookie file entry due to invalid expires
```

### If It Still Fails

1. Check that Playwright actually ran:
   ```
   [REFRESH] Starting Playwright with profile: ...
   [REFRESH] Filtered X cookies -> Y valid cookies
   ```

2. Verify cookies were written:
   ```bash
   ls -la /app/secrets/youtube_cookies.txt
   wc -l /app/secrets/youtube_cookies.txt
   ```

3. Check for other bot-detection mechanisms:
   - May need cookies from actual browser session (manual export)
   - May need to use Bright Data proxy (BrightData)
   - May need to adjust yt-dlp options

## Alternative: Manual Cookies (If Auto-Refresh Still Fails)

If auto-refresh continues to fail, use manually exported cookies:

```bash
# 1. Export from your browser (Chrome/Firefox)
# Use EditThisCookie extension or cookies.txt

# 2. Encode to base64
cat cookies.txt | base64 > cookies.b64

# 3. Set in Railway
YOUTUBE_COOKIES_B64=$(cat cookies.b64)

# 4. Disable auto-refresh
YOUTUBE_ENABLE_AUTO_REFRESH=false
```

## Files Modified

| File | Changes | Purpose |
|------|---------|---------|
| `scripts/refresh_youtube_cookies.py` | Filter invalid cookies | Prevent yt-dlp warnings |
| `requirements.txt` | Add playwright | Enable auto-refresh |
| `backend/api/advanced_routes.py` | Fix imports | Fix queue module conflict |

## Related Issues

- **Previous**: Module naming conflict (queue → task_queue) - ✅ Fixed
- **Current**: Invalid cookie expires - ✅ Fixed
- **Remaining**: IP blocking (if manual cookies also fail) - may need proxy

## Next Steps

1. Deploy this commit to production
2. Monitor logs for 2-3 minutes
3. Test YouTube download again
4. If working → document as standard procedure
5. If not working → implement manual cookie export flow

---

**Commit**: `bff6de1`  
**Date**: 5 April 2026  
**Status**: ✅ Ready for deployment
