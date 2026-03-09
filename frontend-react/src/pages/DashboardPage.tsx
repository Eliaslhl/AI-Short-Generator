import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { authApi, generatorApi } from '../api'
import type { Job, JobStatus } from '../types'
import { Crown, Sparkles, Clock, CheckCircle, AlertCircle, Film, TrendingUp } from 'lucide-react'

function StatusIcon({ status }: { status: JobStatus }) {
  if (status === 'done') return <CheckCircle className="w-5 h-5 text-green-400 shrink-0" />
  if (status === 'error') return <AlertCircle className="w-5 h-5 text-red-400 shrink-0" />
  return <Clock className="w-5 h-5 text-yellow-400 shrink-0" />
}

export default function DashboardPage() {
  const { user } = useAuth()
  const [history, setHistory] = useState<Job[]>([])
  const [loading, setLoading] = useState(true)
  const [loadingCheckout, setLoadingCheckout] = useState(false)

  useEffect(() => {
    generatorApi
      .history()
      .then((res) => setHistory(res.data.history))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const handleUpgrade = async (): Promise<void> => {
    setLoadingCheckout(true)
    try {
      const res = await authApi.createCheckout()
      window.location.href = res.data.checkout_url
    } catch {
      setLoadingCheckout(false)
    }
  }

  const isPro = user?.plan === 'pro'
  const totalClips = history.reduce((acc, j) => acc + (j.clips_count ?? 0), 0)

  return (
    <div className="max-w-4xl mx-auto px-4 py-10">
      <h1 className="text-2xl font-bold text-white mb-8">Dashboard</h1>

      <div className="grid md:grid-cols-3 gap-4 mb-8">
        <div className={`col-span-1 rounded-2xl p-5 border ${isPro ? 'bg-yellow-500/10 border-yellow-500/30' : 'bg-white/5 border-white/10'}`}>
          <div className="flex items-center gap-2 mb-3">
            <Crown className={`w-5 h-5 ${isPro ? 'text-yellow-400' : 'text-gray-500'}`} />
            <span className="text-white font-semibold">{isPro ? 'Pro Plan' : 'Free Plan'}</span>
          </div>
          {isPro ? (
            <p className="text-yellow-300/80 text-sm">Unlimited generations</p>
          ) : (
            <>
              <p className="text-gray-400 text-sm mb-3">
                <span className="text-white font-semibold">{user?.free_generations_left}</span>/2 generations this month
              </p>
              <button
                onClick={() => void handleUpgrade()}
                disabled={loadingCheckout}
                className="w-full py-2 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white text-sm font-semibold rounded-lg transition disabled:opacity-50"
              >
                {loadingCheckout ? '...' : 'Upgrade to Pro'}
              </button>
            </>
          )}
        </div>

        <div className="bg-white/5 border border-white/10 rounded-2xl p-5">
          <div className="flex items-center gap-2 mb-2">
            <Film className="w-5 h-5 text-purple-400" />
            <span className="text-gray-400 text-sm">Total jobs</span>
          </div>
          <p className="text-3xl font-bold text-white">{history.length}</p>
        </div>

        <div className="bg-white/5 border border-white/10 rounded-2xl p-5">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="w-5 h-5 text-green-400" />
            <span className="text-gray-400 text-sm">Clips generated</span>
          </div>
          <p className="text-3xl font-bold text-white">{totalClips}</p>
        </div>
      </div>

      <div className="mb-8">
        <Link
          to="/"
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-purple-600 hover:bg-purple-500 text-white font-semibold rounded-xl transition"
        >
          <Sparkles className="w-4 h-4" />
          New generation
        </Link>
      </div>

      <div>
        <h2 className="text-white font-semibold mb-4">History</h2>
        {loading ? (
          <div className="flex justify-center py-10">
            <div className="w-7 h-7 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : history.length === 0 ? (
          <div className="text-center py-14 bg-white/5 border border-white/10 rounded-2xl">
            <Film className="w-10 h-10 text-gray-600 mx-auto mb-3" />
            <p className="text-gray-400">No generations yet.</p>
            <Link to="/" className="text-purple-400 text-sm hover:underline mt-1 inline-block">
              Generate your first short
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {history.map((job) => (
              <div
                key={job.id}
                className="flex items-center justify-between bg-white/5 border border-white/10 rounded-xl px-5 py-4 hover:border-white/20 transition"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <StatusIcon status={job.status} />
                  <div className="min-w-0">
                    <p className="text-white text-sm font-medium truncate">
                      {job.video_title ?? job.youtube_url}
                    </p>
                    <p className="text-gray-500 text-xs mt-0.5">
                      {new Date(job.created_at).toLocaleDateString('en-GB', {
                        day: '2-digit', month: 'short', year: 'numeric',
                        hour: '2-digit', minute: '2-digit',
                      })}
                    </p>
                  </div>
                </div>
                <div className="text-right shrink-0 ml-4">
                  <p className="text-purple-300 text-sm font-medium">{job.clips_count} clips</p>
                  <p className={`text-xs mt-0.5 capitalize ${
                    job.status === 'done' ? 'text-green-400' :
                    job.status === 'error' ? 'text-red-400' : 'text-yellow-400'
                  }`}>{job.status}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
