import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Film, Zap, Clock, Download, Star, ArrowRight, CheckCircle, Crown, Sparkles, Rocket } from '../components/icons'
import { useAuth } from '../context/AuthContext'
import { authApi } from '../api'

const features = [
  {
    icon: <Zap className="w-6 h-6 text-purple-400" />,
    title: 'AI-Powered Clipping',
    desc: 'Our AI detects the most engaging moments in any YouTube video automatically.',
  },
  {
    icon: <Clock className="w-6 h-6 text-pink-400" />,
    title: 'Seconds, Not Hours',
    desc: 'Generate viral-ready short clips in minutes — no video editing skills needed.',
  },
  {
    icon: <Download className="w-6 h-6 text-blue-400" />,
    title: 'Download & Share',
    desc: 'Export your clips in portrait format, ready for TikTok, Instagram Reels, and YouTube Shorts.',
  },
]

// ── Pricing plans ────────────────────────────────────────────────────────────
const PLANS_BY_PLATFORM = {
  youtube: [
    {
      key: 'free',
      name: 'Free',
      icon: null as null,
      monthlyEur: 0,
      yearlyEur: 0,
      yearlyTotal: 0,
      style: 'default' as const,
      badge: null as null,
      features: [
        '1 video / month',
        '3 shorts per video',
        'Export 1080p',
        'Auto captions',
        'Watermark on exports',
      ],
      cta: 'Get started free',
      ctaHref: '/register' as string | null,
    },
    {
      key: 'standard',
      name: 'Standard',
      icon: 'sparkles' as const,
      monthlyEur: 4.99,
      yearlyEur: +(44.99 / 12).toFixed(2),
      yearlyTotal: 44.99,
      style: 'default' as const,
      badge: null as null,
      features: [
        '20 videos / month',
        '5 shorts per video',
        'Export 1080p',
        'Automatic subtitles',
        'Hook generator',
        'Emoji captions',
      ],
      cta: 'Start Standard',
      ctaHref: null as string | null,
    },
    {
      key: 'pro',
      name: 'Pro',
      icon: 'crown' as const,
      monthlyEur: 19.99,
      yearlyEur: +(179 / 12).toFixed(2),
      yearlyTotal: 179,
      style: 'pro' as const,
      badge: '⭐ MOST POPULAR' as string | null,
      features: [
        '50 videos / month',
        '10 shorts per video',
        'Auto zoom speaker',
        'Smart subtitles',
        'Batch processing',
        'Fast export',
      ],
      cta: 'Start Pro',
      ctaHref: null as string | null,
    },
    {
      key: 'proplus',
      name: 'Pro+',
      icon: 'rocket' as const,
      monthlyEur: 39.99,
      yearlyEur: +(359 / 12).toFixed(2),
      yearlyTotal: 359,
      style: 'proplus' as const,
      badge: null as null,
      features: [
        '100 videos / month',
        '20 shorts per video',
        'Auto title generator',
        'Auto hashtags',
        'Priority rendering (coming soon)',
        'Multi-channel support (coming soon)',
        'Team access (coming soon)',
      ],
      cta: 'Start Pro+',
      ctaHref: null as string | null,
    },
  ],
  twitch: [
    {
      key: 'free',
      name: 'Free',
      icon: null as null,
      monthlyEur: 0,
      yearlyEur: 0,
      yearlyTotal: 0,
      style: 'default' as const,
      badge: null as null,
      features: [
        '1 VOD / month',
        '3 clips per VOD',
        'Export 1080p',
        'Auto captions',
        'Watermark on exports',
      ],
      cta: 'Get started free',
      ctaHref: '/register' as string | null,
    },
    {
      key: 'standard',
      name: 'Standard',
      icon: 'sparkles' as const,
      monthlyEur: 9.99,
      yearlyEur: +(89.99 / 12).toFixed(2),
      yearlyTotal: 89.99,
      style: 'default' as const,
      badge: null as null,
      features: [
        '50 VODs / month',
        '5 clips per VOD',
        'Export 1080p',
        'Automatic subtitles',
        'Trending highlight detection',
      ],
      cta: 'Start Standard',
      ctaHref: null as string | null,
    },
    {
      key: 'pro',
      name: 'Pro',
      icon: 'crown' as const,
      monthlyEur: 34.99,
      yearlyEur: +(314.99 / 12).toFixed(2),
      yearlyTotal: 314.99,
      style: 'pro' as const,
      badge: '⭐ MOST POPULAR' as string | null,
      features: [
        '200 VODs / month',
        '10 clips per VOD',
        'Auto zoom streamer',
        'Smart subtitle styling',
        'Batch clip generation',
        'Chatter detection',
      ],
      cta: 'Start Pro',
      ctaHref: null as string | null,
    },
  ],
  combo: [
    {
      key: 'combo_pro',
      name: 'Combo Pro',
      icon: 'crown' as const,
      monthlyEur: 44.99,
      yearlyEur: +(404.99 / 12).toFixed(2),
      yearlyTotal: 404.99,
      style: 'pro' as const,
      badge: '⚡ BEST VALUE' as string | null,
      features: [
        '50 YouTube videos / month',
        '10 YouTube shorts per video',
        '200 Twitch VODs / month',
        '10 Twitch clips per VOD',
        'All YouTube Pro features',
        'All Twitch Pro features',
        'Priority processing',
      ],
      cta: 'Start Combo Pro',
      ctaHref: null as string | null,
    },
  ],
}

