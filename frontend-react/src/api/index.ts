import client from './client'
import type {
  AuthResponse,
  GenerateResponse,
  StatusResponse,
  ClipsResponse,
  HistoryResponse,
  CheckoutResponse,
} from '../types'
import type { AxiosResponse } from 'axios'

export const authApi = {
  register: (email: string, password: string, fullName: string): Promise<AxiosResponse<AuthResponse>> =>
    client.post('/auth/register', { email, password, full_name: fullName }),

  login: (email: string, password: string): Promise<AxiosResponse<AuthResponse>> =>
    client.post('/auth/login', { email, password }),

  me: (): Promise<AxiosResponse<AuthResponse['user']>> =>
    client.get('/auth/me'),

  googleLogin: (): void => {
    window.location.href = `${client.defaults.baseURL}/auth/google`
  },

  createCheckout: (priceId: string): Promise<AxiosResponse<CheckoutResponse>> =>
    client.post('/auth/stripe/checkout', { price_id: priceId }),

  cancelSubscription: (): Promise<AxiosResponse<{ message: string }>> =>
    client.post('/auth/stripe/cancel'),
}

export const generatorApi = {
  generate: (youtubeUrl: string, maxClips: number = 3, language: string = '', subtitleStyle: string = 'default', includeSubtitles: boolean = true): Promise<AxiosResponse<GenerateResponse>> =>
    client.post('/api/generate', { youtube_url: youtubeUrl, max_clips: maxClips, language, subtitle_style: subtitleStyle, include_subtitles: includeSubtitles }),

  preview: (url: string): Promise<AxiosResponse<{ url: string; title?: string; duration?: number; thumbnail?: string }>> =>
    client.post('/api/preview', { url }),

  twitchVods: (channelLogin: string, limit: number = 20): Promise<AxiosResponse<{ channel_login: string; vods: Array<{ id: string; title?: string; created_at?: string; duration?: number; view_count?: number; url?: string; thumbnail_url?: string; channel_name?: string }> }>> =>
    client.post('/api/twitch/vods', { channel_login: channelLogin, limit }),
  status: (jobId: string): Promise<AxiosResponse<StatusResponse>> =>
    client.get(`/api/status/${jobId}`),

  clips: (jobId: string): Promise<AxiosResponse<ClipsResponse>> =>
    client.get(`/api/clips/${jobId}`),

  history: (): Promise<AxiosResponse<HistoryResponse>> =>
    client.get('/api/history'),
}
