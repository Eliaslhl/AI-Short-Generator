import { useNavigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { PlayCircle, TrendingUp, ArrowRight } from 'lucide-react'
import { useSeoTags } from '../hooks/useSeoTags'

export default function SourceSelectorPage() {
  const navigate = useNavigate()
  const [hoveredSource, setHoveredSource] = useState<'youtube' | 'twitch' | null>(null)

  useSeoTags({
    title: 'Choose Video Source - AI Shorts Generator',
    description: 'Select YouTube or Twitch to start generating viral short-form videos.',
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

  const sources = [
    {
      id: 'youtube',
      name: 'YouTube',
      icon: '▶️',
      description: 'Convert YouTube videos into viral short-form content',
      features: [
        'Videos & Shorts support',
        'Automatic clip detection',
        'AI-powered viral scoring'
      ],
      color: 'from-red-500 to-red-600',
      path: '/generate/youtube'
    },
    {
      id: 'twitch',
      name: 'Twitch',
      icon: '📺',
      description: 'Transform Twitch clips and VODs into TikTok/YouTube Shorts',
      features: [
        'Clips & VODs support',
        'Streamer moments detection',
        'Gaming content optimization'
      ],
      color: 'from-purple-500 to-purple-600',
      path: '/generate/twitch'
    }
  ]

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-950 via-gray-900 to-gray-950 text-white pt-20 pb-20">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center mb-16">
          <h1 className="text-5xl font-bold mb-4 bg-gradient-to-r from-purple-400 via-pink-400 to-purple-400 bg-clip-text text-transparent">
            Choose Your Source
          </h1>
          <p className="text-xl text-gray-300 max-w-2xl mx-auto">
            Select where your video content comes from. We'll transform it into engaging short-form content optimized for social media.
          </p>
        </div>

        {/* Source Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-16">
          {sources.map((source) => (
            <div
              key={source.id}
              className={`relative group cursor-pointer transition-all duration-300 ${
                hoveredSource === source.id ? 'scale-105' : ''
              }`}
              onMouseEnter={() => setHoveredSource(source.id as 'youtube' | 'twitch')}
              onMouseLeave={() => setHoveredSource(null)}
              onClick={() => navigate(source.path)}
            >
              {/* Background gradient */}
              <div className={`absolute inset-0 bg-gradient-to-br ${source.color} opacity-0 group-hover:opacity-10 rounded-2xl blur-xl transition-opacity duration-300`} />
              
              {/* Card */}
              <div className="relative bg-gray-800/50 border border-gray-700 group-hover:border-gray-500 rounded-2xl p-8 transition-all duration-300 h-full flex flex-col">
                {/* Icon */}
                <div className="text-5xl mb-4">{source.icon}</div>

                {/* Title */}
                <h2 className="text-3xl font-bold mb-2 text-white group-hover:text-transparent group-hover:bg-gradient-to-r group-hover:from-purple-400 group-hover:to-pink-400 group-hover:bg-clip-text transition-all duration-300">
                  {source.name}
                </h2>

                {/* Description */}
                <p className="text-gray-300 text-lg mb-6 flex-grow">
                  {source.description}
                </p>

                {/* Features */}
                <div className="mb-8 space-y-2">
                  {source.features.map((feature, idx) => (
                    <div key={idx} className="flex items-center text-gray-200 text-sm">
                      <span className="mr-2">✓</span>
                      {feature}
                    </div>
                  ))}
                </div>

                {/* CTA Button */}
                <button
                  className={`w-full py-3 px-4 rounded-lg font-semibold transition-all duration-300 flex items-center justify-center gap-2 ${
                    hoveredSource === source.id
                      ? 'bg-gradient-to-r ' + source.color + ' text-white'
                      : 'bg-white/10 text-white hover:bg-white/20'
                  }`}
                >
                  Get Started
                  <ArrowRight size={18} className={hoveredSource === source.id ? 'translate-x-1 transition-transform' : ''} />
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* Info Section */}
        <div className="max-w-4xl mx-auto bg-gray-800/30 border border-gray-700 rounded-xl p-8">
          <h3 className="text-xl font-semibold mb-4 text-gray-100">
            💡 Identical Experience, Different Sources
          </h3>
          <p className="text-gray-300 leading-relaxed">
            Whether you choose YouTube or Twitch, you'll get the same powerful AI-driven clip generation, 
            smart subtitle styling, language auto-detection, and beautiful video formatting. The only difference 
            is the source platform—everything else is optimized to give you the best results for social media distribution.
          </p>
        </div>
      </div>
    </div>
  )
}
