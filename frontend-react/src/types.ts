// ─── Domain types ─────────────────────────────────────────────────────────────

export type Plan = 'free' | 'pro'

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
  duration: number
  viral_score: number
  hook: string | null
  start_time: number
  end_time: number
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

export interface HistoryResponse {
  history: Job[]
}

export interface CheckoutResponse {
  checkout_url: string
}
