import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Film, Lock, Eye, EyeOff, CheckCircle, AlertCircle } from 'lucide-react'
import { type AxiosError } from 'axios'
import client from '../api/client'

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const token = searchParams.get('token') ?? ''

  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [showPwd, setShowPwd] = useState(false)
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState('')

  const strengthScore = (() => {
    let s = 0
    if (password.length >= 8) s++
    if (/[A-Z]/.test(password)) s++
    if (/[0-9]/.test(password)) s++
    if (/[^A-Za-z0-9]/.test(password)) s++
    return s
  })()

  const strengthLabel = ['', 'Weak', 'Fair', 'Good', 'Strong'][strengthScore]
  const strengthColor = ['', 'bg-red-500', 'bg-orange-400', 'bg-yellow-400', 'bg-green-500'][strengthScore]

  const handleSubmit = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault()
    setError('')

    if (password !== confirm) {
      setError('Passwords do not match.')
      return
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters.')
      return
    }

    setLoading(true)
    try {
      await client.post('/auth/reset-password', { token, new_password: password })
      setSuccess(true)
      setTimeout(() => navigate('/login'), 3000)
    } catch (err) {
      const axiosErr = err as AxiosError<{ detail: string }>
      setError(axiosErr.response?.data?.detail ?? 'An error occurred. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  /* No token in URL */
  if (!token) {
    return (
      <div className="min-h-[calc(100vh-64px)] flex items-center justify-center px-4">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <h2 className="text-white font-semibold text-xl mb-2">Invalid reset link</h2>
          <p className="text-gray-400 text-sm mb-6">
            This link is missing a token. Please request a new one.
          </p>
          <Link to="/forgot-password" className="px-6 py-2.5 bg-purple-600 hover:bg-purple-500 text-white rounded-lg text-sm font-semibold transition">
            Request new link
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-[calc(100vh-64px)] flex items-center justify-center px-4">
      <div className="w-full max-w-md">

        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-purple-600/20 mb-4">
            <Film className="w-7 h-7 text-purple-400" />
          </div>
          <h1 className="text-2xl font-bold text-white">Set a new password</h1>
          <p className="text-gray-400 mt-1">Choose a strong password for your account.</p>
        </div>

        <div className="bg-white/5 border border-white/10 rounded-2xl p-8">
          {success ? (
            <div className="text-center py-4 space-y-4">
              <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-green-500/20">
                <CheckCircle className="w-7 h-7 text-green-400" />
              </div>
              <div>
                <p className="text-white font-semibold text-lg">Password updated!</p>
                <p className="text-gray-400 text-sm mt-1">
                  Redirecting you to login…
                </p>
              </div>
            </div>
          ) : (
            <form onSubmit={(e) => void handleSubmit(e)} className="space-y-4">
              {error && (
                <div className="bg-red-500/10 border border-red-500/30 text-red-400 rounded-lg px-4 py-3 text-sm flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                  {error}
                </div>
              )}

              {/* New password */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">
                  New password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                  <input
                    type={showPwd ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="At least 8 characters"
                    required
                    className="w-full pl-10 pr-10 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 transition text-sm"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPwd((v) => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300"
                  >
                    {showPwd ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>

                {/* Strength bar */}
                {password.length > 0 && (
                  <div className="mt-2 space-y-1">
                    <div className="flex gap-1">
                      {[1, 2, 3, 4].map((i) => (
                        <div
                          key={i}
                          className={`h-1 flex-1 rounded-full transition-all duration-300 ${
                            i <= strengthScore ? strengthColor : 'bg-white/10'
                          }`}
                        />
                      ))}
                    </div>
                    <p className="text-xs text-gray-500">
                      Strength: <span className="text-white">{strengthLabel}</span>
                    </p>
                  </div>
                )}
              </div>

              {/* Confirm password */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">
                  Confirm password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                  <input
                    type={showPwd ? 'text' : 'password'}
                    value={confirm}
                    onChange={(e) => setConfirm(e.target.value)}
                    placeholder="Repeat your password"
                    required
                    className={`w-full pl-10 pr-4 py-2.5 bg-white/5 border rounded-lg text-white placeholder-gray-500 focus:outline-none transition text-sm ${
                      confirm && password !== confirm
                        ? 'border-red-500/50 focus:border-red-500'
                        : 'border-white/10 focus:border-purple-500'
                    }`}
                  />
                </div>
                {confirm && password !== confirm && (
                  <p className="text-xs text-red-400 mt-1">Passwords don't match.</p>
                )}
              </div>

              <button
                type="submit"
                disabled={loading || !password || !confirm || password !== confirm}
                className="w-full py-2.5 bg-purple-600 hover:bg-purple-500 text-white font-semibold rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed text-sm"
              >
                {loading ? 'Updating…' : 'Update password'}
              </button>
            </form>
          )}
        </div>

      </div>
    </div>
  )
}
