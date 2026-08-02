"""Shared slowapi Limiter instance.

Kept in its own module (not backend/main.py) so route modules such as
backend.auth.router can import it and decorate individual endpoints with
@limiter.limit(...) without a circular import — main.py imports those
routers to register them.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
