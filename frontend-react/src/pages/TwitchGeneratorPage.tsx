import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { generatorApi } from '../api'
import type { StatusResponse, Clip } from '../types'
import { LANGUAGES, SUBTITLE_STYLES } from '../components/GeneratorForm'
import TwitchVodPickerModal from '../components/TwitchVodPickerModal'
import { Download, Expand, X, Link2, SlidersHorizontal, Globe, Type, Sparkles, Tv } from 'lucide-react'

import { getPlanForPlatform } from '../utils/planUtils'

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

interface ClipCardProps {
  clip: Clip
  index: number
  onExpand: (clip: Clip, index: number) => void
}

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
  const downloadRef = useRef<HTMLAnchorElement>(null)

  const handleDownload = () => {
    downloadRef.current?.click()
  }

  return (
    <div className="fixed inset-0 bg-black/95 flex items-center justify-center z-50 p-4 backdrop-blur-sm" onClick={onClose}>
      <div className="max-w-3xl w-full" onClick={(e) => e.stopPropagation()}>
        <div className="bg-slate-950 rounded-2xl overflow-hidden border border-white/10">
          {/* Header */}
          <div className="flex justify-between items-start p-4 border-b border-white/10">
            <div className="flex-1">
              <h2 className="text-lg font-bold text-white mb-1">{clip.title || `Short ${index + 1}`}</h2>
              <p className="text-xs text-gray-400">{clip.duration?.toFixed(1)}s • Viral Score: {clip.viral_score}</p>
            </div>
            <button onClick={onClose} className="hover:bg-white/10 p-2 rounded-lg transition">
              <X size={20} className="text-white" />
            </button>
          </div>

          {/* Video — desktop-friendly frame with blurred fill + sharp portrait center */}
          <div className="relative w-full aspect-video bg-black overflow-hidden">
            <video
              src={`${API_BASE}${clip.file}`}
              className="absolute inset-0 w-full h-full object-cover blur-2xl scale-110 opacity-55"
              aria-hidden="true"
              muted
              playsInline
              preload="metadata"
            />
            <div className="absolute inset-0 bg-black/35" />
            <video
              src={`${API_BASE}${clip.file}`}
              className="relative z-10 h-full max-h-[70vh] mx-auto object-contain"
              controls
              autoPlay
              playsInline
              style={{ aspectRatio: '9/16' }}
            />
          </div>

          {/* Footer */}
          <div className="p-4 border-t border-white/10 space-y-3">
            {/* Hashtags */}
            {clip.hashtags && clip.hashtags.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {clip.hashtags.map((tag) => (
                  <span key={tag} className="text-[11px] text-pink-400 bg-pink-500/10 px-2 py-1 rounded-full">
                    {tag}
                  </span>
                ))}
              </div>
            )}

            {/* Actions */}
            <div className="flex items-center gap-2">
              <button
                onClick={onPrev}
                disabled={total <= 1}
                className="px-4 py-2 bg-white/10 hover:bg-white/20 text-white text-sm rounded-lg transition disabled:opacity-30"
              >
                ← Prev
              </button>
              <button
                onClick={handleDownload}
                className="px-4 py-2 bg-gradient-to-r from-purple-600 to-pink-600 text-white text-sm rounded-lg transition hover:shadow-lg flex items-center gap-2 flex-1 justify-center"
              >
                <Download size={16} />
                Download
              </button>
              <a
                ref={downloadRef}
                href={`${API_BASE}${clip.file}`}
                download={clip.title || `short-${index + 1}.mp4`}
                style={{ display: 'none' }}
              />
              <button
                onClick={onNext}
                disabled={total <= 1}
                className="px-4 py-2 bg-white/10 hover:bg-white/20 text-white text-sm rounded-lg transition disabled:opacity-30"
              >
                Next →
              </button>
            </div>

            <p className="text-center text-xs text-gray-500">
              {index + 1} / {total}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function TwitchGeneratorPage() {
  const { user, refreshUser } = useAuth()
  const navigate = useNavigate()

  const [url, setUrl] = useState('')
  const [maxClips, setMaxClips] = useState(3)
  const [language, setLanguage] = useState('')
  const [subtitleStyle, setSubtitleStyle] = useState('default')
  const [includeSubtitles, setIncludeSubtitles] = useState(true)

  const [status, setStatus] = useState<StatusResponse | null>(null)
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [preview, setPreview] = useState<{ url: string; title?: string; duration?: number; thumbnail?: string } | null>(null)
  const [isPreviewLoading, setIsPreviewLoading] = useState(false)
  const [isVodPickerOpen, setIsVodPickerOpen] = useState(false)
  const [modalIndex, setModalIndex] = useState<number | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const previewTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Max clips by plan (corrigé)
  const currentPlan = getPlanForPlatform(user, 'twitch')
  const maxAllowed = currentPlan === 'proplus' ? 20 : currentPlan === 'pro' ? 10 : currentPlan === 'standard' ? 5 : 3

  // Cleanup interval on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
      if (previewTimerRef.current) clearTimeout(previewTimerRef.current)
    }
  }, [])

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!url.trim()) return

    setError('')
    setStatus(null)
    setIsLoading(true)
    setModalIndex(null)

    try {
      const response = await generatorApi.generate(
        url,
        maxClips,
        language,
        subtitleStyle,
        includeSubtitles
      )
      await refreshUser()

      const jobId = response.data.job_id
      localStorage.setItem('has_generated', 'true')

      // Start polling
      let attempts = 0
      const poll = async () => {
        try {
          const statusRes = await generatorApi.status(jobId)
          setStatus(statusRes.data)

          if (statusRes.data.status === 'done' || statusRes.data.status === 'error') {
            if (pollRef.current) clearInterval(pollRef.current)
            await refreshUser()
          }
        } catch {
          attempts++
          if (attempts > 10) {
            if (pollRef.current) clearInterval(pollRef.current)
          }
        }
      }

      await poll()
      pollRef.current = setInterval(poll, 1000)
    } catch (err: any) {
      const msg =
        err?.response?.data?.detail ||
        err?.message ||
        'Generation failed'
      setError(msg)
    }
  }

  const handlePreview = async () => {
    if (!url.trim()) return
    try {
      setIsPreviewLoading(true)
      setPreview(null)
      const res = await generatorApi.preview(url.trim())
      setPreview(res.data)
    } catch (err: any) {
      // don't block generation on preview failure; show a small non-blocking message
      console.debug('Preview failed', err?.response?.data?.detail || err?.message)
    }
    finally {
      setIsPreviewLoading(false)
    }
  }

  // Debounced auto-preview: trigger when the user stops typing for 700ms.
  useEffect(() => {
    // basic early exits
    if (!url.trim() || isLoading) return

    const v = url.trim()
    const looksLikeSource = v.includes('twitch.tv') || v.includes('youtube.com') || v.includes('youtu.be')
    if (!looksLikeSource) {
      setPreview(null)
      return
    }

    if (previewTimerRef.current) {
      clearTimeout(previewTimerRef.current)
    }
    previewTimerRef.current = setTimeout(() => {
      void handlePreview()
      previewTimerRef.current = null
    }, 700)

    return () => {
      if (previewTimerRef.current) {
        clearTimeout(previewTimerRef.current)
        previewTimerRef.current = null
      }
    }
  }, [url, isLoading])

  const clips = status?.clips || []
  const currentStep = stepIndex(status?.progress ?? 0)
  const isComplete = status?.status === 'done'

  // Plan colors (corrigé)
  const planColor = 
    currentPlan === 'proplus' ? { bg: 'bg-pink-500/5', border: 'border-pink-500/20', text: 'text-pink-400', icon: 'text-pink-400', select: 'border-pink-500/20 focus:border-pink-400', accent: 'accent-pink-400' }
    : currentPlan === 'pro' ? { bg: 'bg-yellow-500/5', border: 'border-yellow-500/20', text: 'text-yellow-400', icon: 'text-yellow-400', select: 'border-yellow-500/20 focus:border-yellow-400', accent: 'accent-yellow-400' }
    : currentPlan === 'standard' ? { bg: 'bg-blue-500/5', border: 'border-blue-500/20', text: 'text-blue-400', icon: 'text-blue-400', select: 'border-blue-500/20 focus:border-blue-400', accent: 'accent-blue-400' }
    : { bg: 'bg-white/5', border: 'border-white/10', text: 'text-purple-400', icon: 'text-purple-400', select: 'border-white/10 focus:border-purple-500', accent: 'accent-purple-500' }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 text-white py-12">
      <div className="w-4/5 mx-auto px-4">
        {/* Back button */}
        <button
          onClick={() => navigate('/generate')}
          className="mb-8 text-gray-400 hover:text-white transition flex items-center gap-1 text-sm"
        >
          ← Back
        </button>

        {/* Header */}
        <div className="mb-12 text-center">
          <h1 className="text-4xl font-bold mb-2 bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
            Twitch Shorts Generator
          </h1>
          <p className="text-gray-300">Transform your Twitch clips and VODs into viral short-form content</p>
        </div>

        {/* Form */}
        <form onSubmit={handleGenerate} className="space-y-6 mb-12">
          {/* URL input */}
          <div className="relative">
            <Link2 className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onBlur={() => void handlePreview()}
              placeholder="https://www.twitch.tv/videos/..."
              required
              disabled={isLoading}
              className="w-full pl-12 pr-4 py-3.5 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 transition"
            />
          </div>

          {/* Browse VODs button */}
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setIsVodPickerOpen(true)}
              disabled={isLoading}
              className="px-4 py-3.5 bg-white/5 border border-white/10 text-white rounded-xl hover:bg-white/10 transition disabled:opacity-50 flex items-center gap-2 justify-center"
            >
              <Tv className="w-5 h-5" />
              Browse VODs
            </button>
          </div>

          {/* URL preview (title / thumbnail) */}
          <div className="mt-3">
            {isPreviewLoading ? (
              <div className="p-3 rounded-xl bg-white/3 border border-white/10 flex items-center gap-3 animate-pulse">
                <div className="w-28 h-16 bg-white/6 rounded-md" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-white/6 rounded w-3/4" />
                  <div className="h-3 bg-white/6 rounded w-1/4" />
                </div>
              </div>
            ) : preview ? (
              <div className="p-3 rounded-xl bg-white/3 border border-white/10 flex items-center gap-3">
                {preview.thumbnail ? (
                  // eslint-disable-next-line jsx-a11y/img-redundant-alt
                  <img src={preview.thumbnail} alt="thumbnail" className="w-28 h-16 object-cover rounded-md" />
                ) : (
                  <div className="w-28 h-16 bg-white/5 rounded-md flex items-center justify-center text-xs text-gray-400">No preview</div>
                )}
                <div className="flex-1">
                  <p className="text-sm font-semibold truncate">{preview.title || 'Untitled'}</p>
                  {preview.duration != null && (
                    <p className="text-xs text-gray-300">Duration: {preview.duration?.toFixed(1)}s</p>
                  )}
                </div>
              </div>
            ) : null}
          </div>

          {/* Number of clips */}
          <div className={`p-4 rounded-xl border ${planColor.bg} ${planColor.border}`}>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <SlidersHorizontal className={`w-4 h-4 ${planColor.icon}`} />
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
              <span className={`text-3xl font-bold w-10 text-center ${planColor.text}`}>
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
              disabled={isLoading}
              className={`w-full cursor-pointer disabled:opacity-50 ${planColor.accent}`}
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              {Array.from({ length: maxAllowed }, (_, i) => {
                if (i === 0 || i === maxAllowed - 1 || (maxAllowed > 4 && (i + 1) % Math.ceil(maxAllowed / 4) === 0)) {
                  return <span key={i}>{i + 1}</span>
                }
                return <span key={i}></span>
              })}
            </div>
          </div>

          {/* Language selector — Standard and above */}
          {currentPlan !== 'free' && (
            <div className={`p-4 rounded-xl border ${planColor.bg} ${planColor.border}`}>
              <div className="flex items-center gap-2 mb-3">
                <Globe className={`w-4 h-4 ${planColor.icon}`} />
                <span className="text-sm font-medium text-white">Transcription language</span>
                <span className={
                  currentPlan === 'proplus'
                    ? 'px-1.5 py-0.5 bg-pink-500/20 text-pink-400 text-xs rounded-full font-semibold'
                    : currentPlan === 'pro'
                    ? 'px-1.5 py-0.5 bg-yellow-500/20 text-yellow-400 text-xs rounded-full font-semibold'
                    : 'px-1.5 py-0.5 bg-blue-500/20 text-blue-400 text-xs rounded-full font-semibold'
                }>
                  {currentPlan.toUpperCase()}
                </span>
              </div>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                disabled={isLoading}
                className={`w-full px-3 py-2.5 bg-black/30 rounded-lg text-white text-sm focus:outline-none transition disabled:opacity-50 cursor-pointer border ${planColor.select}`}
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
            <div className={`p-4 rounded-xl border ${planColor.bg} ${planColor.border}`}>
              <div className="flex items-center gap-2 mb-3">
                <Type className={`w-4 h-4 ${planColor.icon}`} />
                <span className="text-sm font-medium text-white">Subtitle style</span>
                <span className={
                  currentPlan === 'proplus'
                    ? 'px-1.5 py-0.5 bg-pink-500/20 text-pink-400 text-xs rounded-full font-semibold'
                    : currentPlan === 'pro'
                    ? 'px-1.5 py-0.5 bg-yellow-500/20 text-yellow-400 text-xs rounded-full font-semibold'
                    : 'px-1.5 py-0.5 bg-blue-500/20 text-blue-400 text-xs rounded-full font-semibold'
                }>
                  {currentPlan.toUpperCase()}
                </span>
              </div>
              <div className="grid grid-cols-5 gap-2">
                {SUBTITLE_STYLES.map((s) => (
                  <button
                    key={s.code}
                    type="button"
                    disabled={isLoading}
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

          {/* Include Subtitles Toggle */}
          <div className="p-4 rounded-xl mb-4 bg-slate-800/50 border border-slate-700/50">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="include-subtitles"
                  checked={includeSubtitles}
                  onChange={(e) => setIncludeSubtitles(e.target.checked)}
                  disabled={isLoading}
                  className="w-4 h-4 rounded accent-purple-600 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                />
                <label htmlFor="include-subtitles" className="text-sm font-medium text-white cursor-pointer hover:text-gray-200 transition disabled:opacity-50 disabled:cursor-not-allowed flex-1">
                  Include Subtitles
                </label>
              </div>
              <span className={`text-xs px-2 py-1 rounded-full font-medium ${
                includeSubtitles 
                  ? 'bg-green-500/20 text-green-400' 
                  : 'bg-gray-500/20 text-gray-400'
              }`}>
                {includeSubtitles ? 'ON' : 'OFF'}
              </span>
            </div>
            <p className="mt-2 text-xs text-gray-500">
              {includeSubtitles 
                ? '✓ Captions and emojis will be added to your shorts (slower, larger files)'
                : '✗ No captions or emojis (faster processing, smaller files)'}
            </p>
          </div>

          {/* Error message */}
          {error && (
            <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 text-sm text-red-300">
              {error}
            </div>
          )}

          {/* Submit button */}
          <button
            type="submit"
            disabled={isLoading || !url.trim()}
            className="w-full py-3.5 bg-gradient-to-r from-purple-600 to-pink-600 text-white font-semibold rounded-xl hover:shadow-lg hover:shadow-purple-500/20 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            <Sparkles className="w-5 h-5" />
            {isLoading ? 'Generating...' : 'Generate Shorts'}
          </button>
        </form>

        {/* Progress Section */}
        {status && (
          <div className="space-y-6 mb-12">
            {/* Status Header */}
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-bold">
                {isComplete ? '✅ Complete!' : status.status === 'error' ? '❌ Failed' : '⏳ Processing...'}
              </h2>
              <span className="text-3xl font-bold text-purple-400">{status.progress}%</span>
            </div>

            {/* Progress Bar */}
            <div className="w-full bg-white/5 rounded-full h-2 overflow-hidden border border-white/10">
              <div
                className="h-full bg-gradient-to-r from-purple-500 to-pink-500 transition-all duration-300"
                style={{ width: `${status.progress}%` }}
              />
            </div>

            {/* Steps */}
            <div className="grid grid-cols-4 gap-3">
              {STEPS.map((step, idx) => {
                const isDone = currentStep > idx
                const isCurrent = currentStep === idx
                return (
                  <div
                    key={step.key}
                    className={`p-3 rounded-lg text-center text-xs font-semibold transition ${
                      isDone || isCurrent
                        ? 'bg-purple-500/20 border border-purple-500 text-purple-200'
                        : 'bg-white/5 border border-white/10 text-gray-400'
                    }`}
                  >
                    {step.label}
                  </div>
                )
              })}
            </div>

            {/* Current Step */}
            {status.step && (
              <p className="text-center text-gray-300 text-sm">
                {status.step}
              </p>
            )}
          </div>
        )}

        {/* Clips Grid */}
        {clips.length > 0 && (
          <div className="space-y-4">
            <h2 className="text-2xl font-bold">Generated Shorts ({clips.length})</h2>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {clips.map((clip, idx) => (
                <ClipCard
                  key={idx}
                  clip={clip}
                  index={idx}
                  onExpand={() => setModalIndex(idx)}
                />
              ))}
            </div>
          </div>
        )}

        {/* Video Modal */}
        {modalIndex !== null && clips[modalIndex] && (
          <VideoModal
            clip={clips[modalIndex]}
            index={modalIndex}
            total={clips.length}
            onClose={() => setModalIndex(null)}
            onPrev={() => setModalIndex(Math.max(0, modalIndex - 1))}
            onNext={() => setModalIndex(Math.min(clips.length - 1, modalIndex + 1))}
          />
        )}

        {/* Twitch VOD Picker Modal */}
        <TwitchVodPickerModal
          isOpen={isVodPickerOpen}
          onClose={() => setIsVodPickerOpen(false)}
          onSelect={(vodUrl, vodTitle) => {
            setUrl(vodUrl)
            setStatus(null)
            setError('')
          }}
          isLoading={isLoading}
        />
      </div>
    </div>
  )
}
