import { useEffect } from 'react'
import { Link } from 'react-router-dom'

export default function YoutubeShortsGeneratorSEO() {
  useEffect(() => {
    document.title = 'YouTube Shorts Generator — Create vertical clips from full videos'
    const meta = document.querySelector('meta[name="description"]')
    if (meta) meta.setAttribute('content', 'YouTube Shorts Generator: automatically extract and optimize the best moments from YouTube videos into Shorts-ready clips.')
  }, [])

  return (
    <main className="max-w-4xl mx-auto px-6 py-16 text-white">
      <h1 className="text-4xl font-extrabold mb-6">YouTube Shorts Generator</h1>
      <p className="text-gray-300 leading-relaxed mb-4">
        Convert long YouTube uploads into attention-grabbing Shorts. Our system finds highlights, crops to 9:16, and produces captioned clips ready to post.
      </p>

      <h2 className="text-2xl font-bold mt-8 mb-3">Who it's for</h2>
      <p className="text-gray-300 mb-4">Creators, social managers and brands who want to drive views from Shorts back to full videos. Automated workflows let you scale repurposing without hiring editors.</p>

      <h2 className="text-2xl font-bold mt-8 mb-3">Features</h2>
      <ul className="list-disc ml-6 text-gray-300 mb-4">
        <li>Automatic highlight detection</li>
        <li>Subtitle generation for accessibility</li>
        <li>Direct downloads in vertical format</li>
      </ul>

      <p className="text-gray-300 mb-6">Start now: <Link to="/generate" className="text-purple-400 underline">Generate Shorts</Link> from any public YouTube video.</p>

      <p className="text-gray-400 text-sm mt-8">Back to <Link to="/" className="text-purple-400 underline">home</Link>.</p>
    </main>
  )
}
