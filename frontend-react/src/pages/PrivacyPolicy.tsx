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

      <p className="text-gray-300 mb-4">La présente politique de confidentialité décrit comment <strong>AI Shorts Generator</strong> collecte, utilise et protège vos données personnelles lorsque vous utilisez notre service. Nous nous engageons à respecter les dispositions applicables du Règlement Général sur la Protection des Données (RGPD) pour les utilisateurs situés dans l'Union européenne.</p>

      <h2 className="text-xl font-semibold mt-6 mb-2">1. Responsable du traitement</h2>
      <p className="text-gray-300 mb-4">Responsable : AI Shorts Generator<br/>Contact : <a href="mailto:aishortsgenerators@gmail.com" className="text-purple-300 underline">aishortsgenerators@gmail.com</a><br/>Adresse : 1 Rue Exemple, 75000 Paris</p>

      <h2 className="text-xl font-semibold mt-6 mb-2">2. Données collectées et finalités</h2>
      <ul className="list-disc ml-6 text-gray-300 mb-4">
        <li><strong>Données de compte :</strong> email, nom, informations de profil — pour gérer votre compte et l'authentification.</li>
        <li><strong>Données d'usage :</strong> logs d'accès, statistiques d'utilisation — pour améliorer le service et détecter les abus.</li>
        <li><strong>Données de génération :</strong> métadonnées liées aux vidéos/clips (titres, timestamps) — nécessaires au fonctionnement du service.</li>
        <li><strong>Données de paiement :</strong> lorsque vous effectuez un paiement, les données de paiement sont traitées par Stripe et ne sont pas stockées sur nos serveurs.</li>
      </ul>

      <h2 className="text-xl font-semibold mt-6 mb-2">3. Base juridique</h2>
      <p className="text-gray-300 mb-4">Nous traitons vos données lorsque cela est nécessaire pour l'exécution du contrat (ex. fourniture du service), pour respecter une obligation légale, pour nos intérêts légitimes (amélioration du service, sécurité), ou lorsque vous avez donné votre consentement (ex. cookies analytiques).</p>

      <h2 className="text-xl font-semibold mt-6 mb-2">4. Destinataires</h2>
      <p className="text-gray-300 mb-4">Les sous-traitants peuvent inclure des prestataires d'hébergement, des services d'analyse (si activés) et des prestataires de paiement (Stripe). Nous exigeons des garanties contractuelles pour protéger vos données.</p>

      <h2 className="text-xl font-semibold mt-6 mb-2">5. Durée de conservation</h2>
      <p className="text-gray-300 mb-4">Les données de compte sont conservées tant que votre compte existe. Les logs et données d'usage sont conservés pendant une durée limitée (ex. 12 mois) sauf nécessité légale de conservation plus longue. Les clips et fichiers générés sont stockés conformément à notre politique d'expiration (par défaut 1 heure dans l'historique, mais les fichiers peuvent être conservés plus longtemps selon la configuration du déploiement).</p>

      <h2 className="text-xl font-semibold mt-6 mb-2">6. Vos droits</h2>
      <p className="text-gray-300 mb-4">Conformément au RGPD, vous disposez des droits suivants : accès, rectification, effacement, limitation du traitement, opposition, portabilité. Pour exercer ces droits, contactez-nous à <a href="mailto:aishortsgenerators@gmail.com" className="text-purple-300 underline">aishortsgenerators@gmail.com</a>. Nous répondrons dans les délais légaux.</p>

      <h2 className="text-xl font-semibold mt-6 mb-2">7. Sécurité</h2>
      <p className="text-gray-300 mb-4">Nous mettons en place des mesures techniques et organisationnelles appropriées (chiffrement en transit, accès restreint, sauvegardes) pour protéger vos données.</p>

      <h2 className="text-xl font-semibold mt-6 mb-2">8. Cookies et suivi</h2>
      <p className="text-gray-300 mb-4">Nous utilisons des cookies essentiels au fonctionnement du site et des cookies analytiques facultatifs. Vous pouvez gérer vos préférences via la bannière de cookies. Consultez notre <a href="/legal/cookies" className="text-purple-300 underline">Politique des cookies</a> pour plus d'informations.</p>

      <h2 className="text-xl font-semibold mt-6 mb-2">9. Contact et réclamations</h2>
      <p className="text-gray-300 mb-4">Pour toute question relative à la protection des données : <a href="mailto:aishortsgenerators@gmail.com" className="text-purple-300 underline">aishortsgenerators@gmail.com</a>. Vous pouvez également déposer une réclamation auprès de l'autorité de contrôle compétente (ex. CNIL en France).</p>

      <p className="text-gray-300 mt-6">Retour à <Link to="/" className="text-purple-400 underline">l'accueil</Link>.</p>
    </main>
  )
}

