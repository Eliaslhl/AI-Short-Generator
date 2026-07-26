# Dual authentication boundary

PR3.2 accepts either the existing JWT Bearer credential or an opaque session
cookie. If the cookie is present, it is authoritative: an invalid, expired or
revoked cookie returns the normal authentication failure and never falls back to
a Bearer token. When both credentials are valid, they must identify the same
user or the request is rejected.

Password login, email confirmation, and Google OAuth create server-side sessions
directly and set an HttpOnly cookie only after their database transaction commits.
They never return a JWT to the web client. `POST /auth/session` remains a
temporary legacy endpoint for external Bearer clients: it requires a JWT Bearer
token, creates a server-side session and never returns the opaque token. Production uses
a `__Host-` cookie, which requires Secure, Path `/`, and no Domain. `POST
/auth/logout` revokes the cookie session and clears the cookie after a normal
commit; a database failure returns an error without falsely reporting logout.
Email-confirmation tokens are consumed conditionally in the same transaction as
the user confirmation and session creation, so concurrent callbacks have only
one successful winner.
Every cookie-authenticated mutating request, including logout, requires an
exact trusted `Origin`; Bearer-only API requests remain Origin-exempt. Logout
does not revoke existing stateless JWTs.

Duplicate authentication cookies are rejected with the generic authentication
failure rather than selecting one by header order. `POST /auth/session` remains
the exception: it is a Bearer-only conversion boundary, ignores any existing
cookie and replaces it after creating a fresh opaque session.

Google OAuth sets the opaque session cookie server-side and redirects the
frontend without a JWT query parameter. The web client uses that cookie through
credentialed requests, sends no Bearer header and does not persist browser JWTs.
PKCE and eventual removal of the transitional Bearer support remain deferred.
