import { useState, useRef, useEffect, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { generatorApi } from '../api'
import { type AxiosError } from 'axios'
import type { StatusResponse, Clip } from '../types'
import { Link2, Sparkles, Download, Crown, CheckCircle, Clock, AlertCircle, SlidersHorizontal, Expand, X, Lightbulb, Globe, Type } from 'lucide-react'
import { getPlanForPlatform, getGenerationLimit, getGenerationsLeft, getMaxClipsAllowed, getCurrentPlatform } from '../utils/planUtils'

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

// Example URL shown as a hint to new users
const EXAMPLE_URL = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'

const LANGUAGES = [
  { code: '',   label: '🌐 Auto-detect' },
  { code: 'en', label: '🇬🇧 English' },
  { code: 'fr', label: '🇫🇷 French' },
  { code: 'es', label: '🇪🇸 Spanish' },
  { code: 'de', label: '🇩🇪 German' },
  { code: 'pt', label: '🇧🇷 Portuguese' },
  { code: 'it', label: '🇮🇹 Italian' },
  { code: 'nl', label: '🇳🇱 Dutch' },
  { code: 'ar', label: '🇸🇦 Arabic' },
  { code: 'zh', label: '🇨🇳 Chinese' },
  { code: 'ja', label: '🇯🇵 Japanese' },
  { code: 'ko', label: '🇰🇷 Korean' },
  { code: 'ru', label: '🇷🇺 Russian' },
  { code: 'hi', label: '🇮🇳 Hindi' },
]

const SUBTITLE_STYLES = [
  { code: 'default',  label: '🟡 Classic',       desc: 'Yellow bold — TikTok style' },
  { code: 'bold',     label: '⚪ Bold White',     desc: 'White bold with strong outline' },
  { code: 'outlined', label: '🔵 Outlined',       desc: 'White with blue stroke' },
  { code: 'neon',     label: '💚 Neon',           desc: 'Neon green glow effect' },
  { code: 'minimal',  label: '◻️ Minimal',         desc: 'Clean white, no stroke' },
]

const STEPS = [
  { key: 'download',   label: 'Download',      pct: 20 },
  { key: 'transcribe', label: 'Transcription', pct: 40 },
  { key: 'analyze',    label: 'AI Analysis',   pct: 65 },
  { key: 'render',     label: 'Render',        pct: 97 },
] as const

function stepIndex(progress: number): number {
  return STEPS.filter((s) => progress >= s.pct).length - 1
}

interface ClipCardProps { clip: Clip; index: number; onExpand: (clip: Clip, index: number) => void }

function ClipCard({ clip, index, onExpand }: ClipCardProps) {
  const navigate = useNavigate()
  return (
    <div className="bg-white/5 border border-white/10 rounded-xl overflow-hidden hover:border-purple-500/50 transition group">
      <div className="relative" style={{ paddingBottom: '177.78%' }}>
        <video
          src={`${API_BASE}${clip.file}`}
          className="absolute inset-0 w-full h-full object-cover"
          preload="metadata"
        />
        {/* Viral score badge */}
        <div className="absolute top-2 left-2 bg-black/70 text-xs text-purple-300 px-2 py-0.5 rounded-full">
          {clip.viral_score}
        </div>
        {/* Expand overlay on hover */}
        <button
          onClick={() => onExpand(clip, index)}
          className="absolute inset-0 flex items-center justify-center bg-black/0 group-hover:bg-black/40 transition-all duration-200"
          aria-label="Watch fullscreen"
        >
          <div className="opacity-0 group-hover:opacity-100 transition-opacity duration-200 bg-white/10 backdrop-blur-sm border border-white/20 rounded-full p-3">
            <Expand className="w-6 h-6 text-white" />
          </div>
        </button>
      </div>
      <div className="p-3">
        {clip.title ? (
          <p className="text-white text-xs font-semibold truncate mb-0.5">{clip.title}</p>
        ) : (
          <p className="text-white text-xs font-medium truncate mb-1">Short {index + 1}</p>
        )}
        <p className="text-gray-500 text-xs mb-2">{clip.duration}s</p>
        {clip.hook && (
          <p className="text-gray-400 text-xs italic line-clamp-2 mb-2">&ldquo;{clip.hook}&rdquo;</p>
        )}
        {clip.hashtags && clip.hashtags.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-2">
            {clip.hashtags.map((tag) => (
              <button
                key={tag}
                onClick={() => navigate(`/?tag=${encodeURIComponent(tag)}`)}
                className="text-[10px] text-pink-400 bg-pink-500/10 px-1.5 py-0.5 rounded-full hover:bg-pink-500/15 transition cursor-pointer"
                aria-label={`Filter by ${tag}`}
              >
                {tag}
              </button>
            ))}
          </div>
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

interface VideoModalProps {
  clip: Clip
  index: number
  total: number
  onClose: () => void
  onPrev: () => void
  onNext: () => void
}

function VideoModal({ clip, index, total, onClose, onPrev, onNext }: VideoModalProps) {
  // Close on Escape, navigate with arrow keys
  const navigate = useNavigate()
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
      if (e.key === 'ArrowLeft') onPrev()
      if (e.key === 'ArrowRight') onNext()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose, onPrev, onNext])

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 backdrop-blur-sm p-4"
      onClick={onClose}
    >
      {/* Modal content — stop propagation so clicks inside don't close */}
      <div
        className="relative flex flex-col items-center max-h-full"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Top bar */}
        <div className="flex items-center justify-between w-full mb-3 px-1">
          <span className="text-gray-400 text-sm">
            Short <span className="text-white font-semibold">{index + 1}</span> / {total}
          </span>
          <div className="flex items-center gap-3">
            <a
              href={`${API_BASE}${clip.file}`}
              download={`short_${index + 1}.mp4`}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-purple-600/30 hover:bg-purple-600/50 text-purple-300 text-xs rounded-lg transition"
              onClick={(e) => e.stopPropagation()}
            >
              <Download className="w-3.5 h-3.5" /> Download
            </a>
            <button
              onClick={onClose}
              className="p-1.5 rounded-full bg-white/10 hover:bg-white/20 text-white transition"
              aria-label="Close"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Video — portrait 9:16, max height 85vh */}
        <video
          src={`${API_BASE}${clip.file}`}
          className="rounded-xl max-h-[80vh] w-auto"
          style={{ aspectRatio: '9/16' }}
          controls
          autoPlay
        />

        {/* Title + Hook + Hashtags */}
        {clip.title && (
          <p className="mt-3 text-white text-sm font-semibold text-center max-w-sm">
            {clip.title}
          </p>
        )}
        {clip.hook && (
          <p className="mt-1 text-gray-300 text-sm italic text-center max-w-sm">
            &ldquo;{clip.hook}&rdquo;
          </p>
        )}
        {clip.hashtags && clip.hashtags.length > 0 && (
          <div className="flex flex-wrap justify-center gap-1.5 mt-2 max-w-sm">
            {clip.hashtags.map((tag) => (
              <button
                key={tag}
                onClick={() => navigate(`/?tag=${encodeURIComponent(tag)}`)}
                className="text-xs text-pink-400 bg-pink-500/10 border border-pink-500/20 px-2 py-0.5 rounded-full hover:bg-pink-500/15 transition cursor-pointer"
                aria-label={`Filter by ${tag}`}
              >
                {tag}
              </button>
            ))}
          </div>
        )}

        {/* Prev / Next */}
        <div className="flex items-center gap-4 mt-4">
          <button
            onClick={onPrev}
            disabled={total <= 1}
            className="px-4 py-2 bg-white/10 hover:bg-white/20 text-white text-sm rounded-lg transition disabled:opacity-30"
          >
            ← Prev
          </button>
          <button
            onClick={onNext}
            disabled={total <= 1}
            className="px-4 py-2 bg-white/10 hover:bg-white/20 text-white text-sm rounded-lg transition disabled:opacity-30"
          >
            Next →
          </button>
        </div>
      </div>
    </div>
  )
}

