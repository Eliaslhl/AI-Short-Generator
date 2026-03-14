import { useEffect } from 'react'
import { Link } from 'react-router-dom'

export default function AiShortsGeneratorSEO() {
  useEffect(() => {
    document.title = 'AI Shorts Generator — Convert YouTube to Viral Shorts'
    const meta = document.querySelector('meta[name="description"]')
    if (meta) meta.setAttribute('content', 'AI Shorts Generator: automatically convert YouTube videos into short, viral-ready clips. Fast, automated, and optimized for TikTok, Reels and YouTube Shorts.')
  }, [])

  return (
    <main className="max-w-4xl mx-auto px-6 py-16 text-white">
      <h1 className="text-4xl font-extrabold mb-6">AI Shorts Generator — Transform YouTube videos into viral short clips</h1>
      <p className="text-gray-300 leading-relaxed mb-4">
        Our AI Shorts Generator analyzes full-length YouTube videos, finds the most engaging moments, and exports optimized vertical clips ready to publish on TikTok, Instagram Reels and YouTube Shorts. This is ideal for creators and brands who want to repurpose long-form content quickly.
      </p>

      <h2 className="text-2xl font-bold mt-8 mb-3">Why use an AI shorts generator?</h2>
      <ul className="list-disc ml-6 text-gray-300 mb-4">
        <li>Save hours of manual editing.</li>
        <li>Scale your content output: create many shorts from one video.</li>
        <li>Automatic captions, smart cropping, and viral scoring.</li>
      </ul>

      <h2 className="text-2xl font-bold mt-8 mb-3">How it works</h2>
      <p className="text-gray-300 mb-4">
        Paste a YouTube URL, choose the number of clips, and our pipeline transcribes the audio, ranks segments by engagement potential, crops to portrait, and adds subtitles. You get downloadable MP4s ready to post.
      </p>

      <h2 className="text-2xl font-bold mt-8 mb-3">Try it</h2>
      <p className="text-gray-300 mb-6">Ready to generate your first short? <Link to="/generate" className="text-purple-400 underline">Go to the generator</Link> — it only takes a minute to get started.</p>

      <h2 className="text-2xl font-bold mt-8 mb-3">SEO & best practices</h2>
      <p className="text-gray-300 mb-4">To get the best reach, pair generated shorts with compelling titles, relevant hashtags and a short description that points back to the original long-form video. Cross-posting and posting at peak hours increases engagement.</p>

      <p className="text-gray-400 text-sm mt-8">If you want more tips on repurposing content, check our <Link to="/" className="text-purple-400 underline">home page</Link>.</p>
    </main>
  )
}
