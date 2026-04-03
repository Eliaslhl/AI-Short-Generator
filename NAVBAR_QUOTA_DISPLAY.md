# Navbar Quota Display - Platform-Specific Counters

## Overview

The navbar now displays **separate quota counters for YouTube and Twitch**, allowing users to see their actual usage breakdown for each platform at a glance.

## What Changed

### Before ❌
- Showed only one counter based on the current platform
- **Combo plans** displayed as `5/100 left` (confusing - which platform?)
- Didn't separate YouTube and Twitch quotas

### After ✅
- **YouTube-only plans** → Shows: `🎬 YouTube: 5/10`
- **Twitch-only plans** → Shows: `🎮 Twitch: 8/25`
- **Combo plans** → Shows: `🎬 YouTube: 5/10 | 🎮 Twitch: 8/25`

## Desktop Display

```
┌─ Desktop Navbar ────────────────────────────────────────┐
│ [Logo] ... [COMBO] 🎬 YouTube: 5/10 | 🎮 Twitch: 8/25 │
│           [Generate] [Dashboard] [User] [Logout]        │
└─────────────────────────────────────────────────────────┘
```

### Color Coding
- Plan badges: **STANDARD** (blue), **PRO** (yellow), **PRO+** (pink)
- Quota numbers: **Purple-400** for the counts
- Separator: Gray text `|` between platforms

## Mobile Display

```
┌─ Mobile Menu ────────────────────┐
│ 👤 John Doe                       │
│    🎬 YT: 5/10 | 🎮 TW: 8/25    │
│ [Generate] [Dashboard]            │
│ [Settings] [Logout]               │
└──────────────────────────────────┘
```

Compact version uses abbreviations: **YT** and **TW** to save space

## Implementation Details

### Logic Flow

```typescript
// Get all platform counts
const youtubeLeft = getGenerationsLeft(user, 'youtube')
const youtubeLimit = getGenerationLimit(user, 'youtube')
const twitchLeft = getGenerationsLeft(user, 'twitch')
const twitchLimit = getGenerationLimit(user, 'twitch')

// Determine what to show based on subscription_type
const subscriptionType = user?.subscription_type
const showYouTube = subscriptionType === 'youtube' || subscriptionType === 'combo'
const showTwitch = subscriptionType === 'twitch' || subscriptionType === 'combo'
```

### Rendering Logic

**Desktop:**
```tsx
<span className="text-xs text-gray-500">
  {showYouTube && (
    <>
      🎬 YouTube: <span className="text-purple-400">{youtubeLeft}/{youtubeLimit}</span>
    </>
  )}
  {showYouTube && showTwitch && <span className="mx-1">|</span>}
  {showTwitch && (
    <>
      🎮 Twitch: <span className="text-purple-400">{twitchLeft}/{twitchLimit}</span>
    </>
  )}
</span>
```

**Mobile:**
```tsx
<span className="text-gray-400 text-xs">
  {showYouTube && <>🎬 YT: {youtubeLeft}/{youtubeLimit}</> }
  {showYouTube && showTwitch && <span className="mx-0.5">|</span>}
  {showTwitch && <>🎮 TW: {twitchLeft}/{twitchLimit}</> }
</span>
```

## User Benefits

✅ **Clear visibility** - Know exactly how many generations remain for each platform  
✅ **No confusion** - Combo users see both quotas simultaneously  
✅ **Responsive** - Adapts between desktop (full names) and mobile (abbreviated)  
✅ **Consistent** - Works across all account types (Standard, Pro, Pro+)  
✅ **Real-time** - Updates immediately after generation

## Testing Checklist

- [ ] YouTube-only account shows only YouTube counter
- [ ] Twitch-only account shows only Twitch counter
- [ ] Combo account shows both counters on desktop
- [ ] Combo account shows both counters on mobile (abbreviated)
- [ ] Counters update after generating a clip
- [ ] Counters match backend values in user profile
- [ ] Emoji and colors display correctly
- [ ] No layout shifts when switching between single/dual display

## Files Modified

- `frontend-react/src/components/Navbar.tsx` - Navbar component (49 lines, 12 lines changed)

## Commit

```
feat: Display separate YouTube & Twitch quota counters for all account types

- Show platform-specific counters in navbar for youtube, twitch, and combo plans
- Desktop display: 🎬 YouTube: X/Y | 🎮 Twitch: X/Y for combo plans
- Mobile display: Compact version (YT/TW shorthand) in user info
- Single platform accounts show only their respective counter
- All plan types (Standard, Pro, Pro+) now show accurate usage breakdown
```

Commit: `69f4133`

## Related

- `planUtils.ts` - Provides `getGenerationsLeft()` and `getGenerationLimit()` functions
- `User` model - Defines `subscription_type` field (youtube|twitch|combo|none)
- Backend API `/auth/me` - Provides `subscription_type` and quota counts
