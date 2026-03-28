import { Link, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { LogOut, User, Crown, Sparkles, Rocket, LayoutDashboard, Clapperboard, Menu, X } from './icons'
import CookieSettings from './CookieSettings'
import { getCurrentPlatform, getPlanForPlatform, getGenerationsLeft, getGenerationLimit } from '../utils/planUtils'

const PLAN_BADGE: Record<string, { label: string; className: string; icon: React.ReactNode }> = {
  pro: {
    label: 'PRO',
    className: 'bg-yellow-500/20 text-yellow-400',
    icon: <Crown className="w-3 h-3" />,
  },
  standard: {
    label: 'STANDARD',
    className: 'bg-blue-500/20 text-blue-400',
    icon: <Sparkles className="w-3 h-3" />,
  },
  proplus: {
    label: 'PRO+',
    className: 'bg-pink-500/20 text-pink-400',
    icon: <Rocket className="w-3 h-3" />,
  },
}

export default function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)
  const [cookieOpen, setCookieOpen] = useState(false)

  const handleLogout = (): void => {
    logout()
    navigate('/')
    setMenuOpen(false)
  }

  const platform = user ? getCurrentPlatform(user) : 'youtube'
  const effectivePlan = user ? getPlanForPlatform(user, platform) : 'free'
  const generationsLeft = user ? getGenerationsLeft(user, platform) : 0
  const generationLimit = user ? getGenerationLimit(user, platform) : 2

  const planBadge = user ? PLAN_BADGE[effectivePlan] : null

  return (
    <nav className="border-b border-white/10 bg-black/40 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">

    {/* Logo */}
    <Link to="/" className="flex items-center shrink-0 mr-auto md:mr-0">
      <img src="/logoshort.png" alt="AI Shorts Generator" className="h-20 max-h-16 w-auto object-contain" />
    </Link>

        {/* Desktop right */}
        <div className="hidden md:flex items-center gap-3">
          {user ? (
            <>
              {planBadge ? (
                <span className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs font-semibold ${planBadge.className}`}>
                  {planBadge.icon} {planBadge.label}
                </span>
              ) : (
                <span className="text-xs text-gray-400">
                  {generationsLeft} free left
                </span>
              )}
              {/* Quota counter for all plans */}
              <span className="text-xs text-gray-500">
                {generationsLeft}
                {'/'}
                {generationLimit}
                {' left'}
              </span>

              <Link
                to="/generate"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm text-gray-300 hover:text-white hover:bg-white/10 transition"
              >
                <Clapperboard className="w-4 h-4" />
                Generate
              </Link>

              <Link
                to="/dashboard"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm text-gray-300 hover:text-white hover:bg-white/10 transition"
              >
                <LayoutDashboard className="w-4 h-4" />
                Dashboard
              </Link>

              <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/5 text-sm text-white">
                {user.avatar_url ? (
                  <img src={user.avatar_url} alt="" className="w-6 h-6 rounded-full" />
                ) : (
                  <User className="w-4 h-4 text-gray-400" />
                )}
                <span className="text-gray-300 max-w-[120px] truncate">
                  {user.full_name ?? user.email}
                </span>
              </div>

              <button
                onClick={handleLogout}
                className="p-1.5 text-gray-400 hover:text-white hover:bg-white/10 rounded-lg transition"
                  title="Sign out"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </>
          ) : (
            <>
                <Link to="/login" className="text-sm text-gray-300 hover:text-white transition">
                  Sign in
                </Link>
                <Link
                  to="/register"
                  className="px-4 py-1.5 bg-purple-600 hover:bg-purple-500 text-white text-sm rounded-lg transition"
                >
                  Sign up
                </Link>
                <Link to="/privacy" onClick={(e) => { e.preventDefault(); navigate('/privacy'); window.location.href = '/privacy'; }} className="ml-3 text-sm text-gray-400 hover:text-white transition">Privacy</Link>
                <button onClick={() => setCookieOpen(true)} className="ml-3 text-sm text-gray-400 hover:text-white transition">Cookies</button>
            </>
          )}
          {/* Always-visible privacy link for authenticated users as well */}
          {user && (
            <Link to="/privacy" onClick={(e) => { e.preventDefault(); navigate('/privacy'); window.location.href = '/privacy'; }} className="ml-3 text-sm text-gray-400 hover:text-white transition">Privacy</Link>
          )}
        </div>

        {/* Mobile: plan badge + hamburger */}
        <div className="flex md:hidden items-center gap-2">
          {user && planBadge && (
            <span className={`flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold ${planBadge.className}`}>
              {planBadge.icon} {planBadge.label}
            </span>
          )}
          <button
            onClick={() => setMenuOpen((v) => !v)}
            className="p-2 text-gray-300 hover:text-white hover:bg-white/10 rounded-lg transition"
            aria-label="Menu"
          >
            {menuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile dropdown */}
        {menuOpen && (
        <div className="md:hidden border-t border-white/10 bg-black/60 backdrop-blur-md px-4 py-3 flex flex-col gap-1">
          {user ? (
            <>
              {/* User info */}
              <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 mb-1">
                {user.avatar_url ? (
                  <img src={user.avatar_url} alt="" className="w-7 h-7 rounded-full" />
                ) : (
                  <User className="w-4 h-4 text-gray-400" />
                )}
                <div className="flex flex-col min-w-0">
                  <span className="text-white text-sm font-medium truncate">
                    {user.full_name ?? user.email}
                  </span>
                  <span className="text-gray-400 text-xs">
                    {generationsLeft}
                    {'/'}
                    {generationLimit}
                    {' left this month'}
                  </span>
                </div>
              </div>

              <Link
                to="/generate"
                onClick={() => setMenuOpen(false)}
                className="flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm text-gray-300 hover:text-white hover:bg-white/10 transition"
              >
                <Clapperboard className="w-4 h-4" /> Generate
              </Link>

              <Link
                to="/dashboard"
                onClick={() => setMenuOpen(false)}
                className="flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm text-gray-300 hover:text-white hover:bg-white/10 transition"
              >
                <LayoutDashboard className="w-4 h-4" /> Dashboard
              </Link>

              <button
                onClick={() => { handleLogout(); setMenuOpen(false); }}
                className="flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm text-red-400 hover:text-red-300 hover:bg-red-500/10 transition w-full text-left"
              >
                <LogOut className="w-4 h-4" /> Sign out
              </button>
            </>
          ) : (
            <>
              <Link
                to="/login"
                onClick={() => setMenuOpen(false)}
                className="px-3 py-2.5 rounded-lg text-sm text-gray-300 hover:text-white hover:bg-white/10 transition"
              >
                Sign in
              </Link>
              <Link
                to="/register"
                onClick={() => setMenuOpen(false)}
                className="px-3 py-2.5 bg-purple-600 hover:bg-purple-500 text-white text-sm rounded-lg transition text-center"
              >
                Sign up
              </Link>
                  <Link to="/privacy" onClick={(e) => { e.preventDefault(); setMenuOpen(false); navigate('/privacy'); window.location.href = '/privacy'; }} className="px-3 py-2.5 text-sm text-gray-400 hover:text-white transition">Privacy</Link>
                  <button onClick={() => { setCookieOpen(true); setMenuOpen(false) }} className="px-3 py-2.5 text-sm text-gray-400 hover:text-white transition text-left">Cookies</button>
            </>
          )}
          {/* If user is authenticated, still show Privacy + Cookies in the mobile menu */}
          {user && (
            <>
              <Link to="/privacy" onClick={(e) => { e.preventDefault(); setMenuOpen(false); navigate('/privacy'); window.location.href = '/privacy'; }} className="px-3 py-2.5 text-sm text-gray-400 hover:text-white transition">Privacy</Link>
              <button onClick={() => { setCookieOpen(true); setMenuOpen(false) }} className="px-3 py-2.5 text-sm text-gray-400 hover:text-white transition text-left">Cookies</button>
            </>
          )}
        </div>
      )}
      <CookieSettings open={cookieOpen} onClose={() => setCookieOpen(false)} />
    </nav>
  )
}