export default function GeneratorPage() {
  const { user, refreshUser } = useAuth()

  const [url, setUrl] = useState('')
  const [maxClips, setMaxClips] = useState(3)
  const [language, setLanguage] = useState('')
  const [subtitleStyle, setSubtitleStyle] = useState('default')
  // Onboarding banner — hidden once user has generated at least once
  const [showTip, setShowTip] = useState(() => !localStorage.getItem('has_generated'))

  // Keep maxClips within plan limits if plan changes
  const platform = getCurrentPlatform(user)
  const maxAllowed = getMaxClipsAllowed(user, platform)
  useEffect(() => {
    if (maxClips > maxAllowed) setMaxClips(maxAllowed)
  }, [maxAllowed, maxClips])
  const [status, setStatus] = useState<StatusResponse | null>(null)
  const [error, setError] = useState('')
  const [upgradeError, setUpgradeError] = useState(false)
  const [loadingCheckout] = useState(false)
  const [modalIndex, setModalIndex] = useState<number | null>(null)
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
      const res = await generatorApi.generate(url, maxClips, language, subtitleStyle)
      setStatus({ status: 'pending', progress: 0, step: 'Queued...', clips: [] })
      localStorage.setItem('has_generated', '1')
      setShowTip(false)
      startPolling(res.data.job_id)
    } catch (err) {
      const axiosErr = err as AxiosError<{ detail: string }>
      if (axiosErr.response?.status === 402) setUpgradeError(true)
      else setError(axiosErr.response?.data?.detail ?? 'An error occurred.')
    }
  }

  const handleUpgrade = async (): Promise<void> => {
    // Redirect to pricing section — user will choose their plan there
    window.location.href = '/#pricing'
  }

  const currentStep = status ? stepIndex(status.progress) : -1
  const isProcessing = status?.status === 'processing' || status?.status === 'pending'
  const currentPlan = getPlanForPlatform(user, platform)
  const generationsLeft = getGenerationsLeft(user, platform)
  const generationLimit = getGenerationLimit(user, platform)
  const quotaEmpty = generationsLeft === 0

  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      <div className="text-center mb-10">
        <h1 className="text-4xl font-bold text-white mb-3">
          <span className="bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
            AI Shorts Generator
          </span>
        </h1>
        <p className="text-gray-400">Turn any YouTube video into viral shorts</p>
        {user && (
          <div className="mt-4 inline-flex items-center gap-2 px-4 py-2 bg-white/5 border border-white/10 rounded-full text-sm">
            {generationsLeft > 0 ? (
              <span className="text-gray-300">
                <span className="text-purple-400 font-semibold">{generationsLeft}</span>
                {' / '}
                <span className="text-gray-400">
                  {generationLimit}
                </span>
                {' generation'}{generationsLeft !== 1 ? 's' : ''}{' left this month'}
              </span>
            ) : (
              <span className="text-red-400">No generations left this month</span>
            )}
          </div>
        )}
      </div>

      {upgradeError && (
        <div className="mb-6 bg-gradient-to-r from-purple-900/50 to-pink-900/50 border border-purple-500/30 rounded-2xl p-6 text-center">
          <Crown className="w-8 h-8 text-yellow-400 mx-auto mb-3" />
          <h3 className="text-white font-semibold text-lg mb-1">Limit reached</h3>
          <p className="text-gray-400 text-sm mb-4">
            You've used all {generationLimit} of your {getPlanForPlatform(user, platform)} plan generations this month.
          </p>
          <button
            onClick={() => void handleUpgrade()}
            disabled={loadingCheckout}
            className="px-6 py-2.5 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white font-semibold rounded-lg transition disabled:opacity-50"
          >
            {loadingCheckout ? 'Loading...' : 'Upgrade your plan'}
          </button>
        </div>
      )}

      <form onSubmit={(e) => void handleGenerate(e)} className="mb-8">
        {/* Onboarding tip — shown only on first visit */}
        {showTip && (
          <div className="flex items-start gap-3 mb-4 p-4 bg-purple-500/10 border border-purple-500/20 rounded-xl">
            <Lightbulb className="w-4 h-4 text-purple-400 shrink-0 mt-0.5" />
            <div className="flex-1 text-sm text-gray-300">
              <span className="font-medium text-white">How it works: </span>
              paste any YouTube URL below, choose how many clips you want, and our AI will find the best moments and cut them into 9:16 shorts ready to post.
              <button
                type="button"
                onClick={() => setUrl(EXAMPLE_URL)}
                className="ml-2 text-purple-400 hover:text-purple-300 underline underline-offset-2 transition"
              >
                Try with an example →
              </button>
            </div>
            <button
              type="button"
              onClick={() => setShowTip(false)}
              className="text-gray-600 hover:text-gray-400 transition shrink-0"
              aria-label="Dismiss"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

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
          {/* Quick example link below the field */}
          {!url && !isProcessing && (
            <button
              type="button"
              onClick={() => setUrl(EXAMPLE_URL)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-gray-500 hover:text-purple-400 transition"
            >
              Use example
            </button>
          )}
        </div>

        {/* Clip count slider */}
        <div className={`p-4 rounded-xl mb-4 ${
          currentPlan === 'proplus'  ? 'bg-pink-500/5 border border-pink-500/20'
          : currentPlan === 'pro'   ? 'bg-yellow-500/5 border border-yellow-500/20'
          : currentPlan === 'standard' ? 'bg-blue-500/5 border border-blue-500/20'
          : 'bg-white/5 border border-white/10'
        }`}>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <SlidersHorizontal className={`w-4 h-4 ${currentPlan !== 'free' ? 'text-yellow-400' : 'text-purple-400'}`} />
              <span className="text-sm font-medium text-white">Number of clips</span>
              {currentPlan === 'proplus' ? (
                <span className="px-1.5 py-0.5 bg-pink-500/20 text-pink-400 text-xs rounded-full font-semibold">PRO+ · max 20</span>
              ) : currentPlan === 'pro' ? (
                <span className="px-1.5 py-0.5 bg-yellow-500/20 text-yellow-400 text-xs rounded-full font-semibold">PRO · max 10</span>
              ) : currentPlan === 'standard' ? (
                <span className="px-1.5 py-0.5 bg-blue-500/20 text-blue-400 text-xs rounded-full font-semibold">STANDARD · max 5</span>
              ) : (
                <span className="px-1.5 py-0.5 bg-white/10 text-gray-400 text-xs rounded-full">max 3 — upgrade for more</span>
              )}
            </div>
            <span className={`text-3xl font-bold w-10 text-center ${currentPlan === 'proplus' ? 'text-pink-400' : currentPlan === 'pro' ? 'text-yellow-400' : 'text-purple-400'}`}>
              {maxClips}
            </span>
          </div>
          <input
            type="range"
            min={1}
            max={maxAllowed}
            step={1}
            value={maxClips}
            onChange={(e) => setMaxClips(Number(e.target.value))}
            disabled={isProcessing}
            className={`w-full cursor-pointer disabled:opacity-50 ${currentPlan === 'proplus' ? 'accent-pink-400' : currentPlan === 'pro' ? 'accent-yellow-400' : 'accent-purple-500'}`}
          />
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>1</span>
            {currentPlan === 'proplus' ? (
              <>
                <span>5</span>
                <span>10</span>
                <span>15</span>
                <span>20</span>
              </>
            ) : currentPlan === 'pro' ? (
              <>
                <span>3</span>
                <span>5</span>
                <span>8</span>
                <span>10</span>
              </>
            ) : currentPlan === 'standard' ? (
              <>
                <span>3</span>
                <span>5</span>
              </>
            ) : (
              <>
                <span>2</span>
                <span>3</span>
              </>
            )}
          </div>
        </div>

        {/* Language selector — Standard and above */}
        {currentPlan !== 'free' && (
          <div className={`p-4 rounded-xl mb-4 ${
            currentPlan === 'proplus'  ? 'bg-pink-500/5 border border-pink-500/20'
            : currentPlan === 'pro'   ? 'bg-yellow-500/5 border border-yellow-500/20'
                                     : 'bg-blue-500/5 border border-blue-500/20'
          }`}>
            <div className="flex items-center gap-2 mb-3">
              <Globe className={`w-4 h-4 ${
                currentPlan === 'proplus' ? 'text-pink-400'
                : currentPlan === 'pro'  ? 'text-yellow-400'
                                        : 'text-blue-400'
              }`} />
              <span className="text-sm font-medium text-white">Transcription language</span>
              {currentPlan === 'proplus' ? (
                <span className="px-1.5 py-0.5 bg-pink-500/20 text-pink-400 text-xs rounded-full font-semibold">PRO+</span>
              ) : currentPlan === 'pro' ? (
                <span className="px-1.5 py-0.5 bg-yellow-500/20 text-yellow-400 text-xs rounded-full font-semibold">PRO</span>
              ) : (
                <span className="px-1.5 py-0.5 bg-blue-500/20 text-blue-400 text-xs rounded-full font-semibold">STANDARD</span>
              )}
            </div>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              disabled={isProcessing}
              className={`w-full px-3 py-2.5 bg-black/30 rounded-lg text-white text-sm focus:outline-none transition disabled:opacity-50 cursor-pointer border ${
                user?.plan === 'proplus' ? 'border-pink-500/20 focus:border-pink-400'
                : user?.plan === 'pro'  ? 'border-yellow-500/20 focus:border-yellow-400'
                                        : 'border-blue-500/20 focus:border-blue-400'
              }`}
            >
              {LANGUAGES.map((l) => (
                <option key={l.code} value={l.code}>{l.label}</option>
              ))}
            </select>
            <p className="mt-2 text-xs text-gray-500">
              Picking the right language improves transcription accuracy significantly.
            </p>
          </div>
        )}

        {/* Subtitle style selector — Standard and above */}
        {currentPlan !== 'free' && (
          <div className={`p-4 rounded-xl mb-4 ${
            currentPlan === 'proplus'  ? 'bg-pink-500/5 border border-pink-500/20'
            : currentPlan === 'pro'   ? 'bg-yellow-500/5 border border-yellow-500/20'
                                     : 'bg-blue-500/5 border border-blue-500/20'
          }`}>
            <div className="flex items-center gap-2 mb-3">
              <Type className={`w-4 h-4 ${
                currentPlan === 'proplus' ? 'text-pink-400'
                : currentPlan === 'pro'  ? 'text-yellow-400'
                                        : 'text-blue-400'
              }`} />
              <span className="text-sm font-medium text-white">Subtitle style</span>
              {currentPlan === 'proplus' ? (
                <span className="px-1.5 py-0.5 bg-pink-500/20 text-pink-400 text-xs rounded-full font-semibold">PRO+</span>
              ) : currentPlan === 'pro' ? (
                <span className="px-1.5 py-0.5 bg-yellow-500/20 text-yellow-400 text-xs rounded-full font-semibold">PRO</span>
              ) : (
                <span className="px-1.5 py-0.5 bg-blue-500/20 text-blue-400 text-xs rounded-full font-semibold">STANDARD</span>
              )}
            </div>
            <div className="grid grid-cols-5 gap-2">
              {SUBTITLE_STYLES.map((s) => (
                <button
                  key={s.code}
                  type="button"
                  disabled={isProcessing}
                  onClick={() => setSubtitleStyle(s.code)}
                  title={s.desc}
                  className={`px-2 py-2 rounded-lg text-xs font-medium border transition text-center disabled:opacity-50 disabled:cursor-not-allowed ${
                    subtitleStyle === s.code
                      ? currentPlan === 'proplus' ? 'bg-pink-500/20 border-pink-400 text-pink-300'
                        : currentPlan === 'pro'   ? 'bg-yellow-500/20 border-yellow-400 text-yellow-300'
                                                 : 'bg-blue-500/20 border-blue-400 text-blue-300'
                      : currentPlan === 'proplus' ? 'bg-black/20 border-white/10 text-gray-400 hover:border-pink-500/40 hover:text-white'
                        : currentPlan === 'pro'   ? 'bg-black/20 border-white/10 text-gray-400 hover:border-yellow-500/40 hover:text-white'
                                                 : 'bg-black/20 border-white/10 text-gray-400 hover:border-blue-500/40 hover:text-white'
                  }`}
                >
                  {s.label}
                </button>
              ))}
            </div>
            <p className="mt-2 text-xs text-gray-500">
              {SUBTITLE_STYLES.find((s) => s.code === subtitleStyle)?.desc}
            </p>
          </div>
        )}

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
              onClick={async () => {
                // Fetch each clip as a blob and trigger download via object URL.
                // This avoids navigation when download attribute isn't honored (cross-origin or browser quirks).
                for (let i = 0; i < status.clips.length; i++) {
                  const c = status.clips[i]
                  try {
                    const res = await fetch(`${API_BASE}${c.file}`, { credentials: 'include' })
                    if (!res.ok) throw new Error(`Fetch failed: ${res.status}`)
                    const blob = await res.blob()
                    const url = URL.createObjectURL(blob)
                    const a = document.createElement('a')
                    a.href = url
                    a.setAttribute('download', `short_${i + 1}.mp4`)
                    a.style.display = 'none'
                    document.body.appendChild(a)
                    a.click()
                    document.body.removeChild(a)
                    URL.revokeObjectURL(url)
                  } catch (err) {
                    // Fallback: try simple anchor navigation (may open in new tab)
                    const a = document.createElement('a')
                    a.href = `${API_BASE}${c.file}`
                    a.setAttribute('download', `short_${i + 1}.mp4`)
                    a.style.display = 'none'
                    document.body.appendChild(a)
                    a.click()
                    document.body.removeChild(a)
                  }
                  // slight pause to avoid overwhelming browser/network
                  await new Promise((r) => setTimeout(r, 300))
                }
              }}
              className="flex items-center gap-2 px-4 py-2 bg-white/10 hover:bg-white/20 text-white text-sm rounded-lg transition"
            >
              <Download className="w-4 h-4" /> Download all
            </button>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {status.clips.map((clip, i) => (
              <ClipCard
                key={clip.file}
                clip={clip}
                index={i}
                onExpand={(_, idx) => setModalIndex(idx)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Fullscreen video modal */}
      {modalIndex !== null && status?.clips[modalIndex] && (
        <VideoModal
          clip={status.clips[modalIndex]}
          index={modalIndex}
          total={status.clips.length}
          onClose={() => setModalIndex(null)}
          onPrev={() => setModalIndex((i) => ((i ?? 0) - 1 + status.clips.length) % status.clips.length)}
          onNext={() => setModalIndex((i) => ((i ?? 0) + 1) % status.clips.length)}
        />
      )}
    </div>
  )
}