// Stripe Price IDs (monthly + yearly) — must match your Stripe dashboard
const PRICE_IDS_YOUTUBE = {
  standard: { monthly: 'price_1T9TOzEjLhnJfUeo7r6bk5H3', yearly: 'price_1T9TOzEjLhnJfUeoOd4Q6vIw' },
  pro:      { monthly: 'price_1T9TPOEjLhnJfUeo8wr3XuPa', yearly: 'price_1T9TPxEjLhnJfUeoHQmyDdNT' },
  proplus:  { monthly: 'price_1T9TQsEjLhnJfUeohPBAd8wD', yearly: 'price_1T9TREEjLhnJfUeoY8RkeQqG' },
} as const

const PRICE_IDS_TWITCH = {
  standard: { monthly: import.meta.env.REACT_APP_STRIPE_TWITCH_STANDARD_MONTHLY || '', yearly: import.meta.env.REACT_APP_STRIPE_TWITCH_STANDARD_YEARLY || '' },
  pro:      { monthly: import.meta.env.REACT_APP_STRIPE_TWITCH_PRO_MONTHLY || '', yearly: import.meta.env.REACT_APP_STRIPE_TWITCH_PRO_YEARLY || '' },
} as const

const PRICE_IDS_COMBO = {
  combo_pro: { monthly: import.meta.env.REACT_APP_STRIPE_COMBO_PRO_MONTHLY || '', yearly: import.meta.env.REACT_APP_STRIPE_COMBO_PRO_YEARLY || '' },
} as const

type PlanIcon = typeof PLANS_BY_PLATFORM.youtube[number]['icon']
function PlanIcon({ icon }: { icon: PlanIcon }) {
  if (icon === 'crown')    return <Crown className="w-4 h-4 text-yellow-400" />
  if (icon === 'sparkles') return <Sparkles className="w-4 h-4 text-blue-400" />
  if (icon === 'rocket')   return <Rocket className="w-4 h-4 text-pink-400" />
  return null
}

