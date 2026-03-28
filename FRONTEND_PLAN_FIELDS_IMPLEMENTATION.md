# Frontend: Platform-Specific Plan Fields Implementation

## Overview
The frontend now dynamically displays quota limits based on platform-specific plan fields returned by the backend API, instead of using hardcoded limits based on the legacy `plan` field.

## Changes Made

### 1. Updated `types.ts`
Added new optional fields to the `User` interface:
```typescript
export interface User {
  // ... existing fields ...
  plan_youtube?: Plan          // Platform-specific plan (YouTube)
  plan_twitch?: Plan           // Platform-specific plan (Twitch)
  subscription_type?: 'youtube' | 'twitch' | 'combo' | null
  // Computed limits and counters from API
  youtube_limit?: number       // Max generations/month for YouTube
  twitch_limit?: number        // Max generations/month for Twitch
  youtube_generations_left?: number
  twitch_generations_left?: number
}
```

These fields are now populated by the backend `/auth/me` endpoint.

### 2. Created `utils/planUtils.ts`
New utility module with platform-aware helper functions:

#### `getCurrentPlatform(user): CurrentPlatform`
- Determines the current platform (youtube | twitch | combo) from user's subscription_type
- Defaults to 'youtube' if not specified
- Used by other utilities to determine which platform fields to use

#### `getPlanForPlatform(user, platform): Plan`
- Returns the plan for a specific platform
- Falls back to legacy `plan` field for backward compatibility
- Allows per-platform plan differentiation (e.g., youtube=pro, twitch=free)

#### `getGenerationLimit(user, platform): number`
- Returns the monthly generation limit for a platform
- Prefers API-computed limit from `youtube_limit` / `twitch_limit`
- Falls back to hardcoded limits based on plan if API doesn't provide them
- Plans: free=2, standard=20, pro=50, proplus=100

#### `getGenerationsLeft(user, platform): number`
- Returns remaining generations for a platform this month
- Prefers platform-specific counters (`youtube_generations_left`, `twitch_generations_left`)
- Falls back to legacy `free_generations_left` field

#### `getMaxClipsAllowed(user, platform): number`
- Returns max concurrent clips for video generation
- Based on plan: free=3, standard=5, pro=10, proplus=20

### 3. Updated `DashboardPage.tsx`
**Import added:**
```typescript
import { getPlanForPlatform, getGenerationLimit, getGenerationsLeft, getCurrentPlatform } from '../utils/planUtils'
```

**Changes:**
- Removed hardcoded logic: `plan === 'standard' ? '20' : plan === 'pro' ? '50' : '100'`
- Now uses: `getGenerationLimit(user, platform)` and `getGenerationsLeft(user, platform)`
- Displays dynamic limits that match the API response
- Example:
  ```tsx
  // Before
  {plan === 'standard' ? '20' : plan === 'pro' ? '50' : '100'}
  
  // After
  {generationLimit}  // Value from API or computed from plan
  ```

### 4. Updated `GeneratorPage.tsx`
**Import added:**
```typescript
import { getPlanForPlatform, getGenerationLimit, getGenerationsLeft, getMaxClipsAllowed, getCurrentPlatform } from '../utils/planUtils'
```

**Changes:**
1. **Max clips calculation:**
   - Replaced hardcoded ternary: `user?.plan === 'proplus' ? 20 : user?.plan === 'pro' ? 10 : ...`
   - Now uses: `const maxAllowed = getMaxClipsAllowed(user, platform)`

2. **Quota display (header):**
   - Replaced hardcoded limits display
   - Now shows: `{generationsLeft} / {generationLimit} generations left this month`

3. **Quota exceeded message:**
   - Replaced hardcoded message: "You've used your 2 free generations..."
   - Now shows: `You've used all {generationLimit} of your {currentPlan} plan generations this month.`

4. **UI styling (colors, badges):**
   - Replaced all `user?.plan` with `currentPlan` variable
   - `currentPlan` is computed as: `getPlanForPlatform(user, platform)`
   - Maintains same visual styling but based on platform-specific plan

**Example of change:**
```tsx
// Before (hardcoded logic)
{user?.plan === 'proplus' ? (
  <span>20 clips max</span>
) : user?.plan === 'pro' ? (
  <span>10 clips max</span>
) : ...}

// After (API-driven)
const maxAllowed = getMaxClipsAllowed(user, platform)
// Use maxAllowed directly in UI
```

## Behavior

### For Test Accounts
- **test.youtube.pro@test.com:** Shows youtube_limit=50, youtube_generations_left=50
- **test.twitch.pro@test.com:** Shows twitch_limit=50, twitch_generations_left=50
- **test.combo.pro@test.com:** Shows both limits=50, both generations_left=50

### Backward Compatibility
- If API doesn't provide platform-specific fields, frontend falls back to legacy `plan` field
- Hardcoded limits are still used if API doesn't compute limits
- Ensures old API versions still work correctly

## Testing

### Build Verification
```bash
cd frontend-react
npm run build  # Should complete without errors
```

### Runtime Verification
1. Login to application
2. Check Dashboard page - should display correct quota for your plan
3. Check Generator page - should show correct max clips and remaining generations
4. If quota is empty, should show "Limit reached" message with correct plan name

### API Response Check
```bash
curl -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test.combo.pro@test.com","password":"TestPass123456"}' | jq '.user | {plan_youtube, plan_twitch, youtube_limit, twitch_limit, youtube_generations_left, twitch_generations_left}'
```

Expected output:
```json
{
  "plan_youtube": "pro",
  "plan_twitch": "pro",
  "youtube_limit": 50,
  "twitch_limit": 50,
  "youtube_generations_left": 50,
  "twitch_generations_left": 50
}
```

## Benefits

1. **Dynamic Limits:** Frontend now displays the exact limits computed by the backend
2. **Platform Awareness:** Different limits for YouTube, Twitch, and Combo plans
3. **Real-Time Updates:** When quotas are reset or plans change, frontend immediately reflects new limits
4. **Single Source of Truth:** Backend is authoritative for quota limits; frontend just displays them
5. **Future-Proof:** Can add new platforms without frontend code changes

## Potential Future Enhancements

1. **Platform Switcher:** Allow users to switch between YouTube/Twitch context in UI
2. **Per-Platform Quota Tracking:** Show separate progress bars for each platform
3. **Monthly Reset Timer:** Display countdown to next quota reset
4. **Usage Analytics:** Track quota consumption over time per platform
5. **Upgrade Guidance:** Show specific upgrade recommendations based on quota usage patterns
