# Frontend session authentication

The web client uses the backend's HttpOnly session cookie. JavaScript never
reads or writes the opaque session value, and it does not store JWTs in
`localStorage` or `sessionStorage`.

## Web flows

- Google OAuth: the backend validates the callback, creates the session and
  redirects to `/auth/callback` without query data. The page calls `GET
  /auth/me` with credentials to initialise the user.
- Password login and email confirmation create the opaque session and set its
  cookie only after their database transaction commits. The client then calls
  `/auth/me`; neither endpoint returns a JWT.
- Email confirmation consumes its one-time token atomically. Only the winning
  request can create a session and trigger the welcome email.
- The email confirmation link is cleaned from the visible URL before the API
  request. Registration requires confirmation and leaves the visitor signed out.

Axios is configured with `withCredentials: true`; no global Bearer interceptor
exists. Browser code sends no Bearer header. The backend continues to support
JWT Bearer authentication for API clients during the transition period.

## State and failures

Application startup always checks `/auth/me`. A `401` or `403` means signed
out; network and `5xx` failures remain visible as a retryable session-check
error instead of being treated as logout. Protected routes wait for this check.
Ordinary API `403` responses are left to their calling component and do not
force a logout.

The confirmation flow is an AuthContext operation: logout, a newer login, or
unmounting the confirmation page prevents an obsolete response from restoring
authentication or navigating to the dashboard.

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
Bearer-only API clients, including the temporary legacy `POST /auth/session`
endpoint, remain Origin-exempt for backwards compatibility. See [CSRF protection](CSRF_PROTECTION.md)
for the allowlist and deployment requirements. JWT rotation, advanced session
revocation, and removal of transitional backend Bearer support remain deferred.
