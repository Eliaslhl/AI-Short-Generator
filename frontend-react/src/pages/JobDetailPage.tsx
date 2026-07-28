import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { generatorApi } from '../api'
import { useSeoTags } from '../hooks/useSeoTags'
import type { Clip, JobStatus } from '../types'
import { getPrivateClipDownloadUrl, getPrivateClipMediaUrl } from '../utils/privateMedia'

export default function JobDetailPage() {
  const { jobId } = useParams()
  const [clips, setClips] = useState<Clip[]>([])
  const [status, setStatus] = useState<JobStatus | null>(null)
  const [videoTitle, setVideoTitle] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  // Block indexing for this internal page
  useSeoTags({
    title: 'Job Details - AI Shorts Generator',
    description: 'View generated clips and job status.',
  })

  // Add noindex meta tag
  useEffect(() => {
    let robotsMeta = document.querySelector('meta[name="robots"]')
    if (!robotsMeta) {
      robotsMeta = document.createElement('meta')
      robotsMeta.setAttribute('name', 'robots')
      document.head.appendChild(robotsMeta)
    }
    robotsMeta.setAttribute('content', 'noindex, nofollow')
  }, [])

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
                const mediaUrl = getPrivateClipMediaUrl(c)
                const downloadUrl = getPrivateClipDownloadUrl(c)
                return (
                  <div key={idx} className="bg-white/5 border border-white/10 rounded-lg p-4">
                    <p className="text-white font-medium">{c.title ?? `Clip ${idx + 1}`}</p>
                    <p className="text-gray-400 text-sm">{Math.round(c.viral_score)} score • {c.duration}s</p>
                    <p className="mt-2 text-gray-300 text-sm">{c.hook}</p>
                    <div className="mt-3">
                      {mediaUrl ? (
                        <>
                          <video
                            src={mediaUrl}
                            controls
                            className="w-full rounded bg-black"
                            style={{ aspectRatio: '9/16', maxHeight: 480 }}
                          />
                          <div className="mt-2 flex items-center gap-3">
                            <a href={mediaUrl} target="_blank" rel="noreferrer" className="text-sm text-purple-300">Open</a>
                            {downloadUrl && <a href={downloadUrl} className="text-sm text-gray-400">Download</a>}
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
