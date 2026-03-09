import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { Film, Mail, ArrowLeft, CheckCircle } from 'lucide-react'
import { type AxiosError } from 'axios'
import client from '../api/client'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [sent, setSent] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await client.post('/auth/forgot-password', { email })
      setSent(true)
    } catch (err) {
      const axiosErr = err as AxiosError<{ detail: string }>
      setError(axiosErr.response?.data?.detail ?? 'An error occurred. Please try again.')
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
          <h1 className="text-2xl font-bold text-white">Forgot password?</h1>
          <p className="text-gray-400 mt-1">
            Enter your email and we'll send you a reset link.
          </p>
        </div>

        <div className="bg-white/5 border border-white/10 rounded-2xl p-8 space-y-4">
          {sent ? (
            /* Success state */
            <div className="text-center py-4 space-y-4">
              <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-green-500/20">
                <CheckCircle className="w-7 h-7 text-green-400" />
              </div>
              <div>
                <p className="text-white font-semibold text-lg">Check your inbox</p>
                <p className="text-gray-400 text-sm mt-1">
                  If <span className="text-white">{email}</span> is registered,
                  you'll receive a reset link within a few minutes.
                </p>
              </div>
              <p className="text-gray-500 text-xs">
                Didn't receive it? Check your spam folder or{' '}
                <button
                  onClick={() => setSent(false)}
                  className="text-purple-400 hover:text-purple-300 underline"
                >
                  try again
                </button>.
              </p>
            </div>
          ) : (
            /* Form state */
            <form onSubmit={(e) => void handleSubmit(e)} className="space-y-4">
              {error && (
                <div className="bg-red-500/10 border border-red-500/30 text-red-400 rounded-lg px-4 py-3 text-sm">
                  {error}
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">
                  Email address
                </label>
                <div className="relative">
                  <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@example.com"
                    required
                    className="w-full pl-10 pr-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 transition text-sm"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading || !email}
                className="w-full py-2.5 bg-purple-600 hover:bg-purple-500 text-white font-semibold rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed text-sm"
              >
                {loading ? 'Sending…' : 'Send reset link'}
              </button>
            </form>
          )}
        </div>

        <div className="text-center mt-6">
          <Link
            to="/login"
            className="inline-flex items-center gap-1.5 text-sm text-gray-400 hover:text-white transition"
          >
            <ArrowLeft className="w-4 h-4" /> Back to login
          </Link>
        </div>
      </div>
    </div>
  )
}
