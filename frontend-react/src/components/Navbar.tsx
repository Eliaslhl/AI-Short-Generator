import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Film, LogOut, User, Crown, LayoutDashboard, Clapperboard } from 'lucide-react'

export default function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = (): void => {
    logout()
    navigate('/')
  }

  return (
    <nav className="border-b border-white/10 bg-black/40 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2 font-bold text-white text-lg">
          <Film className="w-6 h-6 text-purple-400" />
          <span className="bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
            AI Shorts
          </span>
        </Link>

        {/* Right */}
        <div className="flex items-center gap-3">
          {user ? (
            <>
              {user.plan === 'pro' ? (
                <span className="flex items-center gap-1 px-2 py-1 bg-yellow-500/20 text-yellow-400 rounded-full text-xs font-semibold">
                  <Crown className="w-3 h-3" /> PRO
                </span>
              ) : (
                <span className="text-xs text-gray-400">
                  {user.free_generations_left} génération{user.free_generations_left !== 1 ? 's' : ''} gratuite{user.free_generations_left !== 1 ? 's' : ''}
                </span>
              )}

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
                title="Se déconnecter"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className="text-sm text-gray-300 hover:text-white transition">
                Se connecter
              </Link>
              <Link
                to="/register"
                className="px-4 py-1.5 bg-purple-600 hover:bg-purple-500 text-white text-sm rounded-lg transition"
              >
                S'inscrire
              </Link>
            </>
          )}
        </div>
      </div>
    </nav>
  )
}
