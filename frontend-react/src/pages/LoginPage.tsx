import { useState, useEffect, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { authApi } from '../api'
import { type AxiosError } from 'axios'
import { Film, Mail, Lock, Chrome, AlertTriangle } from 'lucide-react'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  // Persist login error to survive odd re-renders/unmounts
  useEffect(() => {
    const saved = localStorage.getItem('login_error')
    if (saved) setError(saved)
  }, [])

  const handleSubmit = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
      // clear persisted error on success
      localStorage.removeItem('login_error')
      navigate('/generate')
    } catch (err) {
  const axiosErr = err as AxiosError<{ detail: string }>
  const msg = axiosErr.response?.data?.detail ?? 'Email or password incorrect.'
      setError(msg)
      try { localStorage.setItem('login_error', msg) } catch {}
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-[calc(100vh-64px)] flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-purple-600/20 mb-4">
              <Film className="w-7 h-7 text-purple-400" />
            </div>
            <h1 className="text-2xl font-bold text-white">Welcome back 👋</h1>
            <p className="text-gray-400 mt-1">Sign in to generate your shorts</p>
          </div>

        {/* Card */}
        <div className="bg-white/5 border border-white/10 rounded-2xl p-8 space-y-4">
          {error && (
            <div
              role="alert"
              aria-live="assertive"
              className="relative bg-red-500/10 border border-red-500/30 text-red-400 rounded-lg pl-5 pr-4 py-3 text-sm"
            >
              <button
                aria-label="Dismiss error"
                onClick={() => setError('')}
                className="absolute top-2 right-3 text-red-300 hover:text-red-100 text-xs"
              >
                ✕
              </button>
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-red-400 animate-pulse shrink-0 mt-0.5" />
                <div className="leading-tight">{error}</div>
              </div>
            </div>
          )}

          {/* Google */}
          <button
            onClick={() => authApi.googleLogin()}
            className="w-full flex items-center justify-center gap-3 px-4 py-2.5 border border-white/20 rounded-lg text-white hover:bg-white/10 transition text-sm font-medium"
          >
            <Chrome className="w-4 h-4" />
            Continue with Google
          </button>

          <div className="flex items-center gap-3">
            <div className="flex-1 h-px bg-white/10" />
            <span className="text-gray-500 text-xs">or</span>
            <div className="flex-1 h-px bg-white/10" />
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1.5">Email</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="john@example.com"
                  required
                  className="w-full pl-10 pr-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 transition text-sm"
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="block text-sm text-gray-400">Password</label>
                <Link
                  to="/forgot-password"
                  className="text-xs text-purple-400 hover:text-purple-300 transition"
                >
                  Forgot password?
                </Link>
              </div>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  className="w-full pl-10 pr-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 transition text-sm"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition text-sm"
            >
              {loading ? 'Signing in...' : 'Sign in'}
            </button>
          </form>

          <p className="text-center text-sm text-gray-400">
            Don't have an account?{' '}
            <Link to="/register" className="text-purple-400 hover:text-purple-300 transition">
              Sign up for free
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
