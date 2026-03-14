import { useEffect } from 'react'

export default function AiClipGenerator() {
  useEffect(() => {
    document.title = 'AI Clip Generator for YouTube and TikTok'
    const desc = document.querySelector('meta[name="description"]')
    if (desc) desc.setAttribute('content', 'AI Clip Generator for YouTube and TikTok - Automatically create short, shareable clips from long-form videos using AI.')
  }, [])

  return (
    <main className="max-w-4xl mx-auto px-6 py-16 text-white">
      <h1 className="text-4xl font-extrabold mb-6">AI Clip Generator for YouTube and TikTok</h1>

      <p className="text-gray-300 leading-relaxed mb-4">
        The AI clip generator helps creators produce short-form content quickly by extracting the most compelling parts of a video and preparing them for mobile social platforms. The tool identifies peaks in engagement — emotional moments, demonstrations, punchlines and transitions — and turns them into polished clips with captions and vertical crop.
      </p>

      <h2 className="text-2xl font-bold mt-6 mb-3">Features</h2>
      <p className="text-gray-300 leading-relaxed mb-4">
        Automatic highlight detection, subtitle generation, aspect-ratio conversion, and batch processing let you produce dozens of shorts from a single long video. The AI clip generator supports customization for clip length and caption styling so the output matches your channel’s voice.
      </p>

      <h2 className="text-2xl font-bold mt-6 mb-3">Use cases</h2>
      <p className="text-gray-300 leading-relaxed mb-4">
        Repurpose podcasts into bite-sized highlights, create product demo snippets, and surface tutorial steps as quick tips. Each clip is formatted for high completion rates and shareability across YouTube Shorts, TikTok and Reels.
      </p>

      <p className="text-gray-300 leading-relaxed mt-6">
        Keywords: AI clip generator, AI shorts generator, YouTube shorts generator, YouTube video to shorts.
      </p>
    </main>
  )
}
