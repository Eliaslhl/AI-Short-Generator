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
Every cookie-authenticated mutating request, including logout, requires an
exact trusted `Origin`; Bearer-only API requests remain Origin-exempt. Logout
does not revoke existing stateless JWTs.

Duplicate authentication cookies are rejected with the generic authentication
failure rather than selecting one by header order. `POST /auth/session` remains
the exception: it is a Bearer-only conversion boundary, ignores any existing
cookie and replaces it after creating a fresh opaque session.

Google OAuth now sets the opaque session cookie server-side and redirects the
frontend without a JWT query parameter. The web client uses that cookie through
credentialed requests and does not persist browser JWTs. PKCE and eventual
removal of the transitional Bearer support remain deferred.
