# Cookie authentication CSRF protection

Cookie-authenticated `POST`, `PUT`, `PATCH`, and `DELETE` requests require an
exact trusted `Origin`. CORS alone cannot prevent a cross-site request from
being sent, so the server validates Origin before the protected route executes.

The allowlist is shared with CORS and contains normalized explicit origins only.
Both boundaries compare a canonical hostname (case-insensitive) and remove the
default HTTP/HTTPS port (`:80`/`:443`), while reflecting the caller's accepted
Origin verbatim in the CORS response. Exactly one `Origin` header is required;
duplicates, missing, `null`, malformed, credentialed, path-bearing, wildcard
and look-alike origins are rejected. No Referer fallback is used.

Configured hostnames must be valid DNS names or IP addresses. Production rejects
localhost, `*.localhost`, every IPv4/IPv6 loopback spelling and IPv4-mapped
loopback addresses; `localhost.example.com` remains a normal public hostname.
Production without `FRONTEND_URL` starts with an empty allowlist.

The policy applies only after a valid opaque cookie session has authenticated
the request. On dual-auth routes, an empty, malformed, expired or duplicate
authentication cookie fails closed and never falls back to Bearer. Logout is
intentionally idempotent, but still requires Origin whenever the auth cookie is
present. JWT Bearer-only API clients remain compatible without Origin. If a
cookie and Bearer credential are both present, the cookie-first identity and
conflict rules run first; a valid cookie then requires Origin.

`POST /auth/session` is deliberately Bearer-only: it ignores any existing
cookie, requires a valid Bearer JWT, then replaces the browser cookie with a
new server-generated session. Because cross-site requests cannot supply that
Bearer credential, this conversion does not rely on Origin.

This protects web actions such as generation, Twitch jobs, Stripe checkout and
subscription cancellation. It also protects logout. Stripe webhooks and
anonymous email/password flows use their own credentials and are not
cookie-authenticated CSRF flows.

Clients should use browser XHR/fetch with credentials; a cookie mutation without
Origin is deliberately refused, including same-origin clients that omit it.
Reverse proxies must preserve a single Origin header and operators must configure
the exact frontend origin. A future review may add broader CSRF defences for
non-browser clients or deployments that require different trust boundaries.
