import { useEffect } from 'react'
import { Link } from 'react-router-dom'

export default function SitemapPage() {
  useEffect(() => {
    document.title = 'Sitemap'
  }, [])

  return (
    <main className="max-w-4xl mx-auto px-6 py-16 text-white">
      <h1 className="text-3xl font-bold mb-4">Sitemap</h1>
      <p className="text-gray-300 mb-4">Quick access to the main pages:</p>
      <ul className="list-disc ml-6 text-gray-300">
        <li><Link to="/" className="text-purple-300 underline">Home</Link></li>
        <li><Link to="/youtube-shorts-generator" className="text-purple-300 underline">YouTube Shorts Generator</Link></li>
        <li><Link to="/ai-clip-generator" className="text-purple-300 underline">AI Clip Generator</Link></li>
        <li><Link to="/dashboard" className="text-purple-300 underline">Dashboard</Link></li>
        <li><Link to="/privacy" className="text-purple-300 underline">Privacy Policy</Link></li>
        <li><Link to="/legal/mentions" className="text-purple-300 underline">Legal Notice</Link></li>
        <li><Link to="/legal/cgu" className="text-purple-300 underline">Terms</Link></li>
        <li><Link to="/legal/cookies" className="text-purple-300 underline">Cookies</Link></li>
      </ul>

      <p className="text-gray-300 mt-6">Back to <Link to="/" className="text-purple-400 underline">home</Link>.</p>
    </main>
  )
}
