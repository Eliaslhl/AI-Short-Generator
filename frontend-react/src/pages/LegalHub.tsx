import { Link, useParams } from 'react-router-dom'
import MentionsLegales from './MentionsLegales'
import CGU from './CGU'
import PrivacyPolicy from './PrivacyPolicy'
import CookiesPolicy from './CookiesPolicy'
import SitemapPage from './SitemapPage'

const sections: { key: string; title: string; path: string }[] = [
  { key: 'mentions', title: 'Mentions légales', path: '/legal/mentions' },
  { key: 'cgu', title: 'CGU', path: '/legal/cgu' },
  { key: 'privacy', title: 'Politique de confidentialité', path: '/legal/privacy' },
  { key: 'cookies', title: 'Cookies', path: '/legal/cookies' },
  { key: 'sitemap', title: 'Plan du site', path: '/legal/sitemap' },
]

function renderSection(key?: string) {
  switch (key) {
    case 'mentions':
      return <MentionsLegales />
    case 'cgu':
      return <CGU />
    case 'privacy':
      return <PrivacyPolicy />
    case 'cookies':
      return <CookiesPolicy />
    case 'sitemap':
      return <SitemapPage />
    default:
      return <MentionsLegales />
  }
}

export default function LegalHub() {
  const params = useParams()
  const page = params.page || 'mentions'

  return (
    <div className="max-w-6xl mx-auto px-6 py-12">
      <h1 className="text-3xl font-bold mb-6">Informations légales et politiques</h1>
      <div className="flex gap-8">
        <aside className="w-64 shrink-0">
          <nav className="flex flex-col gap-2">
            {sections.map(s => (
              <Link
                key={s.key}
                to={s.path}
                className={`block px-3 py-2 rounded ${s.key === page ? 'bg-gray-800 text-white' : 'text-gray-300 hover:bg-gray-900'}`}>
                {s.title}
              </Link>
            ))}
          </nav>
        </aside>

        <main className="prose prose-invert max-w-none flex-1">
          {renderSection(page)}
        </main>
      </div>
    </div>
  )
}
