# Security Headers Implementation

## Overview

This implementation adds HTTP Security Headers to all API responses to protect against common web vulnerabilities. These headers are applied globally via a Starlette middleware.

## Headers Implemented

### 1. **X-Content-Type-Options: nosniff**
- **Purpose:** Prevents MIME type sniffing attacks
- **Effect:** Browser must respect the Content-Type header and not guess
- **Protection:** Against IE/Edge from executing scripts disguised as images/CSS
- **Browser Support:** All modern browsers

### 2. **X-XSS-Protection: 1; mode=block**
- **Purpose:** Enable XSS protection in older browsers
- **Effect:** Browser blocks page if XSS attack detected
- **Note:** Deprecated in modern browsers (use CSP instead)
- **Browser Support:** Internet Explorer, older versions

### 3. **X-Frame-Options: SAMEORIGIN**
- **Purpose:** Prevents clickjacking attacks
- **Effect:** Page can only be framed by pages from same origin
- **Options:**
  - `DENY` - Cannot be framed at all
  - `SAMEORIGIN` - Only same-origin frames (used here)
  - `ALLOW-FROM uri` - Specific origin only
- **Protection:** Against iFrame-based clickjacking

### 4. **Referrer-Policy: strict-origin-when-cross-origin**
- **Purpose:** Controls how much referrer information is shared
- **Effect:** 
  - Same-origin requests: Full URL sent
  - Cross-origin HTTPS: Origin only
  - Cross-origin HTTP: Nothing sent
- **Options:**
  - `no-referrer` - Never send
  - `same-origin` - Only for same-origin
  - `strict-origin-when-cross-origin` - Used here (good balance)
  - `origin` - Always send origin only
- **Protection:** Against leaked URL information

### 5. **Permissions-Policy** (formerly Feature-Policy)
- **Purpose:** Disable unused browser features
- **Disabled Features:**
  - `accelerometer` - Acceleration sensor
  - `ambient-light-sensor` - Light sensor
  - `camera` - Webcam access
  - `geolocation` - GPS location
  - `gyroscope` - Rotation sensor
  - `magnetometer` - Compass
  - `microphone` - Audio input
  - `payment` - Payment APIs
  - `usb` - USB access
- **Effect:** Even if malicious script runs, can't use these APIs
- **Protection:** Against unauthorized feature access

### 6. **Content-Security-Policy (CSP)**
- **Purpose:** Prevent execution of unauthorized code
- **Directives Used:**
  - `default-src 'self'` - Only same-origin resources by default
  - `script-src 'self' 'unsafe-inline' 'unsafe-eval'` - Scripts from self + inline (for Vite/React)
  - `style-src 'self' 'unsafe-inline'` - Styles from self + inline (Tailwind)
  - `img-src 'self' data: https:` - Images from self, data URIs, HTTPS
  - `font-src 'self' data:` - Fonts from self and data URIs
  - `connect-src 'self' https:` - XHR/WebSocket to self and HTTPS only
  - `frame-ancestors 'self'` - Equivalent to X-Frame-Options
  - `base-uri 'self'` - Base tag can't change document base
  - `form-action 'self'` - Forms submit to same-origin only
  - `upgrade-insecure-requests` - Upgrade HTTP to HTTPS
- **Protection:** Against XSS, injection attacks, malicious code execution

### 7. **Strict-Transport-Security (HSTS)**
- **Purpose:** Force HTTPS connections
- **Configuration:**
  - `max-age=31536000` - 1 year (31,536,000 seconds)
  - `includeSubDomains` - Apply to all subdomains
  - `preload` - Include in HSTS preload list
- **Effect:**
  - First visit: User sees header, future visits use HTTPS automatically
  - Preload: HTTPS enforced even for first visit (via browser preload list)
- **Protection:** Against man-in-the-middle (MITM) attacks via HTTP downgrade

## How It Works

### Middleware Implementation
```python
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # Add all security headers to response
        response.headers["X-Content-Type-Options"] = "nosniff"
        # ... more headers ...
        return response
```

### Applied To
- All API routes (`/api/*`)
- All auth routes (`/auth/*`)
- All static files
- Health checks
- All responses automatically

## Testing Security Headers

### Using curl
```bash
curl -I https://your-api.com/health
```

Expected output includes:
```
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block
X-Frame-Options: SAMEORIGIN
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: accelerometer=(), camera=(), ...
Content-Security-Policy: default-src 'self'; ...
Strict-Transport-Security: max-age=31536000; ...
```

