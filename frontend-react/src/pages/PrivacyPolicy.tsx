import { useEffect } from 'react'
import { Link } from 'react-router-dom'

export default function PrivacyPolicy() {
  useEffect(() => {
    document.title = 'Politique de confidentialité'
    const meta = document.querySelector('meta[name="description"]')
    if (meta) meta.setAttribute('content', 'Politique de confidentialité pour AI Shorts Generator — comment nous collectons et traitons les données, cookies et informations utilisateur.')
  }, [])

  return (
    <main className="max-w-4xl mx-auto px-6 py-16 text-white">
      <h1 className="text-3xl font-bold mb-4">Politique de confidentialité</h1>
      <p className="text-gray-300 mb-4">Cette page explique quelles données nous collectons, pourquoi, et comment vous pouvez exercer vos droits. Nous respectons les règles RGPD applicables aux utilisateurs européens.</p>

      <h2 className="text-xl font-semibold mt-6 mb-2">Données collectées</h2>
      <ul className="list-disc ml-6 text-gray-300 mb-4">
        <li>Données d'utilisation (logs, analytics) — uniquement si vous acceptez les cookies analytiques.</li>
        <li>Informations de compte (email, nom) si vous créez un compte.</li>
        <li>Données de paiement transmises à Stripe lors des achats (nous ne stockons pas vos données de carte).</li>
      </ul>

      <h2 className="text-xl font-semibold mt-6 mb-2">Cookies</h2>
      <p className="text-gray-300 mb-4">Nous utilisons des cookies essentiels au fonctionnement et des cookies analytiques facultatifs (Google Analytics / GTM). Vous pouvez accepter ou refuser les cookies analytiques via la bannière.</p>

      <h2 className="text-xl font-semibold mt-6 mb-2">Vos droits</h2>
      <p className="text-gray-300 mb-4">Vous pouvez demander accès, rectification, suppression de vos données, et retirer votre consentement aux cookies à tout moment en contactant notre équipe ou via les paramètres de votre navigateur.</p>

      <p className="text-gray-300 mt-6">Retour à <Link to="/" className="text-purple-400 underline">l'accueil</Link>.</p>
    </main>
  )
}
