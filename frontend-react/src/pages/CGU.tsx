import { useEffect } from 'react'
import { Link } from 'react-router-dom'

export default function CGU() {
  useEffect(() => {
    document.title = 'Conditions Générales d\'Utilisation (CGU)'
  }, [])
  return (
    <main className="max-w-4xl mx-auto px-6 py-16 text-white">
      <h1 className="text-3xl font-bold mb-4">Conditions Générales d'Utilisation (CGU)</h1>

      <p className="text-gray-300 mb-4">Les présentes Conditions Générales d'Utilisation régissent l'accès et l'utilisation du service AI Shorts Generator. En utilisant le service, vous acceptez ces conditions.</p>

      <h2 className="text-xl font-semibold mt-6 mb-2">1. Objet</h2>
      <p className="text-gray-300 mb-4">AI Shorts Generator propose des outils automatisés pour convertir des vidéos longues en courts extraits (shorts) à l'aide de traitements audiovisuels et d'IA.</p>

      <h2 className="text-xl font-semibold mt-6 mb-2">2. Accès et compte</h2>
      <p className="text-gray-300 mb-4">Certaines fonctionnalités nécessitent la création d'un compte. Vous êtes responsable de la confidentialité de vos identifiants et de toutes les activités effectuées depuis votre compte.</p>

      <h2 className="text-xl font-semibold mt-6 mb-2">3. Contenu utilisateur</h2>
      <p className="text-gray-300 mb-4">Vous garantissez avoir les droits nécessaires sur les vidéos que vous soumettez (droits d'auteur, droits des personnes). Vous vous engagez à ne pas soumettre de contenus illégaux, pornographiques, diffamatoires ou enfreignant les droits tiers.</p>

      <h2 className="text-xl font-semibold mt-6 mb-2">4. Propriété intellectuelle</h2>
      <p className="text-gray-300 mb-4">Nous conservons la propriété du code et des services fournis. Les clips générés restent soumis aux droits de leurs auteurs originaux ; l'utilisateur conserve la responsabilité quant à leur utilisation.</p>

      <h2 className="text-xl font-semibold mt-6 mb-2">5. Paiement et abonnements</h2>
      <p className="text-gray-300 mb-4">Les modalités de paiement (si applicables) sont précisées lors de la souscription. Les paiements sont gérés par des prestataires (ex. Stripe) et soumis à leurs conditions.</p>

      <h2 className="text-xl font-semibold mt-6 mb-2">6. Responsabilité</h2>
      <p className="text-gray-300 mb-4">Dans la limite permise par la loi, AI Shorts Generator n'est pas responsable des dommages indirects résultant de l'utilisation du service. Nous mettons tout en œuvre pour assurer la disponibilité et la qualité du service, mais des interruptions peuvent survenir.</p>

      <h2 className="text-xl font-semibold mt-6 mb-2">7. Résiliation</h2>
      <p className="text-gray-300 mb-4">Nous pouvons suspendre ou résilier un compte en cas de manquement aux CGU. Vous pouvez supprimer votre compte selon la procédure disponible dans les paramètres.</p>

      <h2 className="text-xl font-semibold mt-6 mb-2">8. Droit applicable</h2>
      <p className="text-gray-300 mb-4">Ces CGU sont régies par le droit français. En cas de litige, les tribunaux compétents seront ceux du ressort du siège social, sauf disposition contraire d'ordre public.</p>

      <p className="text-gray-300 mt-6">Retour à <Link to="/" className="text-purple-400 underline">l'accueil</Link>.</p>
    </main>
  )
}
