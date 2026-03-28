import { Plan, User } from '@/types'

/** Determine which platform we're currently working with */
export type CurrentPlatform = 'youtube' | 'twitch' | 'combo'

/**
 * Get current platform from user subscription
 * Default: 'youtube' (most common platform)
 */
export function getCurrentPlatform(user: User | null): CurrentPlatform {
  if (!user) return 'youtube'
  if (user.subscription_type === 'combo') return 'combo'
  if (user.subscription_type === 'twitch') return 'twitch'
  return 'youtube'
}

/**
 * Get the plan for the current platform
 * Falls back to legacy `plan` field for backward compatibility
 */
export function getPlanForPlatform(user: User | null, platform: CurrentPlatform = 'youtube'): Plan {
  if (!user) return 'free'

  // If using combo, both platforms should be in sync; default to youtube
  if (platform === 'combo' || platform === 'youtube') {
    return (user.plan_youtube as Plan) ?? user.plan ?? 'free'
  }
  if (platform === 'twitch') {
    return (user.plan_twitch as Plan) ?? user.plan ?? 'free'
  }

  return user.plan ?? 'free'
}

/**
 * Get generations limit for the current platform
 * Falls back to hardcoded limits based on plan
 */
export function getGenerationLimit(user: User | null, platform: CurrentPlatform = 'youtube'): number {
  if (!user) return 2

  // Prefer computed limits from API
  if (platform === 'twitch' && user.twitch_limit !== undefined) {
    return user.twitch_limit
  }
  if ((platform === 'youtube' || platform === 'combo') && user.youtube_limit !== undefined) {
    return user.youtube_limit
  }

  // Fallback: compute from plan
  const plan = getPlanForPlatform(user, platform)
  const planLimits: Record<Plan, number> = {
    free: 2,
    standard: 20,
    pro: 50,
    proplus: 100,
  }

  return planLimits[plan] ?? 2
}

/**
 * Get generations left this month for the current platform
 * Falls back to legacy `free_generations_left` field
 */
export function getGenerationsLeft(user: User | null, platform: CurrentPlatform = 'youtube'): number {
  if (!user) return 2

  // Prefer platform-specific counts from API
  if (platform === 'twitch' && user.twitch_generations_left !== undefined) {
    return user.twitch_generations_left
  }
  if ((platform === 'youtube' || platform === 'combo') && user.youtube_generations_left !== undefined) {
    return user.youtube_generations_left
  }

  // Fallback: use legacy field (works for all platforms if not distinguished)
  return user.free_generations_left ?? 0
}

/**
 * Get max clips allowed for concurrent generation based on plan
 */
export function getMaxClipsAllowed(user: User | null, platform: CurrentPlatform = 'youtube'): number {
  const plan = getPlanForPlatform(user, platform)

  const clipLimits: Record<Plan, number> = {
    free: 3,
    standard: 5,
    pro: 10,
    proplus: 20,
  }

  return clipLimits[plan] ?? 3
}
