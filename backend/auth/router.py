"""
auth/router.py – Authentication routes:
  POST /auth/register     – email + password signup
  POST /auth/login        – email + password login  
  GET  /auth/me           – current user info
  GET  /auth/google       – redirect to Google OAuth
  GET  /auth/google/callback – Google OAuth callback
  POST /auth/logout       – (stateless JWT: just drop token on client)
  POST /auth/stripe/webhook – Stripe webhook for subscription updates
"""

import json
import logging
import os
from datetime import datetime, timezone

import bcrypt
import stripe
from authlib.integrations.httpx_client import AsyncOAuth2Client
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.auth.jwt import create_access_token
from backend.database import get_db
from backend.models.user import Plan, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

# ── Password hashing ────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ── Google OAuth config ─────────────────────────────────────────────────────
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# ── Stripe config ───────────────────────────────────────────────────────────
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRO_PRICE_ID = os.getenv("STRIPE_PRO_PRICE_ID", "")


# ── Schemas ──────────────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str | None
    avatar_url: str | None
    plan: str
    generations_this_month: int
    free_generations_left: int
    can_generate: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── Register ─────────────────────────────────────────────────────────────────
@router.post("/register", response_model=dict)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        is_verified=True,  # skip email verification for now
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id, user.email)
    logger.info(f"New user registered: {user.email}")
    return {"access_token": token, "token_type": "bearer", "user": _user_dict(user)}


# ── Login ─────────────────────────────────────────────────────────────────────
@router.post("/login", response_model=dict)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not user.hashed_password or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    token = create_access_token(user.id, user.email)
    return {"access_token": token, "token_type": "bearer", "user": _user_dict(user)}


# ── Me ────────────────────────────────────────────────────────────────────────
@router.get("/me", response_model=dict)
async def me(user: User = Depends(get_current_user)):
    return _user_dict(user)


# ── Google OAuth ──────────────────────────────────────────────────────────────
@router.get("/google")
async def google_login():
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=501, detail="Google OAuth not configured")

    client = AsyncOAuth2Client(
        client_id=GOOGLE_CLIENT_ID,
        redirect_uri=GOOGLE_REDIRECT_URI,
    )
    uri, _ = client.create_authorization_url(
        "https://accounts.google.com/o/oauth2/v2/auth",
        scope="openid email profile",
        access_type="offline",
    )
    return RedirectResponse(uri)


@router.get("/google/callback")
async def google_callback(code: str, db: AsyncSession = Depends(get_db)):
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=501, detail="Google OAuth not configured")

    # Exchange code for token
    async with AsyncOAuth2Client(
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        redirect_uri=GOOGLE_REDIRECT_URI,
    ) as client:
        token = await client.fetch_token(
            "https://oauth2.googleapis.com/token",
            code=code,
        )
        # Get user info
        resp = await client.get("https://www.googleapis.com/oauth2/v3/userinfo")
        info = resp.json()

    google_id = info.get("sub")
    email = info.get("email")
    full_name = info.get("name")
    avatar_url = info.get("picture")

    if not email or not google_id:
        raise HTTPException(status_code=400, detail="Could not retrieve Google account info")

    # Find or create user
    result = await db.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()

    if not user:
        # Check if email already registered (link accounts)
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user:
            user.google_id = google_id
            user.avatar_url = avatar_url or user.avatar_url
        else:
            user = User(
                email=email,
                google_id=google_id,
                full_name=full_name,
                avatar_url=avatar_url,
                is_verified=True,
            )
            db.add(user)

    await db.commit()
    await db.refresh(user)

    jwt_token = create_access_token(user.id, user.email)

    # Redirect to frontend with token
    return RedirectResponse(f"{FRONTEND_URL}/auth/callback?token={jwt_token}")


# ── Stripe: create checkout session ──────────────────────────────────────────
@router.post("/stripe/checkout")
async def create_checkout(user: User = Depends(get_current_user)):
    if not stripe.api_key or not STRIPE_PRO_PRICE_ID:
        raise HTTPException(status_code=501, detail="Stripe not configured")

    # Create or retrieve Stripe customer
    if not user.stripe_customer_id:
        customer = stripe.Customer.create(email=user.email, metadata={"user_id": user.id})
        # Note: update in DB done in webhook
        customer_id = customer.id
    else:
        customer_id = user.stripe_customer_id

    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{"price": STRIPE_PRO_PRICE_ID, "quantity": 1}],
        mode="subscription",
        success_url=f"{FRONTEND_URL}/dashboard?upgraded=true",
        cancel_url=f"{FRONTEND_URL}/pricing",
        metadata={"user_id": user.id},
    )
    return {"checkout_url": session.url}


# ── Stripe: webhook ───────────────────────────────────────────────────────────
@router.post("/stripe/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session.get("metadata", {}).get("user_id")
        customer_id = session.get("customer")
        subscription_id = session.get("subscription")

        if user_id:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user:
                user.plan = Plan.PRO
                user.stripe_customer_id = customer_id
                user.stripe_subscription_id = subscription_id
                await db.commit()
                logger.info(f"User {user.email} upgraded to Pro")

    elif event["type"] in ("customer.subscription.deleted", "customer.subscription.paused"):
        subscription = event["data"]["object"]
        customer_id = subscription.get("customer")

        result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
        user = result.scalar_one_or_none()
        if user:
            user.plan = Plan.FREE
            await db.commit()
            logger.info(f"User {user.email} downgraded to Free")

    return {"status": "ok"}


# ── Helper ────────────────────────────────────────────────────────────────────
def _user_dict(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "avatar_url": user.avatar_url,
        "plan": user.plan.value,
        "generations_this_month": user.generations_this_month,
        "free_generations_left": user.free_generations_left,
        "can_generate": user.can_generate,
        "created_at": user.created_at.isoformat(),
    }
