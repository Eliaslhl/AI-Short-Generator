import { Link } from 'react-router-dom'
import { Film, Zap, Clock, Download, Star, ArrowRight, CheckCircle } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

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

const plans = [
  {
    name: 'Free',
    price: '0',
    period: 'forever',
    features: ['3 generations per month', 'Up to 3 clips per video', 'Standard quality'],
    cta: 'Get started free',
    href: '/register',
    highlight: false,
  },
  {
    name: 'Pro',
    price: '12',
    period: 'per month',
    features: ['Unlimited generations', 'Up to 10 clips per video', 'Priority processing', 'Early access to new features'],
    cta: 'Start Pro',
    href: '/register',
    highlight: true,
  },
]

export default function LandingPage() {
  const { user } = useAuth()

  return (
    <div className="w-full text-white">
      {/* Hero */}
      <section className="relative overflow-hidden">
        {/* Background glow */}
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

      {/* Features */}
      <section className="max-w-5xl mx-auto px-6 py-20">
        <h2 className="text-3xl sm:text-4xl font-bold text-center mb-4">How it works</h2>
        <p className="text-center text-gray-400 mb-14 max-w-xl mx-auto">
          No setup, no plugins. Just paste and go.
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-8">
          {features.map((f) => (
            <div
              key={f.title}
              className="flex flex-col gap-4 p-6 rounded-2xl bg-white/5 border border-white/10 hover:border-purple-500/40 transition"
            >
              <div className="w-12 h-12 rounded-xl bg-white/5 flex items-center justify-center">
                {f.icon}
              </div>
              <h3 className="font-semibold text-lg text-white">{f.title}</h3>
              <p className="text-gray-400 text-sm leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Steps */}
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

      {/* Pricing */}
      <section className="max-w-4xl mx-auto px-6 py-20">
        <h2 className="text-3xl sm:text-4xl font-bold text-center mb-4">Simple pricing</h2>
        <p className="text-center text-gray-400 mb-14">Start free. Upgrade when you need more.</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-8">
          {plans.map((plan) => (
            <div
              key={plan.name}
              className={`relative flex flex-col gap-6 p-8 rounded-2xl border transition ${
                plan.highlight
                  ? 'bg-purple-600/10 border-purple-500/60 shadow-xl shadow-purple-900/30'
                  : 'bg-white/5 border-white/10'
              }`}
            >
              {plan.highlight && (
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 bg-purple-600 text-white text-xs font-bold rounded-full uppercase tracking-wider">
                  Most popular
                </span>
              )}
              <div>
                <p className="text-gray-400 text-sm font-medium mb-1">{plan.name}</p>
                <div className="flex items-end gap-1">
                  <span className="text-4xl font-extrabold text-white">${plan.price}</span>
                  <span className="text-gray-400 pb-1 text-sm">/{plan.period}</span>
                </div>
              </div>
              <ul className="flex flex-col gap-3">
                {plan.features.map((feat) => (
                  <li key={feat} className="flex items-center gap-2 text-sm text-gray-300">
                    <CheckCircle className="w-4 h-4 text-purple-400 shrink-0" />
                    {feat}
                  </li>
                ))}
              </ul>
              <Link
                to={plan.href}
                className={`mt-auto text-center px-6 py-3 rounded-xl font-semibold text-sm transition ${
                  plan.highlight
                    ? 'bg-purple-600 hover:bg-purple-500 text-white shadow-lg shadow-purple-900/40'
                    : 'border border-white/20 hover:border-white/40 hover:bg-white/5 text-white'
                }`}
              >
                {plan.cta}
              </Link>
            </div>
          ))}
        </div>
      </section>

      {/* Footer CTA */}
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
    </div>
  )
}
