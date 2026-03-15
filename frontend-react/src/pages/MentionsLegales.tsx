import { Link } from 'react-router-dom'
import { useEffect } from 'react'

export default function MentionsLegales() {
  useEffect(() => {
    document.title = 'Mentions légales'
  }, [])
  return (
    <main className="max-w-4xl mx-auto px-6 py-16 text-white">
      <h1 className="text-3xl font-bold mb-4">Mentions légales</h1>

      <p className="text-gray-300 mb-4"><strong>AI Shorts Generator</strong><br/>Adresse : 1 Rue Exemple, 75000 Paris<br/>SIRET : 000 000 000<br/>Contact : <a href="mailto:aishortsgenerators@gmail.com" className="text-purple-300 underline">aishortsgenerators@gmail.com</a></p>

      <h2 className="text-xl font-semibold mt-6 mb-2">Éditeur</h2>
      <p className="text-gray-300 mb-4">Le site est édité par AI Shorts Generator, représenté par son directeur de publication.</p>

      <h2 className="text-xl font-semibold mt-6 mb-2">Hébergement</h2>
      <p className="text-gray-300 mb-4">Hébergeur : Exemple Host<br/>Adresse : 123 Rue de l'Hébergement<br/>Tél : +33 1 23 45 67 89</p>

      <h2 className="text-xl font-semibold mt-6 mb-2">Propriété intellectuelle</h2>
      <p className="text-gray-300 mb-4">L'ensemble du contenu du site (textes, logos, images, code) est la propriété d'AI Shorts Generator ou de ses partenaires et est protégé par le droit de la propriété intellectuelle. Toute reproduction est interdite sans autorisation expresse.</p>

      <h2 className="text-xl font-semibold mt-6 mb-2">Limitation de responsabilité</h2>
      <p className="text-gray-300 mb-4">AI Shorts Generator met tout en œuvre pour assurer l'exactitude des informations, mais ne peut garantir l'absence d'erreurs. L'utilisation du site se fait sous la seule responsabilité de l'utilisateur.</p>

      <p className="text-gray-300 mt-6">Retour à <Link to="/" className="text-purple-400 underline">l'accueil</Link>.</p>
    </main>
  )
}
