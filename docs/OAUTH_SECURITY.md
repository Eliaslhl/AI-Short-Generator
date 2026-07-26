# OAuth transaction security

The former Google callback created a JWT and redirected with it in the URL.
PR3.3 replaces this with a short-lived, one-time server-side OAuth transaction.
Only a keyed hash of the random state is persisted; no Google access token,
refresh token, JWT, or opaque session token is stored in the transaction.

The callback atomically consumes state before exchanging the Google code. After
the user is found or created, it creates an `AuthSession`, commits, sets the
HttpOnly session cookie, and redirects to `/auth/callback` without query data.

PKCE is intentionally not added: this is a confidential server-side client that
keeps the authorization-code exchange and client secret on the backend. PR3.4
will migrate the frontend away from callback JWT/localStorage assumptions.
