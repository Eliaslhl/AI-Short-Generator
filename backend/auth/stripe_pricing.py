"""
stripe_pricing.py – Strip# ── YouTube Plans ───────# ── Twitch Plans ────────────────────────────────────────────────────────
TWITCH_PRICES = {
    BillingCycle.MONTHLY: {
        Plan.STANDARD: _get_env("STRIPE_TWITCH_STANDARD_MONTHLY_PRICE_ID", ""),
        Plan.PRO: _get_env("STRIPE_TWITCH_PRO_MONTHLY_PRICE_ID", ""),
        Plan.PROPLUS: _get_env("STRIPE_TWITCH_PROPLUS_MONTHLY_PRICE_ID", ""),
    },
    BillingCycle.YEARLY: {
        Plan.STANDARD: _get_env("STRIPE_TWITCH_STANDARD_YEARLY_PRICE_ID", ""),
        Plan.PRO: _get_env("STRIPE_TWITCH_PRO_YEARLY_PRICE_ID", ""),
        Plan.PROPLUS: _get_env("STRIPE_TWITCH_PROPLUS_YEARLY_PRICE_ID", ""),
    },
}───────────────────────────────────
YOUTUBE_PRICES = {
    BillingCycle.MONTHLY: {
        Plan.STANDARD: _get_env("STRIPE_YOUTUBE_STANDARD_MONTHLY_PRICE_ID") or _get_env("STRIPE_STANDARD_MONTHLY_PRICE_ID"),
        Plan.PRO: _get_env("STRIPE_YOUTUBE_PRO_MONTHLY_PRICE_ID") or _get_env("STRIPE_PRO_MONTHLY_PRICE_ID"),
        Plan.PROPLUS: _get_env("STRIPE_YOUTUBE_PROPLUS_MONTHLY_PRICE_ID") or _get_env("STRIPE_PROPLUS_MONTHLY_PRICE_ID"),
    },
    BillingCycle.YEARLY: {
        Plan.STANDARD: _get_env("STRIPE_YOUTUBE_STANDARD_YEARLY_PRICE_ID") or _get_env("STRIPE_STANDARD_YEARLY_PRICE_ID"),
        Plan.PRO: _get_env("STRIPE_YOUTUBE_PRO_YEARLY_PRICE_ID") or _get_env("STRIPE_PRO_YEARLY_PRICE_ID"),
        Plan.PROPLUS: _get_env("STRIPE_YOUTUBE_PROPLUS_YEARLY_PRICE_ID") or _get_env("STRIPE_PROPLUS_YEARLY_PRICE_ID"),
    },
}figuration for YouTube, Twitch, and Combo plans.

Maps Stripe price IDs to platforms and plans.
"""

import os
from enum import Enum as PyEnum

from backend.models.user import Plan


class PlatformType(str, PyEnum):
    YOUTUBE = "youtube"
    TWITCH = "twitch"
    COMBO = "combo"


class BillingCycle(str, PyEnum):
    MONTHLY = "monthly"
    YEARLY = "yearly"


def _get_env(key: str, default: str = "") -> str:
    """Get environment variable, return default if empty."""
    val = os.getenv(key, default)
    return val.strip() if val else default


# ── YouTube Plans ───────────────────────────────────────────────────────────
YOUTUBE_PRICES = {
    BillingCycle.MONTHLY: {
        Plan.STANDARD: _get_env("STRIPE_YOUTUBE_STANDARD_MONTHLY_PRICE_ID", "price_yt_std_m"),
        Plan.PRO: _get_env("STRIPE_YOUTUBE_PRO_MONTHLY_PRICE_ID", "price_yt_pro_m"),
        Plan.PROPLUS: _get_env("STRIPE_YOUTUBE_PROPLUS_MONTHLY_PRICE_ID", "price_yt_proplus_m"),
    },
    BillingCycle.YEARLY: {
        Plan.STANDARD: _get_env("STRIPE_YOUTUBE_STANDARD_YEARLY_PRICE_ID", "price_yt_std_y"),
        Plan.PRO: _get_env("STRIPE_YOUTUBE_PRO_YEARLY_PRICE_ID", "price_yt_pro_y"),
        Plan.PROPLUS: _get_env("STRIPE_YOUTUBE_PROPLUS_YEARLY_PRICE_ID", "price_yt_proplus_y"),
    },
}

