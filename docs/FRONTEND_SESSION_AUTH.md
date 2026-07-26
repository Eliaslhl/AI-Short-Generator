# Frontend session authentication

The web client uses the backend's HttpOnly session cookie. JavaScript never
reads or writes the opaque session value, and it does not store JWTs in
`localStorage` or `sessionStorage`.

## Web flows

- Google OAuth: the backend validates the callback, creates the session and
  redirects to `/auth/callback` without query data. The page calls `GET
  /auth/me` with credentials to initialise the user.
- Password login: `POST /auth/login` returns a JWT only in process memory. The
  client immediately sends it once to `POST /auth/session`, then calls
  `/auth/me`. It never persists the JWT.
- Email confirmation follows the same one-time in-memory exchange. The email
  confirmation link is cleaned from the visible URL before the API request.
- Registration normally requires confirmation and leaves the visitor signed
  out. A legacy backend response containing a JWT uses the same exchange.

Axios is configured with `withCredentials: true`; no global Bearer interceptor
exists. A Bearer header is sent only for the explicit `/auth/session` exchange.
The backend continues to support JWT Bearer authentication for API clients and
the transition period.

## State and failures

Application startup always checks `/auth/me`. A `401` or `403` means signed
out; network and `5xx` failures remain visible as a retryable session-check
error instead of being treated as logout. Protected routes wait for this check.
Ordinary API `403` responses are left to their calling component and do not
force a logout.

Logout calls `POST /auth/logout`. On success, or an idempotent `401`/`403`, the
client clears its user state and the old `token`, `access_token`, and
`token_type` browser keys. On a server/network failure it retains local user
state and reports failure; JavaScript never attempts to delete the HttpOnly
cookie itself.

## CSRF boundary

Credentialed requests make cookie-authenticated mutating routes CSRF-relevant.
The backend requires an exact trusted `Origin` for every cookie-authenticated
`POST`, `PUT`, `PATCH`, or `DELETE`; the browser supplies this header for
cross-origin fetch/XHR requests. It rejects missing or duplicate Origin headers;
hostname case and default ports are canonicalized consistently with CORS.
Bearer-only API clients, including the one-time `POST /auth/session` conversion,
remain Origin-exempt for backwards compatibility. See [CSRF protection](CSRF_PROTECTION.md)
for the allowlist and deployment requirements. JWT rotation, advanced session
revocation, and removal of transitional backend Bearer support remain deferred.
