import { Link } from 'react-router-dom'

export default function Footer() {
  return (
    <footer className="mt-12 border-t border-white/10 bg-gray-900 text-gray-300">
      <div className="max-w-6xl mx-auto px-6 py-8 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="flex flex-col">
          <div className="text-white font-semibold text-lg">AI Shorts Generator</div>
          <div className="text-sm text-gray-400 mt-1">Transformez vos vidéos YouTube en shorts viraux</div>
        </div>

        <nav className="flex gap-6 flex-wrap">
          <Link to="/legal/mentions" className="text-sm text-gray-300 hover:text-white">Mentions légales</Link>
          <Link to="/legal/cgu" className="text-sm text-gray-300 hover:text-white">CGU</Link>
          <Link to="/privacy" className="text-sm text-gray-300 hover:text-white">Politique de confidentialité</Link>
          <Link to="/legal/cookies" className="text-sm text-gray-300 hover:text-white">Cookies</Link>
          <Link to="/sitemap" className="text-sm text-gray-300 hover:text-white">Plan du site</Link>
        </nav>
      </div>
      <div className="border-t border-white/5 text-center text-xs text-gray-500 py-3">© {new Date().getFullYear()} AI Shorts Generator — Tous droits réservés.</div>
    </footer>
  )
}