# ── Twitch Plans ────────────────────────────────────────────────────────────
TWITCH_PRICES = {
    BillingCycle.MONTHLY: {
        Plan.STANDARD: _get_env("STRIPE_TWITCH_STANDARD_MONTHLY_PRICE_ID", "price_tw_std_m"),
        Plan.PRO: _get_env("STRIPE_TWITCH_PRO_MONTHLY_PRICE_ID", "price_tw_pro_m"),
        Plan.PROPLUS: _get_env("STRIPE_TWITCH_PROPLUS_MONTHLY_PRICE_ID", "price_tw_proplus_m"),
    },
    BillingCycle.YEARLY: {
        Plan.STANDARD: _get_env("STRIPE_TWITCH_STANDARD_YEARLY_PRICE_ID", "price_tw_std_y"),
        Plan.PRO: _get_env("STRIPE_TWITCH_PRO_YEARLY_PRICE_ID", "price_tw_pro_y"),
        Plan.PROPLUS: _get_env("STRIPE_TWITCH_PROPLUS_YEARLY_PRICE_ID", "price_tw_proplus_y"),
    },
}

# ── Combo Plans (YouTube + Twitch) ──────────────────────────────────────────
COMBO_PRICES = {
    BillingCycle.MONTHLY: {
        Plan.STANDARD: _get_env("STRIPE_COMBO_STANDARD_MONTHLY_PRICE_ID", ""),
        Plan.PRO: _get_env("STRIPE_COMBO_PRO_MONTHLY_PRICE_ID", ""),
        Plan.PROPLUS: _get_env("STRIPE_COMBO_PROPLUS_MONTHLY_PRICE_ID", ""),
    },
    BillingCycle.YEARLY: {
        Plan.STANDARD: _get_env("STRIPE_COMBO_STANDARD_YEARLY_PRICE_ID", ""),
        Plan.PRO: _get_env("STRIPE_COMBO_PRO_YEARLY_PRICE_ID", ""),
        Plan.PROPLUS: _get_env("STRIPE_COMBO_PROPLUS_YEARLY_PRICE_ID", ""),
    },
}


def get_price_id(
    platform: PlatformType,
    plan: Plan,
    billing_cycle: BillingCycle = BillingCycle.MONTHLY,
) -> str:
    """Get the Stripe price ID for a given platform, plan, and billing cycle."""
    prices_map = {
        PlatformType.YOUTUBE: YOUTUBE_PRICES,
        PlatformType.TWITCH: TWITCH_PRICES,
        PlatformType.COMBO: COMBO_PRICES,
    }
    
    if platform not in prices_map:
        raise ValueError(f"Unknown platform: {platform}")
    
    prices = prices_map[platform]
    if billing_cycle not in prices:
        raise ValueError(f"Unknown billing cycle: {billing_cycle}")
    
    cycle_prices = prices[billing_cycle]
    if plan not in cycle_prices:
        raise ValueError(f"Unknown plan: {plan}")
    
    return cycle_prices[plan]


# ── Reverse mapping: price_id → (platform, plan, billing_cycle) ────────────
def _build_reverse_map():
    """Build a reverse mapping from price_id to (platform, plan, billing_cycle)."""
    mapping = {}
    
    for cycle in [BillingCycle.MONTHLY, BillingCycle.YEARLY]:
        for plan in [Plan.STANDARD, Plan.PRO, Plan.PROPLUS]:
            # YouTube
            yt_price = get_price_id(PlatformType.YOUTUBE, plan, cycle)
            if yt_price:
                mapping[yt_price] = (PlatformType.YOUTUBE, plan, cycle)
            
            # Twitch
            tw_price = get_price_id(PlatformType.TWITCH, plan, cycle)
            if tw_price:
                mapping[tw_price] = (PlatformType.TWITCH, plan, cycle)
            
            # Combo
            combo_price = get_price_id(PlatformType.COMBO, plan, cycle)
            if combo_price:
                mapping[combo_price] = (PlatformType.COMBO, plan, cycle)
    
    return mapping


PRICE_ID_TO_PLAN = _build_reverse_map()


def parse_price_id(price_id: str) -> tuple[PlatformType, Plan, BillingCycle] | None:
    """Parse a Stripe price ID to extract platform, plan, and billing cycle.
    
    Returns (platform, plan, billing_cycle) or None if not found.
    """
    return PRICE_ID_TO_PLAN.get(price_id)


# ── Legacy mapping for backward compatibility ──────────────────────────────
def _build_legacy_price_to_plan():
    """Build the old PRICE_TO_PLAN mapping for backward compatibility (YouTube only)."""
    mapping = {}
    for cycle in [BillingCycle.MONTHLY, BillingCycle.YEARLY]:
        for plan in [Plan.STANDARD, Plan.PRO, Plan.PROPLUS]:
            price = get_price_id(PlatformType.YOUTUBE, plan, cycle)
            if price:
                mapping[price] = plan
    return mapping


PRICE_TO_PLAN = _build_legacy_price_to_plan()  # For backward compatibility