### Online Tools
- **SecurityHeaders.com** - Scan and grade security headers
- **Mozilla Observatory** - Comprehensive security scan
- **OWASP ZAP** - Automated security testing

### Browser DevTools
1. Open browser DevTools (F12)
2. Go to Network tab
3. Make a request to the API
4. Click on response
5. Check "Response Headers" section

## Security Grade Impact

These headers typically improve security rating to **A** or **A+**:

| Header | Rating Impact |
|--------|---------------|
| Content-Security-Policy | Major |
| Strict-Transport-Security | Major |
| X-Frame-Options | Major |
| X-Content-Type-Options | Medium |
| Referrer-Policy | Medium |
| Permissions-Policy | Medium |
| X-XSS-Protection | Minor |

## Compatibility

| Header | Modern Browsers | IE 11 | Mobile |
|--------|-----------------|-------|--------|
| X-Content-Type-Options | ✅ | ✅ | ✅ |
| X-XSS-Protection | ✅ | ✅ | ✅ |
| X-Frame-Options | ✅ | ✅ | ✅ |
| Referrer-Policy | ✅ | ❌ | ✅ |
| Permissions-Policy | ✅ | ❌ | ✅ |
| CSP | ✅ | Limited | ✅ |
| HSTS | ✅ | ✅ | ✅ |

## Development Mode

### Disabling Strict CSP (if needed)
If you encounter CSP violations during development:

1. Check browser console for CSP violations
2. Identify resource causing issue
3. Update CSP directive in `SecurityHeadersMiddleware`

Example CSP violation:
```
Refused to load script from 'https://cdn.example.com/...'
Reason: Content Security Policy violation
```

Solution: Add to `script-src`:
```python
"script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.example.com; "
```

## Production Deployment

### HTTPS Requirement
HSTS requires HTTPS. Ensure:
1. SSL certificate installed
2. All traffic redirected to HTTPS
3. Certificate is valid and not expired

### HSTS Preload
1. Visit: https://hstspreload.org/
2. Enter your domain
3. Follow instructions to submit
4. Domain added to browser preload list (takes ~3 months)

### CSP Report-Only Mode
For testing without blocking resources:
```python
response.headers["Content-Security-Policy-Report-Only"] = "..."
```

## Future Enhancements

1. **Dynamic CSP Nonce** - Use nonce for inline scripts instead of 'unsafe-inline'
2. **Report Violations** - Send CSP violations to monitoring service
3. **Subresource Integrity (SRI)** - Verify external script integrity
4. **X-Permitted-Cross-Domain-Policies** - Control Flash/PDF cross-domain policies
5. **Cross-Origin-Embedder-Policy (COEP)** - Enable crossOriginIsolated features
6. **Cross-Origin-Opener-Policy (COOP)** - Isolate from cross-origin popups

## Troubleshooting

### CSP Blocks Images/Scripts
**Symptom:** Resources load in dev but blocked in production

**Solution:**
- Check browser console for CSP violations
- Add source to appropriate CSP directive
- Test with `Content-Security-Policy-Report-Only` first

### HSTS Breaks Development
**Symptom:** Can't access HTTP version after visiting HTTPS

**Solution:**
- Clear browser HSTS cache: `chrome://net-internals/#hsts`
- Use different domain for dev (http://localhost:8000)
- Disable HSTS on localhost in browser

### Referrer Not Sent
**Symptom:** Server logs show no referrer for cross-origin requests

**Expected:** This is by design with `strict-origin-when-cross-origin`

**To Allow:** Change to `same-origin` or `origin`

## Files Modified

| File | Changes |
|------|---------|
| `backend/main.py` | Added `SecurityHeadersMiddleware` class + middleware registration |

## References

- [OWASP Security Headers](https://owasp.org/www-project-secure-headers/)
- [Mozilla HTTP Observatory](https://observatory.mozilla.org/)
- [MDN: HTTP Headers Security](https://developer.mozilla.org/en-US/docs/Glossary/HTTP_header)
- [SecurityHeaders.com](https://securityheaders.com)
- [HSTS Preload](https://hstspreload.org/)

## Summary

These security headers provide defense-in-depth protection against:
- ✅ XSS attacks
- ✅ MIME sniffing
- ✅ Clickjacking
- ✅ Code injection
- ✅ MITM attacks
- ✅ Unauthorized feature access
- ✅ Information leakage

**Result:** Significantly improved security posture and better score on security assessment tools.
