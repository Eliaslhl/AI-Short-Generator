import { useEffect } from 'react'
import { Link } from 'react-router-dom'

export default function ConvertYoutubeToShortsSEO() {
  useEffect(() => {
    document.title = 'Convert YouTube video to Shorts — Fast & automatic'
    const meta = document.querySelector('meta[name="description"]')
    if (meta) meta.setAttribute('content', 'Convert any YouTube video to Shorts quickly. Our AI selects the best moments and outputs ready-to-post vertical clips with captions.')
  }, [])

  return (
    <main className="max-w-4xl mx-auto px-6 py-16 text-white">
      <h1 className="text-4xl font-extrabold mb-6">Convert YouTube video to Shorts</h1>
      <p className="text-gray-300 leading-relaxed mb-4">Paste a YouTube URL and let our AI convert the best moments into short, vertical clips. Perfect for creators who want quick, polished Shorts without manual editing.</p>

      <h2 className="text-2xl font-bold mt-8 mb-3">Fast workflow</h2>
      <p className="text-gray-300 mb-4">Select clip length and quantity, then download captioned MP4s. Use our presets for maximum engagement or customize subtitles and styles.</p>

      <p className="text-gray-300 mb-6">Try it now: <Link to="/generate" className="text-purple-400 underline">Generate your Shorts</Link>.</p>

      <p className="text-gray-400 text-sm mt-8">Back to <Link to="/" className="text-purple-400 underline">home</Link>.</p>
    </main>
  )
}
