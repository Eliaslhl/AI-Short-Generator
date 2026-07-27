"""
auth/router.py – Authentication routes:
  POST /auth/register           – email + password signup
  POST /auth/login              – email + password login
  GET  /auth/me                 – current user info
  GET  /auth/google             – redirect to Google OAuth
  GET  /auth/google/callback    – Google OAuth callback
  POST /auth/forgot-password    – send password reset email
  POST /auth/reset-password     – set new password via token
  POST /auth/stripe/checkout    – create Stripe checkout session
  POST /auth/stripe/webhook     – Stripe webhook for subscription updates
"""

import asyncio
import logging
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import stripe
from authlib.integrations.httpx_client import AsyncOAuth2Client
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.auth.session_cookie import (
    delete_session_cookie,
    read_session_cookie,
    require_allowed_origin,
    session_cookie_present,
    reject_ambiguous_session_cookie,
    set_session_cookie,
)
from backend.database import get_db
from backend.models.user import Plan, PasswordResetToken, User, EmailConfirmationToken
from backend.services.email_service import send_reset_email, send_welcome_email, send_confirmation_email
from backend.services.session_service import session_service
from backend.services.oauth_transaction_service import (
    consume_oauth_transaction,
    create_oauth_transaction,
)

if os.getenv("APP_ENVIRONMENT") in {"development", "test"}:
    load_dotenv()

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
GOOGLE_REDIRECT_URI = os.getenv(
    "GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback"
)
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# ── Stripe config ───────────────────────────────────────────────────────────
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

# Map price_id → Plan (covers monthly + yearly for all 3 plans)
PRICE_TO_PLAN: dict[str, Plan] = {
    os.getenv("STRIPE_STANDARD_MONTHLY_PRICE_ID", ""): Plan.STANDARD,
    os.getenv("STRIPE_STANDARD_YEARLY_PRICE_ID", ""): Plan.STANDARD,
    os.getenv("STRIPE_PRO_MONTHLY_PRICE_ID", ""): Plan.PRO,
    os.getenv("STRIPE_PRO_YEARLY_PRICE_ID", ""): Plan.PRO,
    os.getenv("STRIPE_PROPLUS_MONTHLY_PRICE_ID", ""): Plan.PROPLUS,
    os.getenv("STRIPE_PROPLUS_YEARLY_PRICE_ID", ""): Plan.PROPLUS,
}
# Remove empty-key entries (unset env vars)
PRICE_TO_PLAN = {k: v for k, v in PRICE_TO_PLAN.items() if k}

# Build a mapping price_id -> (platform, Plan) for platform-specific price IDs
PRICE_TO_PLATFORM_PLAN: dict[str, tuple[str, Plan]] = {}
for prefix, platform in (
    ("STRIPE_YOUTUBE", "youtube"),
    ("STRIPE_TWITCH", "twitch"),
    ("STRIPE_COMBO", "combo"),
):
    for plan_name in ("STANDARD", "PRO", "PROPLUS"):
        for period in ("MONTHLY", "YEARLY"):
            env_key = f"{prefix}_{plan_name}_{period}_PRICE_ID"
            pid = os.getenv(env_key, "")
            if pid:
                try:
                    PRICE_TO_PLATFORM_PLAN[pid] = (platform, Plan[plan_name])
                except Exception:
                    # ignore unknown plan names
                    pass


# ── Schemas ──────────────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ConfirmEmailRequest(BaseModel):
    token: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str | None
    avatar_url: str | None
    plan: str
    plan_youtube: str | None = None
    plan_twitch: str | None = None
    subscription_type: str | None = None
    generations_this_month: int
    free_generations_left: int
    can_generate: bool
    youtube_limit: int | None = None
    twitch_limit: int | None = None
    youtube_generations_left: int | None = None
    twitch_generations_left: int | None = None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Helper: Send email in background (catches errors silently) ────────────────
async def send_confirmation_email_safe(email: str, token: str) -> None:
    """Send confirmation email. Silently catch errors (for background tasks)."""
    try:
        await send_confirmation_email(email, token)
    except Exception:
        logger.error("Failed to send confirmation email")


