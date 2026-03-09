import { useState, useRef, useEffect, type FormEvent } from 'react'
import { useAuth } from '../context/AuthContext'
import { generatorApi, authApi } from '../api'
import { type AxiosError } from 'axios'
import type { StatusResponse, Clip } from '../types'
import { Link2, Sparkles, Download, Crown, CheckCircle, Clock, AlertCircle, SlidersHorizontal } from 'lucide-react'

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

const STEPS = [
  { key: 'download',   label: 'Download',      pct: 20 },
  { key: 'transcribe', label: 'Transcription', pct: 40 },
  { key: 'analyze',    label: 'AI Analysis',   pct: 65 },
  { key: 'render',     label: 'Render',        pct: 97 },
] as const

function stepIndex(progress: number): number {
  return STEPS.filter((s) => progress >= s.pct).length - 1
}

interface ClipCardProps { clip: Clip; index: number }

function ClipCard({ clip, index }: ClipCardProps) {
  return (
    <div className="bg-white/5 border border-white/10 rounded-xl overflow-hidden hover:border-purple-500/50 transition">
      <div className="relative" style={{ paddingBottom: '177.78%' }}>
        <video
          src={`${API_BASE}${clip.file}`}
          className="absolute inset-0 w-full h-full object-cover"
          controls
          preload="metadata"
        />
        <div className="absolute top-2 left-2 bg-black/70 text-xs text-purple-300 px-2 py-0.5 rounded-full">
          {clip.viral_score}
        </div>
      </div>
      <div className="p-3">
        <p className="text-white text-xs font-medium truncate mb-1">Short {index + 1}</p>
        <p className="text-gray-500 text-xs mb-3">{clip.duration}s</p>
        {clip.hook && (
          <p className="text-gray-400 text-xs italic line-clamp-2 mb-3">&ldquo;{clip.hook}&rdquo;</p>
        )}
        <a
          href={`${API_BASE}${clip.file}`}
          download={`short_${index + 1}.mp4`}
          className="flex items-center justify-center gap-1.5 w-full py-1.5 bg-purple-600/20 hover:bg-purple-600/40 text-purple-300 text-xs rounded-lg transition"
        >
          <Download className="w-3 h-3" /> Download
        </a>
      </div>
    </div>
  )
}

