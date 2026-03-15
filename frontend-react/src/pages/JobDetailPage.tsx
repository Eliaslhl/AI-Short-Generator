import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { generatorApi } from '../api'
import type { Clip, JobStatus } from '../types'
import apiClient from '../api/client'

export default function JobDetailPage() {
  const { jobId } = useParams()
  const [clips, setClips] = useState<Clip[]>([])
  const [status, setStatus] = useState<JobStatus | null>(null)
  const [videoTitle, setVideoTitle] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!jobId) return
    setLoading(true)
    generatorApi.clips(jobId)
      .then((res) => {
        setClips(res.data.clips || [])
        setStatus(res.data.status || null)
        setVideoTitle(res.data.video_title || null)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [jobId])

  if (!jobId) return <div className="p-6">Job ID missing</div>

  return (
    <div className="max-w-4xl mx-auto px-4 py-10">
      <div className="mb-6">
        <Link
          to="/dashboard"
          className="inline-flex items-center gap-2 text-sm text-purple-300 bg-white/5 px-3 py-1.5 rounded-full hover:bg-white/10 transition mb-3"
        >
          ← Back
        </Link>
        <h1 className="text-2xl font-bold">{videoTitle ?? `Job ${jobId}`}</h1>
      </div>

      {loading ? (
        <div>Loading...</div>
      ) : (
        <div className="space-y-4">
          <p className="text-sm text-gray-400">Status: <span className="text-white">{status}</span></p>
          {clips.length === 0 ? (
            <div className="text-gray-400">No clips yet.</div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {clips.map((c, idx) => {
                // build absolute URL to the clip file using the API client's baseURL
                const base = (apiClient.defaults && apiClient.defaults.baseURL) || ''
                const fileUrl = c.file?.startsWith('http') ? c.file : `${base}${c.file}`
                const posterUrl = c.poster ? (c.poster.startsWith('http') ? c.poster : `${base}${c.poster}`) : undefined
                return (
                  <div key={idx} className="bg-white/5 border border-white/10 rounded-lg p-4">
                    <p className="text-white font-medium">{c.title ?? `Clip ${idx + 1}`}</p>
                    <p className="text-gray-400 text-sm">{Math.round(c.viral_score)} score • {c.duration}s</p>
                    <p className="mt-2 text-gray-300 text-sm">{c.hook}</p>
                    <div className="mt-3">
                      {c.file ? (
                        <>
                          <video
                            src={fileUrl}
                            controls
                            poster={posterUrl}
                            className="w-full rounded bg-black"
                            style={{ aspectRatio: '9/16', maxHeight: 480 }}
                          />
                          <div className="mt-2 flex items-center gap-3">
                            <a href={fileUrl} target="_blank" rel="noreferrer" className="text-sm text-purple-300">Open</a>
                            <a href={fileUrl} download className="text-sm text-gray-400">Download</a>
                          </div>
                        </>
                      ) : (
                        <div className="text-sm text-gray-500">No file available</div>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