# ── Register ─────────────────────────────────────────────────────────────────
@router.post("/register", response_model=dict)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    if len(body.password) < 8:
        raise HTTPException(
            status_code=400, detail="Password must be at least 8 characters"
        )

    # Create user with is_verified=False (requires email confirmation)
    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        is_verified=False,  # Requires email confirmation before account is active
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info("New user registered: user_id=%s", user.id)

    # Generate confirmation token
    confirmation_token_obj = EmailConfirmationToken.create_token(user.id, user.email)
    db.add(confirmation_token_obj)
    await db.commit()

    # Send confirmation email (non-blocking with background task)
    asyncio.create_task(
        send_confirmation_email_safe(user.email, confirmation_token_obj.token)
    )

    return {
        "message": "Registration successful! Please check your email to confirm your account.",
        "email": user.email,
        "requires_email_confirmation": True,
    }


# ── Login ─────────────────────────────────────────────────────────────────────
@router.post("/login", response_model=dict)
async def login(
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    try:
        # SQLite releases a top-level savepoint on exit. Start a real write
        # transaction so the session service's retry savepoint remains enclosed
        # by this route's commit/rollback boundary.
        if db.bind is not None and db.bind.dialect.name == "sqlite":
            await db.execute(text("BEGIN IMMEDIATE"))

        result = await db.execute(select(User).where(User.email == body.email))
        user = result.scalar_one_or_none()

        if (
            not user
            or not user.hashed_password
            or not verify_password(body.password, user.hashed_password)
        ):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        if not user.is_active:
            raise HTTPException(status_code=403, detail="Account disabled")

        if not user.is_verified:
            raise HTTPException(status_code=403, detail="Email not confirmed. Please check your inbox and confirm your email address.")

        try:
            created = await session_service.create_session(db, user.id)
            await db.commit()
        except Exception:
            await db.rollback()
            raise
        set_session_cookie(response, created.raw_token)
        return {"user": _user_dict(user)}
    except HTTPException:
        # re-raise known HTTP exceptions unchanged
        raise
    except Exception:
        logger.error("Unexpected error during login")
        raise HTTPException(status_code=500, detail="Unable to log in. Please try again.")


# ── Me ────────────────────────────────────────────────────────────────────────
@router.get("/me", response_model=dict)
async def me(user: User = Depends(get_current_user)):
    return _user_dict(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, db: AsyncSession = Depends(get_db)):
    """Idempotently revoke the opaque cookie session."""
    reject_ambiguous_session_cookie(request)
    has_cookie = session_cookie_present(request)
    if has_cookie:
        require_allowed_origin(request)

    token = read_session_cookie(request)
    if token is not None:
        try:
            await session_service.revoke_session_by_token(db, token)
            await db.commit()
        except Exception:
            await db.rollback()
            raise

    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    delete_session_cookie(response)
    return response


# ── Confirm Email ─────────────────────────────────────────────────────────────
@router.post("/confirm-email", response_model=dict)
async def confirm_email(
    body: ConfirmEmailRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Verify email confirmation token and activate user account."""
    token = body.token
    now = datetime.now(timezone.utc)

    # Consume the one-time capability in the database, not in application
    # memory. A concurrent request can never receive the same user_id here.
    result = await db.execute(
        update(EmailConfirmationToken)
        .where(
            EmailConfirmationToken.token == token,
            EmailConfirmationToken.used.is_(False),
            EmailConfirmationToken.expires_at > now,
        )
        .values(used=True)
        .returning(EmailConfirmationToken.user_id)
    )
    user_id = result.scalar_one_or_none()
    if user_id is None:
        # Preserve the historical client errors without ever allowing this
        # fallback read to create a session.
        result = await db.execute(
            select(EmailConfirmationToken).where(EmailConfirmationToken.token == token)
        )
        email_token = result.scalar_one_or_none()
        if not email_token:
            raise HTTPException(status_code=400, detail="Invalid confirmation token")
        if email_token.used:
            raise HTTPException(status_code=400, detail="Confirmation token already used")
        raise HTTPException(status_code=400, detail="Confirmation token has expired")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        await db.rollback()
        raise HTTPException(status_code=404, detail="User not found")

    user.is_verified = True
    db.add(user)
    try:
        created = await session_service.create_session(db, user.id)
        await db.commit()
    except Exception:
        await db.rollback()
        logger.error("Unexpected error during email confirmation")
        raise HTTPException(
            status_code=500,
            detail="Unable to confirm email. Please try again.",
        )
    await db.refresh(user)
    set_session_cookie(response, created.raw_token)
    
    logger.info("Email confirmed: user_id=%s", user.id)
    
    # Send welcome email now that they're verified
    try:
        await send_welcome_email(user.email, user.full_name or "")
    except Exception:
        logger.error("Failed to send welcome email")
    
    return {
        "user": _user_dict(user),
        "message": "Email confirmed! Your account is now active."
    }


# ── Google OAuth ──────────────────────────────────────────────────────────────
@router.get("/google")
async def google_login(db: AsyncSession = Depends(get_db)):
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=501, detail="Google OAuth not configured")

    client = AsyncOAuth2Client(
        client_id=GOOGLE_CLIENT_ID,
        redirect_uri=GOOGLE_REDIRECT_URI,
    )
    state = await create_oauth_transaction(
        db, provider="google", redirect_uri=GOOGLE_REDIRECT_URI
    )
    await db.commit()
    uri, _ = client.create_authorization_url(
        "https://accounts.google.com/o/oauth2/v2/auth",
        scope="openid email profile",
        access_type="offline",
        state=state,
    )
    return RedirectResponse(uri)


@router.get("/google/callback")
async def google_callback(code: str, state: str | None = None, db: AsyncSession = Depends(get_db)):
    """Exchange Google code, find-or-create user using raw SQL to avoid selecting missing columns.

    This is a defensive hotfix: if the DB schema is partially migrated and some columns
    (like youtube_limit_override) are missing, ORM queries that select all columns will
    raise and cause a 500. Using minimal raw SQL here avoids referencing those columns.
    """
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=501, detail="Google OAuth not configured")

    if not await consume_oauth_transaction(
        db, state=state, provider="google", redirect_uri=GOOGLE_REDIRECT_URI
    ):
        raise HTTPException(status_code=400, detail="Invalid OAuth transaction")
    await db.commit()

    # Exchange code for token and fetch Google user info
    async with AsyncOAuth2Client(
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        redirect_uri=GOOGLE_REDIRECT_URI,
    ) as client:
        await client.fetch_token("https://oauth2.googleapis.com/token", code=code)
        resp = await client.get("https://www.googleapis.com/oauth2/v3/userinfo")
        info = resp.json()

    google_id = info.get("sub")
    email = info.get("email")
    full_name = info.get("name")
    avatar_url = info.get("picture")

    if not email or not google_id:
        raise HTTPException(status_code=400, detail="Could not retrieve Google account info")

    # Use raw SQL to find existing users (avoid ORM selecting all columns during schema drift)
    # but always use ORM for creating new users (handles defaults properly)
    user_id = None

    try:
        # 1) try find by google_id
        r = await db.execute(
            text("SELECT id, email, full_name, avatar_url, is_active FROM users WHERE google_id = :gid"),
            {"gid": google_id},
        )
        row = r.first()
        if row:
            user_id = row[0]
        else:
            # 2) try find by email (link account)
            r = await db.execute(text("SELECT id FROM users WHERE email = :email"), {"email": email})
            row = r.first()
            if row:
                user_id = row[0]
                # update google_id and avatar_url if needed
                await db.execute(
                    text(
                        "UPDATE users SET google_id = :gid, avatar_url = COALESCE(:avatar, avatar) WHERE id = :id"
                    ),
                    {"gid": google_id, "avatar": avatar_url, "id": user_id},
                )
                await db.commit()
            else:
                # 3) create new user via ORM (handles plan default properly)
                new_id = str(uuid.uuid4())
                user = User(
                    id=new_id,
                    email=email,
                    google_id=google_id,
                    full_name=full_name,
                    avatar_url=avatar_url,
                    is_verified=True,
                    is_active=True,
                )
                db.add(user)
                await db.commit()
                user_id = new_id
    except Exception as exc:
        # Log the low-level DB error and attempt an ORM fallback
        logger.exception("Raw SQL path failed in google_callback, falling back to ORM: %s", exc)
        
        # Rollback the corrupted transaction before retrying
        await db.rollback()

        try:
            # ORM fallback: safer once schema is in expected state
            result = await db.execute(select(User).where(User.google_id == google_id))
            user = result.scalar_one_or_none()
            if user:
                user_id = user.id
            else:
                result = await db.execute(select(User).where(User.email == email))
                user = result.scalar_one_or_none()
                if user:
                    user_id = user.id
                    # update google_id and avatar_url
                    user.google_id = google_id
                    if avatar_url:
                        user.avatar_url = avatar_url
                    db.add(user)
                    await db.commit()
                else:
                    # create new user via ORM
                    new_id = str(uuid.uuid4())
                    user = User(
                        id=new_id,
                        email=email,
                        google_id=google_id,
                        full_name=full_name,
                        avatar_url=avatar_url,
                        is_verified=True,
                        is_active=True,
                    )
                    db.add(user)
                    await db.commit()
                    await db.refresh(user)
                    user_id = user.id
        except Exception:
            logger.exception("ORM fallback also failed in google_callback")
            raise HTTPException(status_code=502, detail="Database error during authentication")

    if not user_id:
        raise HTTPException(status_code=500, detail="Could not create or find user")

    created_session = await session_service.create_session(db, user_id)
    await db.commit()
    response = RedirectResponse(f"{FRONTEND_URL}/auth/callback", status_code=302)
    set_session_cookie(response, created_session.raw_token)
    return response


# ── Stripe: create checkout session ──────────────────────────────────────────
class CheckoutRequest(BaseModel):
    price_id: str


@router.post("/stripe/checkout")
async def create_checkout(
    body: CheckoutRequest, user: User = Depends(get_current_user)
):
    if not stripe.api_key:
        raise HTTPException(status_code=501, detail="Stripe not configured")
    # Validate the price_id is one of our known prices (generic or platform-specific)
    if body.price_id not in PRICE_TO_PLAN and body.price_id not in PRICE_TO_PLATFORM_PLAN:
        raise HTTPException(status_code=400, detail="Invalid price ID")

    # Create or retrieve Stripe customer
    if not user.stripe_customer_id:
        customer = stripe.Customer.create(
            email=user.email, metadata={"user_id": user.id}
        )
        customer_id = customer.id
    else:
        customer_id = user.stripe_customer_id
    # Create checkout using a predefined price id
    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{"price": body.price_id, "quantity": 1}],
        mode="subscription",
        success_url=f"{FRONTEND_URL}/dashboard?upgraded=true",
        cancel_url=f"{FRONTEND_URL}/#pricing",
        metadata={"user_id": user.id},
    )
    return {"checkout_url": session.url}


# ── Stripe: cancel subscription ───────────────────────────────────────────────
@router.post("/stripe/cancel")
async def cancel_subscription(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    if not stripe.api_key:
        raise HTTPException(status_code=501, detail="Stripe not configured")

    if user.plan == Plan.FREE or not user.stripe_subscription_id:
        raise HTTPException(status_code=400, detail="No active subscription to cancel")

    try:
        # Cancel at period end — user keeps access until billing cycle ends
        stripe.Subscription.modify(
            user.stripe_subscription_id,
            cancel_at_period_end=True,
        )
        logger.info(f"User {user.email} requested subscription cancellation")
        return {
            "message": "Your subscription will be cancelled at the end of the current billing period."
        }
    except Exception as e:
        logger.error(f"Stripe cancel error for {user.email}: {e}")
        raise HTTPException(
            status_code=502, detail="Could not cancel subscription. Please try again."
        )


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
                # Prefer explicit metadata (used for local TEST sessions). Otherwise
                # retrieve the subscription and map the Stripe price id to a
                # platform-specific plan. Then assign the plan to the correct
                # platform field and initialize monthly counters/reset dates.
                meta_plan = session.get("metadata", {}).get("plan")
                meta_platform = session.get("metadata", {}).get("platform")

                assigned_platform = None
                assigned_plan = None

                if meta_plan and meta_platform:
                    try:
                        assigned_plan = Plan[meta_plan]
                        assigned_platform = meta_platform
                    except Exception:
                        logger.warning(f"Unknown plan in session metadata: {meta_plan}")
                else:
                    if subscription_id:
                        try:
                            sub = stripe.Subscription.retrieve(subscription_id)
                            price_id = sub["items"]["data"][0]["price"]["id"]
                            # platform-agnostic fallback
                            assigned_plan = PRICE_TO_PLAN.get(price_id, None)
                            # platform-aware mapping
                            pp = PRICE_TO_PLATFORM_PLAN.get(price_id)
                            if pp:
                                assigned_platform, assigned_plan = pp
                        except Exception as e:
                            logger.warning(f"Could not retrieve subscription price: {e}")

                # Apply the assignment to the correct user fields
                now = datetime.now(timezone.utc)
                if assigned_plan and assigned_platform:
                    if assigned_platform == "youtube":
                        user.plan_youtube = assigned_plan
                        user.youtube_generations_month = 0
                        user.youtube_plan_reset_date = now
                        user.stripe_customer_id = customer_id
                        user.stripe_subscription_id = subscription_id
                    elif assigned_platform == "twitch":
                        user.plan_twitch = assigned_plan
                        user.twitch_generations_month = 0
                        user.twitch_plan_reset_date = now
                        user.stripe_customer_id = customer_id
                        user.stripe_subscription_id_twitch = subscription_id
                    elif assigned_platform == "combo":
                        # Combo applies to both platforms
                        user.plan_youtube = assigned_plan
                        user.plan_twitch = assigned_plan
                        user.youtube_generations_month = 0
                        user.youtube_plan_reset_date = now
                        user.twitch_generations_month = 0
                        user.twitch_plan_reset_date = now
                        user.stripe_customer_id = customer_id
                        user.stripe_subscription_id = subscription_id
                    # update subscription_type when available
                    if meta_platform:
                        user.subscription_type = meta_platform
                elif assigned_plan:
                    # legacy fallback: set global plan for compatibility
                    user.plan = assigned_plan
                    user.stripe_customer_id = customer_id
                    user.stripe_subscription_id = subscription_id

                await db.commit()
                logger.info(f"User {user.email} upgraded (platform={assigned_platform}) to {assigned_plan}")

    elif event["type"] in (
        "customer.subscription.deleted",
        "customer.subscription.paused",
    ):
        subscription = event["data"]["object"]
        customer_id = subscription.get("customer")

        result = await db.execute(
            select(User).where(User.stripe_customer_id == customer_id)
        )
        user = result.scalar_one_or_none()
        if user:
            user.plan = Plan.FREE
            await db.commit()
            logger.info(
                f"User {user.email} downgraded to Free (subscription cancelled)"
            )

    return {"status": "ok"}


# ── Resend Confirmation Email ─────────────────────────────────────────────────
class ResendConfirmationRequest(BaseModel):
    email: EmailStr


@router.post("/resend-confirmation-email")
async def resend_confirmation_email(
    body: ResendConfirmationRequest,
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Resend email confirmation link to user."""
    # Find the user
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    
    if not user:
        # Don't reveal if user exists (security best practice)
        return {
            "message": "If an account exists, a confirmation email will be sent.",
            "email": body.email
        }
    
    # If already verified, no need to resend
    if user.is_verified:
        return {
            "message": "Your email is already verified!",
            "email": body.email
        }
    
    # Create a new confirmation token (invalidating old ones)
    confirmation_token = secrets.token_urlsafe(48)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    
    # Mark old tokens as used
    result = await db.execute(
        select(EmailConfirmationToken).where(
            EmailConfirmationToken.user_id == user.id,
            ~EmailConfirmationToken.used
        )
    )
    old_tokens = result.scalars().all()
    for token in old_tokens:
        token.used = True
        db.add(token)
    
    # Create new token
    email_token = EmailConfirmationToken(
        email=body.email,
        token=confirmation_token,
        expires_at=expires_at,
        user_id=user.id,
        used=False
    )
    db.add(email_token)
    await db.commit()
    
    # Send confirmation email in background (non-blocking)
    background_tasks.add_task(
        send_confirmation_email_safe,
        body.email,
        confirmation_token
    )
    
    return {
        "message": "If an account exists, a confirmation email will be sent.",
        "email": body.email
    }


# ── Forgot password ───────────────────────────────────────────────────────────
class ForgotPasswordRequest(BaseModel):
    email: EmailStr


@router.post("/forgot-password")
async def forgot_password(
    body: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)
):
    """
    Always returns 200 — never reveal whether an email exists (security best practice).
    Sends a reset link if the account exists and uses email/password auth.
    """
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if user and user.hashed_password:
        # Delete any previous unused tokens for this user
        existing = await db.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.used == False,  # noqa: E712
            )
        )
        for old_token in existing.scalars().all():
            await db.delete(old_token)

        # Create new token (64 hex chars = 256 bits of entropy)
        raw_token = secrets.token_hex(32)
        expires = datetime.now(timezone.utc) + timedelta(hours=1)
        reset_token = PasswordResetToken(
            user_id=user.id,
            token=raw_token,
            expires_at=expires,
        )
        db.add(reset_token)
        await db.commit()

        try:
            await send_reset_email(user.email, raw_token)
        except Exception:
            pass  # logged inside send_reset_email

    return {"message": "If this email is registered, a reset link has been sent."}