export default function GeneratorPage() {
  const { user, refreshUser } = useAuth()

  const [url, setUrl] = useState('')
  const [maxClips, setMaxClips] = useState(3)

  // Keep maxClips within plan limits if plan changes
  const maxAllowed = user?.plan === 'pro' ? 20 : 5
  useEffect(() => {
    if (maxClips > maxAllowed) setMaxClips(maxAllowed)
  }, [maxAllowed, maxClips])
  const [status, setStatus] = useState<StatusResponse | null>(null)
  const [error, setError] = useState('')
  const [upgradeError, setUpgradeError] = useState(false)
  const [loadingCheckout, setLoadingCheckout] = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const stopPolling = () => clearInterval(pollRef.current ?? undefined)

  const startPolling = (id: string): void => {
    pollRef.current = setInterval(() => {
      void (async () => {
        try {
          const res = await generatorApi.status(id)
          setStatus(res.data)
          if (res.data.status === 'done' || res.data.status === 'error') {
            stopPolling()
            void refreshUser()
          }
        } catch {
          stopPolling()
        }
      })()
    }, 2000)
  }

  const handleGenerate = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault()
    setError('')
    setUpgradeError(false)
    setStatus(null)
    try {
      const res = await generatorApi.generate(url, maxClips)
      setStatus({ status: 'pending', progress: 0, step: 'Queued...', clips: [] })
      startPolling(res.data.job_id)
    } catch (err) {
      const axiosErr = err as AxiosError<{ detail: string }>
      if (axiosErr.response?.status === 402) setUpgradeError(true)
      else setError(axiosErr.response?.data?.detail ?? 'An error occurred.')
    }
  }

  const handleUpgrade = async (): Promise<void> => {
    setLoadingCheckout(true)
    try {
      const res = await authApi.createCheckout()
      window.location.href = res.data.checkout_url
    } catch {
      setLoadingCheckout(false)
    }
  }

  const currentStep = status ? stepIndex(status.progress) : -1
  const isProcessing = status?.status === 'processing' || status?.status === 'pending'
  const quotaEmpty = user?.plan === 'free' && user.free_generations_left === 0

  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      <div className="text-center mb-10">
        <h1 className="text-4xl font-bold text-white mb-3">
          <span className="bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
            AI Shorts Generator
          </span>
        </h1>
        <p className="text-gray-400">Turn any YouTube video into viral shorts</p>
        {user?.plan === 'free' && (
          <div className="mt-4 inline-flex items-center gap-2 px-4 py-2 bg-white/5 border border-white/10 rounded-full text-sm">
            {user.free_generations_left > 0 ? (
              <span className="text-gray-300">
                <span className="text-purple-400 font-semibold">{user.free_generations_left}</span>{' '}
                free generation{user.free_generations_left > 1 ? 's' : ''} left
              </span>
            ) : (
              <span className="text-red-400">No free generations left this month</span>
            )}
          </div>
        )}
      </div>

      {upgradeError && (
        <div className="mb-6 bg-gradient-to-r from-purple-900/50 to-pink-900/50 border border-purple-500/30 rounded-2xl p-6 text-center">
          <Crown className="w-8 h-8 text-yellow-400 mx-auto mb-3" />
          <h3 className="text-white font-semibold text-lg mb-1">Limit reached</h3>
          <p className="text-gray-400 text-sm mb-4">You used your 2 free generations this month.</p>
          <button
            onClick={() => void handleUpgrade()}
            disabled={loadingCheckout}
            className="px-6 py-2.5 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white font-semibold rounded-lg transition disabled:opacity-50"
          >
            {loadingCheckout ? 'Loading...' : 'Upgrade to Pro'}
          </button>
        </div>
      )}

      <form onSubmit={(e) => void handleGenerate(e)} className="mb-8">
        {/* URL input */}
        <div className="relative mb-4">
          <Link2 className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://www.youtube.com/watch?v=..."
            required
            disabled={isProcessing}
            className="w-full pl-12 pr-4 py-3.5 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 transition"
          />
        </div>

        {/* Clip count slider — FREE (1–5) and PRO (1–20) */}
        <div className={`p-4 rounded-xl mb-4 ${
          user?.plan === 'pro'
            ? 'bg-yellow-500/5 border border-yellow-500/20'
            : 'bg-white/5 border border-white/10'
        }`}>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <SlidersHorizontal className={`w-4 h-4 ${user?.plan === 'pro' ? 'text-yellow-400' : 'text-purple-400'}`} />
              <span className="text-sm font-medium text-white">Number of clips</span>
              {user?.plan === 'pro' ? (
                <span className="px-1.5 py-0.5 bg-yellow-500/20 text-yellow-400 text-xs rounded-full font-semibold">PRO</span>
              ) : (
                <span className="px-1.5 py-0.5 bg-white/10 text-gray-400 text-xs rounded-full">max 5 — upgrade for 20</span>
              )}
            </div>
            <span className={`text-3xl font-bold w-10 text-center ${user?.plan === 'pro' ? 'text-yellow-400' : 'text-purple-400'}`}>
              {maxClips}
            </span>
          </div>
          <input
            type="range"
            min={1}
            max={user?.plan === 'pro' ? 20 : 5}
            step={1}
            value={maxClips}
            onChange={(e) => setMaxClips(Number(e.target.value))}
            disabled={isProcessing}
            className={`w-full cursor-pointer disabled:opacity-50 ${user?.plan === 'pro' ? 'accent-yellow-400' : 'accent-purple-500'}`}
          />
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>1</span>
            {user?.plan === 'pro' ? (
              <>
                <span>5</span>
                <span>10</span>
                <span>15</span>
                <span>20</span>
              </>
            ) : (
              <>
                <span>3</span>
                <span>5</span>
              </>
            )}
          </div>
        </div>

        {/* Generate button */}
        <button
          type="submit"
          disabled={!url || isProcessing || quotaEmpty}
          className="w-full py-3.5 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white font-semibold rounded-xl transition flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Sparkles className="w-4 h-4" />
          {isProcessing ? 'Generating...' : `Generate ${maxClips} short${maxClips > 1 ? 's' : ''}`}
        </button>

        {error && <p className="mt-3 text-red-400 text-sm">{error}</p>}
      </form>

      {status && status.status !== 'done' && status.status !== 'error' && (
        <div className="bg-white/5 border border-white/10 rounded-2xl p-6 mb-8">
          <div className="h-2 bg-white/10 rounded-full mb-6 overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-purple-500 to-pink-500 rounded-full transition-all duration-500"
              style={{ width: `${status.progress}%` }}
            />
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {STEPS.map((step, i) => {
              const done = i < currentStep
              const active = i === currentStep
              return (
                <div
                  key={step.key}
                  className={`flex items-center gap-2 p-3 rounded-lg text-sm transition ${
                    active
                      ? 'bg-purple-600/20 border border-purple-500/30 text-purple-300'
                      : done ? 'text-green-400' : 'text-gray-600'
                  }`}
                >
                  {done
                    ? <CheckCircle className="w-4 h-4 shrink-0" />
                    : active
                    ? <div className="w-4 h-4 border-2 border-purple-400 border-t-transparent rounded-full animate-spin shrink-0" />
                    : <Clock className="w-4 h-4 shrink-0" />}
                  {step.label}
                </div>
              )
            })}
          </div>
          <p className="mt-4 text-center text-gray-400 text-sm">{status.step}</p>
        </div>
      )}

      {status?.status === 'error' && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-2xl p-6 mb-8 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-red-400 font-medium">Generation failed</p>
            <p className="text-red-400/70 text-sm mt-1">{status.step}</p>
          </div>
        </div>
      )}

      {status?.status === 'done' && status.clips.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-white font-semibold text-xl">
              {status.clips.length} short{status.clips.length > 1 ? 's' : ''} generated
            </h2>
            <button
              onClick={() =>
                status.clips.forEach((c, i) => {
                  setTimeout(() => {
                    const a = document.createElement('a')
                    a.href = `${API_BASE}${c.file}`
                    a.download = `short_${i + 1}.mp4`
                    a.click()
                  }, i * 400)
                })
              }
              className="flex items-center gap-2 px-4 py-2 bg-white/10 hover:bg-white/20 text-white text-sm rounded-lg transition"
            >
              <Download className="w-4 h-4" /> Download all
            </button>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {status.clips.map((clip, i) => (
              <ClipCard key={clip.file} clip={clip} index={i} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
