"""
models/user.py – User, Subscription and Job database models.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import String, Boolean, DateTime, Integer, ForeignKey, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


def _now():
    return datetime.now(timezone.utc)


def _uuid():
    return str(uuid.uuid4())


class Plan(str, PyEnum):
    FREE = "free"
    STANDARD = "standard"
    PRO = "pro"
    PROPLUS = "proplus"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )  # None for OAuth users
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # OAuth
    google_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Plan (legacy, kept for backward compatibility)
    plan: Mapped[Plan] = mapped_column(Enum(Plan), default=Plan.FREE)
    generations_this_month: Mapped[int] = mapped_column(Integer, default=0)
    plan_reset_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now
    )

    # NEW: Separated YouTube and Twitch plans + quotas
    plan_youtube: Mapped[Plan] = mapped_column(
        Enum(Plan), default=Plan.FREE, nullable=True
    )
    plan_twitch: Mapped[Plan] = mapped_column(
        Enum(Plan), default=Plan.FREE, nullable=True
    )
    subscription_type: Mapped[str] = mapped_column(
        String(50), default="none", nullable=True
    )  # "none" | "youtube" | "twitch" | "combo"

    # YouTube quota
    youtube_generations_month: Mapped[int] = mapped_column(Integer, default=0)
    youtube_plan_reset_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=True
    )

    # Per-user overrides for limits (optional)
    youtube_limit_override: Mapped[int | None] = mapped_column(Integer, nullable=True)
    twitch_limit_override: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Twitch quota
    twitch_generations_month: Mapped[int] = mapped_column(Integer, default=0)
    twitch_plan_reset_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=True
    )

    # Stripe
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    stripe_subscription_id_twitch: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    # Relationships
    jobs: Mapped[list["Job"]] = relationship(
        "Job", back_populates="user", cascade="all, delete-orphan"
    )

    # Monthly generation limits per plan
    PLAN_LIMITS_YOUTUBE: dict = {
        Plan.FREE: 2,
        Plan.STANDARD: 10,
        Plan.PRO: 25,
        Plan.PROPLUS: 50,
    }

    PLAN_LIMITS_TWITCH: dict = {
        Plan.FREE: 2,
        Plan.STANDARD: 10,
        Plan.PRO: 25,
        Plan.PROPLUS: 50,
    }

    # Legacy mapping (for backward compatibility)
    PLAN_LIMITS: dict = PLAN_LIMITS_YOUTUBE

    @property
    def monthly_limit(self) -> int:
        """Legacy property: returns YouTube limit for backward compatibility."""
        return self.PLAN_LIMITS_YOUTUBE.get(self.plan_youtube or self.plan, 2)

    @property
    def youtube_limit(self) -> int:
        """YouTube monthly generation limit."""
        # Prefer per-user override when set
        if getattr(self, "youtube_limit_override", None):
            return int(self.youtube_limit_override)
        return self.PLAN_LIMITS_YOUTUBE.get(self.plan_youtube or self.plan, 2)

    @property
    def twitch_limit(self) -> int:
        """Twitch monthly generation limit."""
        # Prefer per-user override when set
        if getattr(self, "twitch_limit_override", None):
            return int(self.twitch_limit_override)
        return self.PLAN_LIMITS_TWITCH.get(self.plan_twitch or Plan.FREE, 2)

    @property
    def free_generations_left(self) -> int:
        """Legacy property: returns YouTube generations left."""
        return max(0, self.youtube_limit - (self.youtube_generations_month or 0))

    @property
    def youtube_generations_left(self) -> int:
        """YouTube generations left this month."""
        return max(0, self.youtube_limit - (self.youtube_generations_month or 0))

    @property
    def twitch_generations_left(self) -> int:
        """Twitch generations left this month."""
        return max(0, self.twitch_limit - (self.twitch_generations_month or 0))

    @property
    def can_generate(self) -> bool:
        """Legacy property: can generate on YouTube."""
        return (self.youtube_generations_month or 0) < self.youtube_limit

    @property
    def can_generate_youtube(self) -> bool:
        """Can generate on YouTube."""
        return (self.youtube_generations_month or 0) < self.youtube_limit

    @property
    def can_generate_twitch(self) -> bool:
        """Can generate on Twitch."""
        return (self.twitch_generations_month or 0) < self.twitch_limit


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )

    youtube_url: Mapped[str] = mapped_column(String(512), nullable=False)
    video_title: Mapped[str | None] = mapped_column(String(512), nullable=True)

    status: Mapped[str] = mapped_column(
        String(50), default="pending"
    )  # pending, processing, done, error
    progress: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    clips_json: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # JSON array of clip metadata

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="jobs")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    token: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    used: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped["User"] = relationship("User")


class EmailConfirmationToken(Base):
    __tablename__ = "email_confirmation_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    token: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped["User | None"] = relationship("User")