# ── Reset password ────────────────────────────────────────────────────────────
class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@router.post("/reset-password")
async def reset_password(
    body: ResetPasswordRequest, db: AsyncSession = Depends(get_db)
):
    if len(body.new_password) < 8:
        raise HTTPException(
            status_code=400, detail="Password must be at least 8 characters."
        )

    # Find the token
    result = await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token == body.token)
    )
    reset_token = result.scalar_one_or_none()

    if not reset_token:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link.")

    if reset_token.used:
        raise HTTPException(
            status_code=400, detail="This reset link has already been used."
        )

    if datetime.now(timezone.utc) > reset_token.expires_at:
        raise HTTPException(
            status_code=400,
            detail="This reset link has expired. Please request a new one.",
        )

    # Update password
    user_result = await db.execute(select(User).where(User.id == reset_token.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid reset link.")

    user.hashed_password = bcrypt.hashpw(
        body.new_password.encode(), bcrypt.gensalt()
    ).decode()
    reset_token.used = True
    await db.commit()

    logger.info(f"Password reset successful for {user.email}")
    return {"message": "Password updated successfully. You can now log in."}


# ── Helper ────────────────────────────────────────────────────────────────────
def _user_dict(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "avatar_url": user.avatar_url,
        "plan": user.plan.value,
        "plan_youtube": user.plan_youtube.value if user.plan_youtube else None,
        "plan_twitch": user.plan_twitch.value if user.plan_twitch else None,
        "subscription_type": user.subscription_type,
        "generations_this_month": user.generations_this_month,
        "free_generations_left": user.free_generations_left,
        "can_generate": user.can_generate,
        "youtube_limit": user.youtube_limit,
        "twitch_limit": user.twitch_limit,
        "youtube_generations_left": user.youtube_generations_left,
        "twitch_generations_left": user.twitch_generations_left,
        # created_at may be a datetime or a text value depending on DB; handle both
        "created_at": (user.created_at.isoformat() if hasattr(user.created_at, "isoformat") else str(user.created_at)),
    }


# ── Stripe Pricing endpoint (for frontend) ──────────────────────────────────
@router.get("/stripe-pricing")
async def get_stripe_pricing():
    """Expose Stripe price IDs to frontend (loaded dynamically at runtime)."""
    prices = {}
    
    # Collect platform-specific prices (YouTube, Twitch, Combo)
    for prefix, platform in (
        ("STRIPE_YOUTUBE", "youtube"),
        ("STRIPE_TWITCH", "twitch"),
        ("STRIPE_COMBO", "combo"),
    ):
        platform_prices = {}
        for plan_name in ("STANDARD", "PRO", "PROPLUS"):
            plan_key = plan_name.lower()  # "standard", "pro", "proplus"
            monthly_key = f"{prefix}_{plan_name}_MONTHLY_PRICE_ID"
            yearly_key = f"{prefix}_{plan_name}_YEARLY_PRICE_ID"
            monthly_pid = os.getenv(monthly_key, "")
            yearly_pid = os.getenv(yearly_key, "")
            if monthly_pid or yearly_pid:
                platform_prices[plan_key] = {
                    "monthly": monthly_pid,
                    "yearly": yearly_pid,
                }
        if platform_prices:
            prices[platform] = platform_prices
    
    return prices