export default function LandingPage() {
  const { user } = useAuth()
  const [billing, setBilling] = useState<'monthly' | 'yearly'>('monthly')
  const [platform, setPlatform] = useState<'youtube' | 'twitch' | 'combo'>('youtube')
  const [loadingKey, setLoadingKey] = useState<string | null>(null)

  const handleUpgrade = async (planKey: string) => {
    if (!user) { window.location.href = '/register'; return }
    setLoadingKey(planKey)
    try {
      let priceId = ''
      if (platform === 'youtube') {
        const priceIds = PRICE_IDS_YOUTUBE[planKey as keyof typeof PRICE_IDS_YOUTUBE]
        priceId = billing === 'yearly' ? priceIds.yearly : priceIds.monthly
      } else if (platform === 'twitch') {
        const priceIds = PRICE_IDS_TWITCH[planKey as keyof typeof PRICE_IDS_TWITCH]
        priceId = billing === 'yearly' ? priceIds.yearly : priceIds.monthly
      } else if (platform === 'combo') {
        const priceIds = PRICE_IDS_COMBO[planKey as keyof typeof PRICE_IDS_COMBO]
        priceId = billing === 'yearly' ? priceIds.yearly : priceIds.monthly
      }
      if (!priceId) { 
        alert('Price ID not configured for this plan. Contact support.')
        window.location.href = '/#pricing'
        setLoadingKey(null)
        return 
      }
      const res = await authApi.createCheckout(priceId)
      window.location.href = res.data.checkout_url
    } catch {
      window.location.href = '/#pricing'
      setLoadingKey(null)
    }
  }

  const currentPlan = user?.plan ?? 'free'

  return (
    <div className="w-full text-white">

      {/* ── Hero ── */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[500px] bg-purple-700/20 rounded-full blur-3xl" />
        </div>
        <div className="relative max-w-5xl mx-auto px-6 pt-24 pb-20 text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-purple-500/40 bg-purple-500/10 text-purple-300 text-sm font-medium mb-8">
            <Star className="w-4 h-4" />
            100% free to start — no credit card required
          </div>
          <h1 className="text-5xl sm:text-6xl lg:text-7xl font-extrabold leading-tight tracking-tight mb-6">
            Turn any YouTube video
            <br />
            <span className="bg-gradient-to-r from-purple-400 via-pink-400 to-blue-400 bg-clip-text text-transparent">
              into viral short clips
            </span>
          </h1>
          <p className="text-lg sm:text-xl text-gray-400 max-w-2xl mx-auto mb-10">
            Paste a YouTube URL. Our AI finds the best moments, cuts them into portrait shorts, and lets you download them instantly.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            {user ? (
              <Link
                to="/generate"
                className="flex items-center gap-2 px-8 py-3.5 bg-purple-600 hover:bg-purple-500 text-white font-semibold rounded-xl text-base transition shadow-lg shadow-purple-900/40"
              >
                Go to Generator <ArrowRight className="w-4 h-4" />
              </Link>
            ) : (
              <>
                <Link
                  to="/register"
                  className="flex items-center gap-2 px-8 py-3.5 bg-purple-600 hover:bg-purple-500 text-white font-semibold rounded-xl text-base transition shadow-lg shadow-purple-900/40"
                >
                  Get started free <ArrowRight className="w-4 h-4" />
                </Link>
                <Link
                  to="/login"
                  className="px-8 py-3.5 border border-white/20 hover:border-white/40 hover:bg-white/5 text-white font-semibold rounded-xl text-base transition"
                >
                  Sign in
                </Link>
              </>
            )}
          </div>
        </div>
      </section>

      {/* ── Features ── */}
      <section className="max-w-5xl mx-auto px-6 py-20">
        <h2 className="text-3xl sm:text-4xl font-bold text-center mb-4">How it works</h2>
        <p className="text-center text-gray-400 mb-14 max-w-xl mx-auto">No setup, no plugins. Just paste and go.</p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-8">
          {features.map((f) => (
            <div key={f.title} className="flex flex-col gap-4 p-6 rounded-2xl bg-white/5 border border-white/10 hover:border-purple-500/40 transition">
              <div className="w-12 h-12 rounded-xl bg-white/5 flex items-center justify-center">{f.icon}</div>
              <h3 className="font-semibold text-lg text-white">{f.title}</h3>
              <p className="text-gray-400 text-sm leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Steps ── */}
      <section className="bg-white/[0.02] border-y border-white/10">
        <div className="max-w-5xl mx-auto px-6 py-20">
          <h2 className="text-3xl sm:text-4xl font-bold text-center mb-14">3 steps to your first clip</h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-8">
            {[
              { step: '01', title: 'Paste a YouTube URL', desc: 'Any public video works — interviews, podcasts, tutorials, gaming.' },
              { step: '02', title: 'AI finds the highlights', desc: 'Whisper transcribes the audio. Our model scores each segment for impact.' },
              { step: '03', title: 'Download your shorts', desc: 'Portrait-format clips are ready to upload directly to social media.' },
            ].map((s) => (
              <div key={s.step} className="flex flex-col gap-3">
                <span className="text-5xl font-black text-purple-500/30">{s.step}</span>
                <h3 className="font-semibold text-lg">{s.title}</h3>
                <p className="text-gray-400 text-sm leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Pricing ── */}
      <section id="pricing" className="max-w-7xl mx-auto px-6 py-24">
        <h2 className="text-3xl sm:text-4xl font-bold text-center mb-3">Simple pricing</h2>
        <p className="text-center text-gray-400 mb-8">Choose your content platform. Start free. Scale when you grow.</p>

        {/* Platform tabs */}
        <div className="flex items-center justify-center gap-2 mb-12 flex-wrap">
          <button
            onClick={() => setPlatform('youtube')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
              platform === 'youtube' ? 'bg-purple-600 text-white shadow' : 'bg-white/5 text-gray-400 hover:text-white border border-white/10'
            }`}
          >
            📺 YouTube
          </button>
          <button
            onClick={() => setPlatform('twitch')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
              platform === 'twitch' ? 'bg-purple-600 text-white shadow' : 'bg-white/5 text-gray-400 hover:text-white border border-white/10'
            }`}
          >
            🎮 Twitch
          </button>
          <button
            onClick={() => setPlatform('combo')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
              platform === 'combo' ? 'bg-purple-600 text-white shadow' : 'bg-white/5 text-gray-400 hover:text-white border border-white/10'
            }`}
          >
            ⚡ Combo Pack
          </button>
        </div>

        {/* Billing toggle */}
        <div className="flex items-center justify-center mb-14">
          <div className="flex items-center gap-1 p-1 bg-white/5 border border-white/10 rounded-xl">
            <button
              onClick={() => setBilling('monthly')}
              className={`px-5 py-2 rounded-lg text-sm font-medium transition ${
                billing === 'monthly' ? 'bg-purple-600 text-white shadow' : 'text-gray-400 hover:text-white'
              }`}
            >
              Monthly
            </button>
            <button
              onClick={() => setBilling('yearly')}
              className={`flex items-center gap-2 px-5 py-2 rounded-lg text-sm font-medium transition ${
                billing === 'yearly' ? 'bg-purple-600 text-white shadow' : 'text-gray-400 hover:text-white'
              }`}
            >
              Yearly
              <span className="px-1.5 py-0.5 rounded-full text-[10px] font-bold bg-green-500/20 text-green-400 border border-green-500/30">
                −15%
              </span>
            </button>
          </div>
        </div>

        {/* Plans grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-6 items-stretch">
          {PLANS_BY_PLATFORM[platform].map((plan: any) => {
            const isPro     = plan.style === 'pro'
            const isProPlus = plan.style === 'proplus'
            const isCurrent = currentPlan === plan.key

            return (
              <div
                key={plan.key}
                className={`relative flex flex-col gap-6 p-7 rounded-2xl border transition ${
                  isPro
                    ? 'bg-purple-600/10 border-purple-500/60 shadow-2xl shadow-purple-900/40 xl:scale-[1.04]'
                    : isProPlus
                    ? 'bg-gradient-to-b from-pink-900/20 to-purple-900/10 border-pink-500/30'
                    : 'bg-white/5 border-white/10'
                }`}
              >
                {/* Badge */}
                {plan.badge && (
                  <span className="absolute -top-4 left-1/2 -translate-x-1/2 whitespace-nowrap px-3 py-1 bg-gradient-to-r from-purple-600 to-pink-600 text-white text-[11px] font-bold rounded-full shadow-lg tracking-wide">
                    {plan.badge}
                  </span>
                )}

                {/* Header */}
                <div>
                  <p className={`text-sm font-semibold mb-2 flex items-center gap-1.5 ${
                    isPro ? 'text-purple-300' : isProPlus ? 'text-pink-300' : 'text-gray-400'
                  }`}>
                    <PlanIcon icon={plan.icon} />
                    {plan.name}
                  </p>
                  <div className="relative flex items-end gap-1 flex-wrap">
                    {billing === 'yearly' && plan.yearlyTotal > 0 && (
                      <span className="absolute -top-3 right-0 text-[10px] font-semibold text-green-400">
                        Save €{(plan.monthlyEur * 12 - plan.yearlyTotal).toFixed(0)}
                      </span>
                    )}
                    <span className="text-4xl font-extrabold text-white">
                      {plan.monthlyEur === 0
                        ? '€0'
                        : billing === 'yearly' && plan.yearlyTotal > 0
                        ? `€${plan.yearlyTotal}`
                        : `€${plan.monthlyEur}`}
                    </span>
                    <span className="text-gray-400 pb-1 text-sm">
                      {plan.monthlyEur === 0
                        ? '/ forever'
                        : billing === 'yearly' && plan.yearlyTotal > 0
                        ? '/ yr'
                        : '/ mo'}
                    </span>
                  </div>
                  {billing === 'yearly' && plan.yearlyTotal > 0 && (
                    <p className="text-xs text-gray-500 mt-1">
                      €{plan.yearlyEur} / mo
                    </p>
                  )}
                </div>

                {/* Features */}
                <ul className="flex flex-col gap-2.5 flex-1">
                  {plan.features.map((feat: string) => {
                    const isSoon = feat.includes('(coming soon)')
                    const label = feat.replace(' (coming soon)', '')
                    return (
                      <li key={feat} className={`flex items-start gap-2 text-sm ${isSoon ? 'text-gray-600' : 'text-gray-300'}`}>
                        {isSoon ? (
                          <Clock className="w-4 h-4 shrink-0 mt-0.5 text-gray-600" />
                        ) : (
                          <CheckCircle className={`w-4 h-4 shrink-0 mt-0.5 ${
                            isPro ? 'text-purple-400' : isProPlus ? 'text-pink-400' : 'text-gray-500'
                          }`} />
                        )}
                        {label}
                        {isSoon && (
                          <span className="ml-auto text-[10px] text-gray-600 border border-gray-700 rounded-full px-1.5 py-0.5 shrink-0">
                            soon
                          </span>
                        )}
                      </li>
                    )
                  })}
                </ul>

                {/* CTA */}
                {isCurrent ? (
                  <div className={`mt-auto text-center px-4 py-2.5 rounded-xl text-sm font-semibold border ${
                    isPro
                      ? 'border-purple-500/30 bg-purple-600/20 text-purple-300'
                      : 'border-white/10 text-gray-500'
                  }`}>
                    ✓ Current plan
                  </div>
                ) : plan.ctaHref ? (
                  <Link
                    to={plan.ctaHref}
                    className="mt-auto text-center px-4 py-2.5 rounded-xl text-sm font-semibold border border-white/20 hover:border-white/40 hover:bg-white/5 text-white transition"
                  >
                    {plan.cta}
                  </Link>
                ) : (
                  <button
                    onClick={() => void handleUpgrade(plan.key)}
                    disabled={loadingKey === plan.key}
                    className={`mt-auto w-full px-4 py-2.5 rounded-xl text-sm font-semibold transition disabled:opacity-50 ${
                      isPro
                        ? 'bg-gradient-to-r from-purple-600 to-purple-500 hover:from-purple-500 hover:to-purple-400 text-white shadow-lg shadow-purple-900/40'
                        : isProPlus
                        ? 'bg-gradient-to-r from-pink-600 to-purple-600 hover:from-pink-500 hover:to-purple-500 text-white shadow-lg shadow-pink-900/30'
                        : 'bg-white/10 hover:bg-white/20 text-white border border-white/20'
                    }`}
                  >
                    {loadingKey === plan.key ? 'Redirecting…' : plan.cta}
                  </button>
                )}
              </div>
            )
          })}
        </div>

        {/* Annual savings nudge */}
        {billing === 'monthly' && (
          <p className="text-center text-gray-500 text-sm mt-10">
            💡 Switch to yearly billing and save up to{' '}
            <span className="text-green-400 font-semibold">€120/year</span> on Pro+
          </p>
        )}
      </section>

      {/* ── Footer CTA — hidden if logged in ── */}
      {!user && (
        <section className="border-t border-white/10 bg-white/[0.02]">
          <div className="max-w-3xl mx-auto px-6 py-20 text-center">
            <Film className="w-10 h-10 text-purple-400 mx-auto mb-6" />
            <h2 className="text-3xl sm:text-4xl font-bold mb-4">Ready to go viral?</h2>
            <p className="text-gray-400 mb-8">Join thousands of creators repurposing content in seconds.</p>
            <Link
              to="/register"
              className="inline-flex items-center gap-2 px-8 py-3.5 bg-purple-600 hover:bg-purple-500 text-white font-semibold rounded-xl text-base transition shadow-lg shadow-purple-900/40"
            >
              Create your free account <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </section>
      )}
    </div>
  )
}