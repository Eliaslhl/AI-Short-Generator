import { useEffect } from 'react'
import { Link } from 'react-router-dom'

export default function CookiesPolicy() {
  useEffect(() => {
    document.title = 'Politique des cookies'
  }, [])
  return (
    <main className="max-w-4xl mx-auto px-6 py-16 text-white">
      <h1 className="text-3xl font-bold mb-4">Politique des cookies</h1>
      <p className="text-gray-300 mb-4">Nous utilisons des cookies et des technologies similaires pour rendre le site fonctionnel, mesurer l'audience et personnaliser l'expérience. Cette page explique les types de cookies utilisés, leur finalité et comment gérer vos préférences.</p>

      <h2 className="text-xl font-semibold mt-6 mb-2">Types de cookies utilisés</h2>
      <ul className="list-disc ml-6 text-gray-300 mb-4">
        <li><strong>Cookies essentiels :</strong> nécessaires au fonctionnement du site (ex. session, authentification).</li>
        <li><strong>Cookies de performance / analytiques :</strong> utilisés pour mesurer l'audience et améliorer le service (ex. Google Analytics).</li>
        <li><strong>Cookies fonctionnels :</strong> pour mémoriser vos préférences (ex. langue, préférence d'affichage).</li>
      </ul>

      <h2 className="text-xl font-semibold mt-6 mb-2">Exemples de cookies</h2>
      <ul className="list-disc ml-6 text-gray-300 mb-4">
        <li><code>session</code> — cookie de session pour garder l'utilisateur connecté (essentiel).</li>
        <li><code>_ga, _gid</code> — Google Analytics (analytiques, facultatif).</li>
      </ul>

      <h2 className="text-xl font-semibold mt-6 mb-2">Consentement et gestion</h2>
      <p className="text-gray-300 mb-4">Au premier accès, une bannière vous permet d'accepter ou de refuser les cookies analytiques. Vous pouvez modifier votre choix à tout moment via les paramètres de cookies (si disponibles) ou en configurant votre navigateur pour bloquer/corriger les cookies.</p>

      <h2 className="text-xl font-semibold mt-6 mb-2">Désactivation via le navigateur</h2>
      <p className="text-gray-300 mb-4">La plupart des navigateurs permettent de gérer ou de supprimer les cookies (préférences → vie privée). Notez que la désactivation des cookies essentiels peut affecter le fonctionnement du site.</p>

      <p className="text-gray-300 mt-6">Retour à <Link to="/" className="text-purple-400 underline">l'accueil</Link>.</p>
    </main>
  )
}
