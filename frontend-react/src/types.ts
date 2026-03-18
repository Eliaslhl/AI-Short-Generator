// ─── Domain types ─────────────────────────────────────────────────────────────

export type Plan = 'free' | 'standard' | 'pro' | 'proplus'

export interface User {
  id: number
  email: string
  full_name: string | null
  avatar_url: string | null
  plan: Plan
  generations_this_month: number
  free_generations_left: number
}

export interface Clip {
  file: string
  poster?: string
  duration: number
  viral_score: number
  hook?: string | null
  title?: string | null
  hashtags?: string[] | null
  start?: number
  end?: number
}

export type JobStatus = 'pending' | 'processing' | 'done' | 'error'

export interface Job {
  id: string
  youtube_url: string
  video_title: string | null
  status: JobStatus
  progress: number
  step: string
  clips: Clip[]
  clips_count: number
  created_at: string
  hashtags?: string[] | null
}

// ─── API response shapes ───────────────────────────────────────────────────────

export interface AuthResponse {
  access_token: string
  token_type: string
  user: User
}

export interface GenerateResponse {
  job_id: string
  message: string
}

export interface StatusResponse {
  status: JobStatus
  progress: number
  step: string
  clips: Clip[]
}

export interface ClipsResponse {
  clips: Clip[]
  video_title?: string | null
  status?: JobStatus
}

export interface HistoryResponse {
  history: Job[]
}

export interface CheckoutResponse {
  checkout_url: string
}
