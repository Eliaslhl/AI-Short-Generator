# Dual authentication boundary

PR3.2 accepts either the existing JWT Bearer credential or an opaque session
cookie. If the cookie is present, it is authoritative: an invalid, expired or
revoked cookie returns the normal authentication failure and never falls back to
a Bearer token. When both credentials are valid, they must identify the same
user or the request is rejected.

`POST /auth/session` requires a JWT Bearer token, creates a server-side session
and sets an HttpOnly cookie. It never returns the opaque token. Production uses
a `__Host-` cookie, which requires Secure, Path `/`, and no Domain. `POST
/auth/logout` revokes the cookie session and clears the cookie after a normal
commit; a database failure returns an error without falsely reporting logout.
It checks an explicit CORS origin when a cookie is supplied. Logout does not
revoke existing stateless JWTs.

Google OAuth still places a JWT in its callback URL, the frontend still uses
localStorage, and PKCE/state plus the frontend cookie migration remain deferred
to PR3.3 and PR3.4.
