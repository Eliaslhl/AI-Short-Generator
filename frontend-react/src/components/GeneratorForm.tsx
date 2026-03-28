/**
 * GeneratorForm.tsx
 * Shared form component for both YouTube and Twitch generation.
 * Handles URL input, clip count, language, subtitle style, and generation logic.
 */

import { useState, useRef, useEffect, type FormEvent } from 'react'
import { Link2, Sparkles, AlertCircle, Globe, Type } from 'lucide-react'

// Language options
export const LANGUAGES = [
  { code: '', label: '🌐 Auto-detect' },
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

export const SUBTITLE_STYLES = [
  { code: 'default', label: '🟡 Classic', desc: 'Yellow bold — TikTok style' },
  { code: 'bold', label: '⚪ Bold White', desc: 'White bold with strong outline' },
  { code: 'outlined', label: '🔵 Outlined', desc: 'White with blue stroke' },
  { code: 'neon', label: '💚 Neon', desc: 'Neon green glow effect' },
  { code: 'minimal', label: '◻️ Minimal', desc: 'Clean white, no stroke' },
]

export interface GeneratorFormProps {
  source: 'youtube' | 'twitch'
  placeholderUrl: string
  exampleUrl: string
  onGenerate: (request: GenerateFormRequest) => Promise<void>
  isLoading?: boolean
  error?: string
  maxClips?: number
  currentPlan?: string
}

export interface GenerateFormRequest {
  url: string
  maxClips: number
  language: string
  subtitleStyle: string
  includeSubtitles: boolean
}

export function GeneratorForm({
  source,
  placeholderUrl,
  exampleUrl,
  onGenerate,
  isLoading = false,
  error = '',
  maxClips: initialMaxClips = 3,
  currentPlan = 'free'
}: GeneratorFormProps) {
  const [url, setUrl] = useState('')
  const [maxClips, setMaxClips] = useState(initialMaxClips)
  const [language, setLanguage] = useState('')
  const [subtitleStyle, setSubtitleStyle] = useState('default')
  const [includeSubtitles, setIncludeSubtitles] = useState(true)
  const urlRef = useRef<HTMLInputElement>(null)

  // Plan-based limits
  const maxAllowed = {
    'proplus': 20,
    'pro': 10,
    'standard': 5,
    'free': 3
  }[currentPlan] ?? 3

  useEffect(() => {
    if (maxClips > maxAllowed) {
      setMaxClips(maxAllowed)
    }
  }, [maxAllowed, maxClips])

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    if (!url.trim()) {
      urlRef.current?.focus()
      return
    }

    try {
      await onGenerate({
        url: url.trim(),
        maxClips,
        language,
        subtitleStyle,
        includeSubtitles
      })
    } catch (err) {
      // Error handling is done by parent component
    }
  }

  const planBadgeColor = {
    'proplus': 'from-pink-500 to-purple-600',
    'pro': 'from-yellow-500 to-orange-500',
    'standard': 'from-blue-500 to-cyan-500',
    'free': 'from-gray-500 to-gray-600'
  }[currentPlan] ?? 'from-gray-500 to-gray-600'

  return (
    <form onSubmit={handleSubmit} className="max-w-3xl mx-auto space-y-6">
      {/* URL Input */}
      <div className="relative">
        <label className="block text-sm font-medium text-gray-200 mb-2">
          <Link2 className="inline mr-2" size={16} />
          {source === 'youtube' ? 'YouTube' : 'Twitch'} URL
        </label>
        <input
          ref={urlRef}
          type="text"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder={placeholderUrl}
          className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:border-purple-500 focus:ring-2 focus:ring-purple-500/30 transition"
          disabled={isLoading}
        />
        <button
          type="button"
          onClick={() => setUrl(exampleUrl)}
          className="absolute right-3 top-10 text-xs text-gray-400 hover:text-gray-200 transition"
        >
          Use example
        </button>
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 flex gap-2">
          <AlertCircle size={18} className="text-red-400 flex-shrink-0 mt-0.5" />
          <p className="text-red-300 text-sm">{error}</p>
        </div>
      )}

      {/* Main Options */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Max Clips */}
        <div>
          <label className="block text-sm font-medium text-gray-200 mb-2">
            <Sparkles className="inline mr-2" size={16} />
            Clips to Generate
          </label>
          <input
            type="range"
            min={1}
            max={maxAllowed}
            value={maxClips}
            onChange={(e) => setMaxClips(parseInt(e.target.value))}
            disabled={isLoading}
            className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
          />
          <div className="text-xs text-gray-400 mt-1">
            {maxClips} / {maxAllowed} {currentPlan !== 'free' && <span className="ml-2 text-xs text-gray-500">(Plan limit)</span>}
          </div>
        </div>

        {/* Language */}
        <div>
          <label className="block text-sm font-medium text-gray-200 mb-2">
            <Globe className="inline mr-2" size={16} />
            Language
          </label>
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            disabled={isLoading}
            className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm focus:border-purple-500 focus:ring-2 focus:ring-purple-500/30 transition"
          >
            {LANGUAGES.map((lang) => (
              <option key={lang.code} value={lang.code}>
                {lang.label}
              </option>
            ))}
          </select>
        </div>

        {/* Subtitle Style */}
        <div>
          <label className="block text-sm font-medium text-gray-200 mb-2">
            <Type className="inline mr-2" size={16} />
            Subtitle Style
          </label>
          <select
            value={subtitleStyle}
            onChange={(e) => setSubtitleStyle(e.target.value)}
            disabled={isLoading}
            className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm focus:border-purple-500 focus:ring-2 focus:ring-purple-500/30 transition"
          >
            {SUBTITLE_STYLES.map((style) => (
              <option key={style.code} value={style.code}>
                {style.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Subtitle Toggle */}
      <div className="bg-gray-800/30 border border-gray-700 rounded-lg p-4">
        <label className="flex items-center cursor-pointer group">
          <input
            type="checkbox"
            checked={includeSubtitles}
            onChange={(e) => setIncludeSubtitles(e.target.checked)}
            disabled={isLoading}
            className="w-4 h-4 rounded border-gray-600 text-purple-600 focus:ring-purple-500 cursor-pointer"
          />
          <span className="ml-3 text-gray-200 group-hover:text-white transition">
            Include Subtitles
          </span>
          <span className="text-xs text-gray-500 ml-2">
            {currentPlan === 'free' ? '(Free feature)' : '(Available on your plan)'}
          </span>
        </label>
      </div>

      {/* Generate Button */}
      <button
        type="submit"
        disabled={isLoading || !url.trim()}
        className={`w-full py-3 px-4 rounded-lg font-semibold transition-all flex items-center justify-center gap-2 ${
          isLoading || !url.trim()
            ? 'bg-gray-700 text-gray-400 cursor-not-allowed'
            : 'bg-gradient-to-r from-purple-600 to-pink-600 text-white hover:from-purple-700 hover:to-pink-700 hover:shadow-lg'
        }`}
      >
        {isLoading ? (
          <>
            <div className="w-4 h-4 border-2 border-gray-400 border-t-white rounded-full animate-spin" />
            Processing...
          </>
        ) : (
          <>
            <Sparkles size={18} />
            Generate Shorts
          </>
        )}
      </button>

      {/* Plan Info */}
      <div className="text-xs text-gray-500 text-center">
        <span className={`inline-block px-2 py-1 rounded bg-gradient-to-r ${planBadgeColor} text-white text-xs font-semibold`}>
          {currentPlan.toUpperCase()}
        </span>
        <span className="ml-2">
          {currentPlan === 'free' ? 'Upgrade to generate more clips' : 'Thanks for supporting us!'}
        </span>
      </div>
    </form>
  )
}
