# Opaque application sessions

`AuthSession` is the server-side foundation for future web sessions. This PR
does not change Google OAuth, JWT Bearer authentication, HTTP cookies, or any
frontend behavior.

The database stores only an HMAC-SHA-256 digest of each opaque session token.
The raw token is generated with `secrets.token_urlsafe(32)`, returned only when
the session is created, is masked by `repr()` and `str()`, and is never
recoverable from the database. A separate `SESSION_HASH_KEY` scopes this
digesting key away from `SECRET_KEY`; production requires a unique value of at
least 32 characters. Rotating this key invalidates every active session, which
can serve as an emergency global revocation mechanism.

Sessions default to 30 days and can be expired, revoked individually, revoked
per user, touched, or deleted in bounded cleanup batches. The future HTTP layer
should limit touches to avoid write amplification. This PR intentionally stores
no device or IP metadata: their privacy and retention formats are not defined.
Expired sessions are currently deleted without audit retention; that policy may
change before commercial launch. Future PRs will use this service behind an
HttpOnly cookie for web traffic. JWT Bearer tokens and the existing OAuth flow
remain unchanged until that migration is explicitly implemented.
