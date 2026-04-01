#!/usr/bin/env python
"""
check_stripe_config.py – Verify Stripe pricing configuration.

Usage:
    python check_stripe_config.py
"""

import os
import sys


def _get_env(key: str) -> str:
    """Get environment variable value."""
    return os.getenv(key, "").strip()


def main():
    """Check and report Stripe configuration status."""
    print("🔍 Checking Stripe Configuration...\n")

    categories = {
        "YouTube Plans": [
            "STRIPE_YOUTUBE_STANDARD_MONTHLY_PRICE_ID",
            "STRIPE_YOUTUBE_STANDARD_YEARLY_PRICE_ID",
            "STRIPE_YOUTUBE_PRO_MONTHLY_PRICE_ID",
            "STRIPE_YOUTUBE_PRO_YEARLY_PRICE_ID",
            "STRIPE_YOUTUBE_PROPLUS_MONTHLY_PRICE_ID",
            "STRIPE_YOUTUBE_PROPLUS_YEARLY_PRICE_ID",
        ],
        "Twitch Plans": [
            "STRIPE_TWITCH_STANDARD_MONTHLY_PRICE_ID",
            "STRIPE_TWITCH_STANDARD_YEARLY_PRICE_ID",
            "STRIPE_TWITCH_PRO_MONTHLY_PRICE_ID",
            "STRIPE_TWITCH_PRO_YEARLY_PRICE_ID",
            "STRIPE_TWITCH_PROPLUS_MONTHLY_PRICE_ID",
            "STRIPE_TWITCH_PROPLUS_YEARLY_PRICE_ID",
        ],
        "Combo Plans": [
            "STRIPE_COMBO_STANDARD_MONTHLY_PRICE_ID",
            "STRIPE_COMBO_STANDARD_YEARLY_PRICE_ID",
            "STRIPE_COMBO_PRO_MONTHLY_PRICE_ID",
            "STRIPE_COMBO_PRO_YEARLY_PRICE_ID",
            "STRIPE_COMBO_PROPLUS_MONTHLY_PRICE_ID",
            "STRIPE_COMBO_PROPLUS_YEARLY_PRICE_ID",
        ],
    }

    total_missing = 0

    for category, keys in categories.items():
        print(f"📦 {category}")
        missing_in_category = 0

        for key in keys:
            value = _get_env(key)
            if value and value.startswith("price_"):
                print(f"  ✅ {key}")
            else:
                print(f"  ❌ {key} = {value or '(empty)'}")
                missing_in_category += 1
                total_missing += 1

        status = f"({len(keys) - missing_in_category}/{len(keys)})" if missing_in_category else "✨ Complete!"
        print(f"     {status}\n")

    print("=" * 60)
    if total_missing == 0:
        print("✅ All Stripe prices are configured!")
        print("You can now use the checkout endpoints.\n")
        return 0
    else:
        print(f"⚠️  Missing {total_missing} price IDs.")
        print("Please add them to .env before deploying.\n")
        print("Refer to STRIPE_QUICK_SETUP.md for instructions.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
