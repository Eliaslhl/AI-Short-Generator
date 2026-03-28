import { describe, it, expect } from 'vitest'
import {
  getCurrentPlatform,
  getPlanForPlatform,
  getGenerationLimit,
  getGenerationsLeft,
  getMaxClipsAllowed,
} from './planUtils'
import type { User } from '../types'

describe('planUtils', () => {
  describe('getCurrentPlatform', () => {
    it('should return youtube as default', () => {
      expect(getCurrentPlatform(null)).toBe('youtube')
      expect(getCurrentPlatform({} as User)).toBe('youtube')
    })

    it('should return platform from subscription_type', () => {
      const userYT = { subscription_type: 'youtube' } as User
      const userTwitch = { subscription_type: 'twitch' } as User
      const userCombo = { subscription_type: 'combo' } as User

      expect(getCurrentPlatform(userYT)).toBe('youtube')
      expect(getCurrentPlatform(userTwitch)).toBe('twitch')
      expect(getCurrentPlatform(userCombo)).toBe('combo')
    })
  })

  describe('getPlanForPlatform', () => {
    it('should return youtube plan for youtube platform', () => {
      const user = {
        plan_youtube: 'pro' as const,
        plan_twitch: 'standard' as const,
        plan: 'free' as const,
      } as User

      expect(getPlanForPlatform(user, 'youtube')).toBe('pro')
      expect(getPlanForPlatform(user, 'twitch')).toBe('standard')
    })

    it('should fallback to legacy plan field', () => {
      const user = {
        plan: 'pro' as const,
      } as User

      expect(getPlanForPlatform(user, 'youtube')).toBe('pro')
      expect(getPlanForPlatform(user, 'twitch')).toBe('pro')
    })

    it('should return free for null user', () => {
      expect(getPlanForPlatform(null, 'youtube')).toBe('free')
    })
  })

  describe('getGenerationLimit', () => {
    it('should return API limit when available', () => {
      const user = {
        youtube_limit: 50,
        twitch_limit: 75,
        plan_youtube: 'pro' as const,
        plan_twitch: 'proplus' as const,
      } as User

      expect(getGenerationLimit(user, 'youtube')).toBe(50)
      expect(getGenerationLimit(user, 'twitch')).toBe(75)
    })

    it('should compute limit from plan when API limit not available', () => {
      const userPro = {
        plan_youtube: 'pro' as const,
        plan_twitch: 'pro' as const,
      } as User

      expect(getGenerationLimit(userPro, 'youtube')).toBe(50)
      expect(getGenerationLimit(userPro, 'twitch')).toBe(50)
    })

    it('should return hardcoded limits for each plan', () => {
      const userStandard = {
        plan_youtube: 'standard' as const,
      } as User
      const userProPlus = {
        plan_youtube: 'proplus' as const,
      } as User
      const userFree = {
        plan_youtube: 'free' as const,
      } as User

      expect(getGenerationLimit(userStandard, 'youtube')).toBe(20)
      expect(getGenerationLimit(userProPlus, 'youtube')).toBe(100)
      expect(getGenerationLimit(userFree, 'youtube')).toBe(2)
    })
  })

  describe('getGenerationsLeft', () => {
    it('should return API count when available', () => {
      const user = {
        youtube_generations_left: 25,
        twitch_generations_left: 40,
      } as User

      expect(getGenerationsLeft(user, 'youtube')).toBe(25)
      expect(getGenerationsLeft(user, 'twitch')).toBe(40)
    })

    it('should fallback to legacy field', () => {
      const user = {
        free_generations_left: 15,
      } as User

      expect(getGenerationsLeft(user, 'youtube')).toBe(15)
      expect(getGenerationsLeft(user, 'twitch')).toBe(15)
    })
  })

  describe('getMaxClipsAllowed', () => {
    it('should return max clips per plan', () => {
      const userFree = { plan: 'free' as const } as User
      const userStandard = { plan: 'standard' as const } as User
      const userPro = { plan: 'pro' as const } as User
      const userProPlus = { plan: 'proplus' as const } as User

      expect(getMaxClipsAllowed(userFree, 'youtube')).toBe(3)
      expect(getMaxClipsAllowed(userStandard, 'youtube')).toBe(5)
      expect(getMaxClipsAllowed(userPro, 'youtube')).toBe(10)
      expect(getMaxClipsAllowed(userProPlus, 'youtube')).toBe(20)
    })
  })
})
