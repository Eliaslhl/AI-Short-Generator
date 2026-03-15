import { useEffect } from 'react'
import { Link } from 'react-router-dom'

export default function SitemapPage() {
  useEffect(() => {
    document.title = 'Plan du site'
  }, [])

  return (
    <main className="max-w-4xl mx-auto px-6 py-16 text-white">
      <h1 className="text-3xl font-bold mb-4">Plan du site</h1>
      <p className="text-gray-300 mb-4">Accédez rapidement aux pages principales :</p>
      <ul className="list-disc ml-6 text-gray-300">
        <li><Link to="/" className="text-purple-300 underline">Accueil</Link></li>
        <li><Link to="/youtube-shorts-generator" className="text-purple-300 underline">YouTube Shorts Generator</Link></li>
        <li><Link to="/ai-clip-generator" className="text-purple-300 underline">AI Clip Generator</Link></li>
        <li><Link to="/dashboard" className="text-purple-300 underline">Dashboard</Link></li>
        <li><Link to="/privacy" className="text-purple-300 underline">Politique de confidentialité</Link></li>
        <li><Link to="/legal/mentions" className="text-purple-300 underline">Mentions légales</Link></li>
        <li><Link to="/legal/cgu" className="text-purple-300 underline">CGU</Link></li>
        <li><Link to="/legal/cookies" className="text-purple-300 underline">Cookies</Link></li>
      </ul>

      <p className="text-gray-300 mt-6">Retour à <Link to="/" className="text-purple-400 underline">l'accueil</Link>.</p>
    </main>
  )
}
