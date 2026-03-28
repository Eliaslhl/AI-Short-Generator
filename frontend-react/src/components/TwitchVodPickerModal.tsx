import { useState } from 'react'
import { generatorApi } from '../api'
import { Search, X, Play, Eye, Calendar } from 'lucide-react'

interface TwitchVod {
  id: string
  title?: string
  created_at?: string
  duration?: number
  view_count?: number
  url?: string
  thumbnail_url?: string
  channel_name?: string
}

interface TwitchVodPickerModalProps {
  isOpen: boolean
  onClose: () => void
  onSelect: (vodUrl: string, vodTitle: string) => void
  isLoading?: boolean
}

export default function TwitchVodPickerModal({ isOpen, onClose, onSelect, isLoading }: TwitchVodPickerModalProps) {
  const [channelInput, setChannelInput] = useState('')
  const [vods, setVods] = useState<TwitchVod[]>([])
  const [isFetching, setIsFetching] = useState(false)
  const [error, setError] = useState('')
  const [selectedVod, setSelectedVod] = useState<TwitchVod | null>(null)

  const handleSearch = async () => {
    if (!channelInput.trim()) {
      setError('Please enter a channel name')
      return
    }

    setError('')
    setIsFetching(true)
    setVods([])
    setSelectedVod(null)

    try {
      const res = await generatorApi.twitchVods(channelInput.trim(), 20)
      setVods(res.data.vods || [])
      if (!res.data.vods || res.data.vods.length === 0) {
        setError(`No VODs found for channel "${channelInput.trim()}"`)
      }
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || 'Failed to fetch VODs'
      setError(msg)
    } finally {
      setIsFetching(false)
    }
  }

  const handleSelectVod = (vod: TwitchVod) => {
    if (vod.url) {
      onSelect(vod.url, vod.title || 'Twitch VOD')
      setChannelInput('')
      setVods([])
      setSelectedVod(null)
      onClose()
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/95 flex items-center justify-center z-50 p-4 backdrop-blur-sm" onClick={onClose}>
      <div className="max-w-2xl w-full" onClick={(e) => e.stopPropagation()}>
        <div className="bg-slate-950 rounded-2xl overflow-hidden border border-white/10">
          {/* Header */}
          <div className="flex justify-between items-center p-4 border-b border-white/10">
            <h2 className="text-lg font-bold text-white">Select a Twitch VOD</h2>
            <button onClick={onClose} className="hover:bg-white/10 p-2 rounded-lg transition">
              <X size={20} className="text-white" />
            </button>
          </div>

          {/* Search box */}
          <div className="p-4 border-b border-white/10">
            <div className="flex gap-2">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                <input
                  type="text"
                  value={channelInput}
                  onChange={(e) => setChannelInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && void handleSearch()}
                  placeholder="Enter Twitch channel name (e.g., 'ninja')"
                  disabled={isFetching || isLoading}
                  className="w-full pl-10 pr-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 transition disabled:opacity-50"
                />
              </div>
              <button
                onClick={() => void handleSearch()}
                disabled={isFetching || isLoading}
                className="px-4 py-2.5 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-lg hover:shadow-lg transition disabled:opacity-50"
              >
                Search
              </button>
            </div>
          </div>

          {/* Error message */}
          {error && (
            <div className="mx-4 mt-3 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-300">
              {error}
            </div>
          )}

          {/* VODs list */}
          <div className="max-h-96 overflow-y-auto p-4 space-y-2">
            {isFetching ? (
              <div className="text-center py-8 text-gray-400">Searching VODs...</div>
            ) : vods.length > 0 ? (
              vods.map((vod) => (
                <button
                  key={vod.id}
                  onClick={() => void handleSelectVod(vod)}
                  className="w-full p-3 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 hover:border-purple-500/50 transition text-left"
                >
                  <div className="flex gap-3 items-start">
                    {vod.thumbnail_url ? (
                      <img
                        src={vod.thumbnail_url}
                        alt={vod.title}
                        className="w-24 h-14 object-cover rounded-md flex-shrink-0"
                        onError={(e) => {
                          e.currentTarget.style.display = 'none'
                        }}
                      />
                    ) : (
                      <div className="w-24 h-14 bg-white/5 rounded-md flex items-center justify-center flex-shrink-0">
                        <Play className="w-6 h-6 text-gray-500" />
                      </div>
                    )}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-white truncate">{vod.title || 'Untitled VOD'}</p>
                      <p className="text-xs text-gray-400 mt-1 flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        {vod.created_at
                          ? new Date(vod.created_at).toLocaleDateString('en-US', {
                              year: 'numeric',
                              month: 'short',
                              day: 'numeric',
                            })
                          : 'Unknown date'}
                      </p>
                      {vod.view_count != null && (
                        <p className="text-xs text-gray-500 mt-0.5 flex items-center gap-1">
                          <Eye className="w-3 h-3" />
                          {vod.view_count.toLocaleString()} views
                        </p>
                      )}
                      {vod.duration != null && (
                        <p className="text-xs text-gray-500">Duration: {Math.floor(vod.duration / 60)} min</p>
                      )}
                    </div>
                  </div>
                </button>
              ))
            ) : (
              <div className="text-center py-8 text-gray-400">
                {channelInput ? 'Click "Search" to find VODs' : 'Enter a channel name and search'}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
