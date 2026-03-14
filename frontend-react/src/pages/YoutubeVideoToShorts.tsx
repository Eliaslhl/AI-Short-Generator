import { useEffect } from 'react'

export default function YoutubeVideoToShorts() {
  useEffect(() => {
    document.title = 'Turn YouTube Videos Into Shorts with AI'
    const desc = document.querySelector('meta[name="description"]')
    if (desc) desc.setAttribute('content', 'Turn YouTube videos into short vertical clips automatically. AI selects highlights and exports ready-to-publish Shorts, Reels and TikToks.')
  }, [])

  return (
    <main className="max-w-4xl mx-auto px-6 py-16 text-white">
      <h1 className="text-4xl font-extrabold mb-6">Turn YouTube Videos Into Shorts with AI</h1>

      <p className="text-gray-300 leading-relaxed mb-4">
        Convert full-length YouTube videos into a series of short clips designed for modern social platforms. Our AI evaluates speech, pacing and scene changes to detect moments that are likely to capture attention. Each clip is trimmed, enhanced and captioned automatically so you can upload immediately.
      </p>

      <h2 className="text-2xl font-bold mt-6 mb-3">From long-form to short-form</h2>
      <p className="text-gray-300 leading-relaxed mb-4">
        Whether you publish interviews, tutorials or livestreams, this flow makes repurposing effortless. The system creates multiple clip variants, applies portrait cropping, and adds subtitles to improve accessibility and completion rates. Export options include 9:16 vertical video at 1080p.
      </p>

      <h2 className="text-2xl font-bold mt-6 mb-3">Best practices</h2>
      <p className="text-gray-300 leading-relaxed mb-4">
        Add a descriptive title and custom thumbnail after export, experiment with multiple clips per video, and post within the first 24–48 hours of publishing for best reach. Use the AI clip generator to create teasers that drive viewers back to the full video.
      </p>

      <p className="text-gray-300 leading-relaxed mt-6">
        Keywords: YouTube video to shorts, AI clip generator, YouTube shorts generator, AI shorts generator.
      </p>
    </main>
  )
}
