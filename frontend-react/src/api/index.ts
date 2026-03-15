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
  generate: (youtubeUrl: string, maxClips: number = 3, language: string = '', subtitleStyle: string = 'default'): Promise<AxiosResponse<GenerateResponse>> =>
    client.post('/api/generate', { youtube_url: youtubeUrl, max_clips: maxClips, language, subtitle_style: subtitleStyle }),

  status: (jobId: string): Promise<AxiosResponse<StatusResponse>> =>
    client.get(`/api/status/${jobId}`),

  clips: (jobId: string): Promise<AxiosResponse<ClipsResponse>> =>
    client.get(`/api/clips/${jobId}`),

  history: (): Promise<AxiosResponse<HistoryResponse>> =>
    client.get('/api/history'),
}
