# Pricing Page Update Summary

## Changes Made

### 1. **Backend Changes**
✅ **Already Completed:**
- Dual-plan model: `plan_youtube`, `plan_twitch`, `subscription_type`
- Stripe webhook handler supports both metadata.plan and subscription retrieval
- Environment variables: `STRIPE_YOUTUBE_*`, `STRIPE_TWITCH_*`, `STRIPE_COMBO_*`
- Database migration file created (manual ALTERs applied locally)

### 2. **Frontend Changes (LandingPage.tsx)**

#### Platform-Specific Plan Arrays
Remplacé le single `PLANS` array par `PLANS_BY_PLATFORM`:
- `youtube`: Free, Standard, Pro, Pro+ (existing pricing)
- `twitch`: Free, Standard, Pro (platform-specific features like "VODs", "clips", "chatter detection")
- `combo`: Combo Pro (best value combining YouTube Pro + Twitch Pro)

**Key differences by platform:**
- **YouTube**: "videos / month", "shorts per video", "Auto zoom speaker"
- **Twitch**: "VODs / month", "clips per VOD", "Auto zoom streamer", "Chatter detection"
- **Combo**: All features from both YouTube Pro + Twitch Pro

#### Stripe Price IDs
Split into three separate mappings:
- `PRICE_IDS_YOUTUBE`: Existing price IDs (hardcoded)
- `PRICE_IDS_TWITCH`: From env variables `REACT_APP_STRIPE_TWITCH_*`
- `PRICE_IDS_COMBO`: From env variables `REACT_APP_STRIPE_COMBO_*`

#### Platform Tabs
Added new state: `platform` (`'youtube' | 'twitch' | 'combo'`)
- Three tab buttons with emojis: 📺 YouTube | 🎮 Twitch | ⚡ Combo Pack
- Tabs filter which plans are displayed
- Same billing toggle (Monthly/Yearly) applies to all platforms

#### Updated handleUpgrade()
Logic now reads the selected platform and maps to correct Price ID set before redirecting to Stripe Checkout.

### 3. **Frontend Environment Setup**
Updated `frontend-react/.env.example` to include all Stripe Price ID variables:
- YouTube Price IDs (pre-filled with existing values)
- Twitch Price IDs (placeholders to be filled)
- Combo Price IDs (placeholders to be filled)

Created `frontend-react/PRICING_ENV_SETUP.md` with detailed instructions on:
- How to copy `.env.example` → `.env.local`
- Where to find Price IDs in Stripe Dashboard
- How to populate each variable
- Testing checklist

### 4. **Card Design**
**Unchanged** — kept existing design:
- Purple gradient for Pro plans
- Pink/Purple gradient for Pro+ (Combo)
- Default white/gray for Standard/Free
- Same badge system ("⭐ MOST POPULAR", "⚡ BEST VALUE")
- Same feature list styling with checkmarks
- Same CTA buttons with hover effects

## Testing Checklist

- [ ] Verify pricing section loads with YouTube tab selected
- [ ] Switch to Twitch tab → verify different plan names/features displayed
- [ ] Switch to Combo tab → verify single "Combo Pro" plan shown
- [ ] Toggle Monthly/Yearly billing → prices update for all platforms
- [ ] Click "Start Standard" on YouTube while logged in → redirects to Stripe Checkout
- [ ] Verify Price ID not configured error if env vars missing
- [ ] In production: populate Stripe Price IDs in frontend `.env`
- [ ] Verify webhook updates correct `plan_youtube` / `plan_twitch` fields in DB

## Environment Variables to Set

**Production Frontend (.env or deployment config):**
```
REACT_APP_STRIPE_YOUTUBE_STANDARD_MONTHLY=price_xxx
REACT_APP_STRIPE_YOUTUBE_STANDARD_YEARLY=price_xxx
REACT_APP_STRIPE_YOUTUBE_PRO_MONTHLY=price_xxx
REACT_APP_STRIPE_YOUTUBE_PRO_YEARLY=price_xxx
REACT_APP_STRIPE_YOUTUBE_PROPLUS_MONTHLY=price_xxx
REACT_APP_STRIPE_YOUTUBE_PROPLUS_YEARLY=price_xxx
REACT_APP_STRIPE_TWITCH_STANDARD_MONTHLY=price_xxx
REACT_APP_STRIPE_TWITCH_STANDARD_YEARLY=price_xxx
REACT_APP_STRIPE_TWITCH_PRO_MONTHLY=price_xxx
REACT_APP_STRIPE_TWITCH_PRO_YEARLY=price_xxx
REACT_APP_STRIPE_COMBO_PRO_MONTHLY=price_xxx
REACT_APP_STRIPE_COMBO_PRO_YEARLY=price_xxx
```

## Files Modified

1. `frontend-react/src/pages/LandingPage.tsx`
   - Added `PLANS_BY_PLATFORM` (youtube, twitch, combo)
   - Added `PRICE_IDS_YOUTUBE`, `PRICE_IDS_TWITCH`, `PRICE_IDS_COMBO`
   - Added `platform` state and tabs
   - Updated `handleUpgrade()` logic
   - Updated pricing section JSX with platform tabs

2. `frontend-react/.env.example`
   - Added all Stripe Price ID env variable definitions

3. `frontend-react/PRICING_ENV_SETUP.md` (new)
   - Setup instructions for frontend pricing env variables

## Notes

- The backend already handles all three plan types (YouTube, Twitch, Combo)
- Frontend now displays them clearly with platform-specific messaging
- Design remains consistent with existing card styling
- Webhook handler intelligently stores plan in `plan_youtube` or `plan_twitch` based on price mapping
