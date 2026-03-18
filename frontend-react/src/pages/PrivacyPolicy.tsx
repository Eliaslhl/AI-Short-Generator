import { useEffect } from 'react'
import { Link } from 'react-router-dom'

export default function PrivacyPolicy() {
  useEffect(() => {
    document.title = 'Privacy Policy'
    const meta = document.querySelector('meta[name="description"]')
    if (meta) meta.setAttribute('content', 'Privacy policy for AI Shorts Generator — how we collect and process data, cookies and user information.')
  }, [])

  return (
    <main className="max-w-4xl mx-auto px-6 py-16 text-white">
      <h1 className="text-3xl font-bold mb-4">Privacy Policy</h1>

      <p className="text-gray-300 mb-4">This privacy policy explains how <strong>AI Shorts Generator</strong> collects, uses and protects your personal data when you use our service. We are committed to complying with applicable data protection laws, such as the GDPR for users in the European Union.</p>

      <h2 className="text-xl font-semibold mt-6 mb-2">1. Data controller</h2>
      <p className="text-gray-300 mb-4">Controller: AI Shorts Generator<br/>Contact: <a href="mailto:aishortsgenerators@gmail.com" className="text-purple-300 underline">aishortsgenerators@gmail.com</a><br/>Address: 1 Example Street, 75000 Paris</p>

      <h2 className="text-xl font-semibold mt-6 mb-2">2. Data collected and purposes</h2>
      <ul className="list-disc ml-6 text-gray-300 mb-4">
        <li><strong>Account data:</strong> email, name, profile info — to manage your account and authentication.</li>
        <li><strong>Usage data:</strong> access logs, usage statistics — to improve the service and detect abuse.</li>
        <li><strong>Generation data:</strong> metadata related to videos/clips (titles, timestamps) — necessary for the service to function.</li>
        <li><strong>Payment data:</strong> when you make a payment, payment details are processed by Stripe and are not stored on our servers.</li>
      </ul>

      <h2 className="text-xl font-semibold mt-6 mb-2">3. Legal basis</h2>
      <p className="text-gray-300 mb-4">We process your data when necessary for contract performance (e.g., providing the service), to comply with legal obligations, for our legitimate interests (service improvement, security), or when you have given consent (e.g., analytics cookies).</p>

      <h2 className="text-xl font-semibold mt-6 mb-2">4. Recipients</h2>
      <p className="text-gray-300 mb-4">Processors may include hosting providers, analytics services (if enabled) and payment providers (Stripe). We require contractual safeguards to protect your data.</p>

      <h2 className="text-xl font-semibold mt-6 mb-2">5. Data retention</h2>
      <p className="text-gray-300 mb-4">Account data is retained while your account exists. Logs and usage data are retained for a limited period (e.g., 12 months) unless legal requirements demand longer retention. Generated clips and files are stored according to our expiration policy (default 1 hour in history, but may vary based on deployment configuration).</p>

      <h2 className="text-xl font-semibold mt-6 mb-2">6. Your rights</h2>
      <p className="text-gray-300 mb-4">Subject to applicable law, you have rights such as access, rectification, deletion, restriction of processing, objection, and portability. To exercise these rights contact us at <a href="mailto:aishortsgenerators@gmail.com" className="text-purple-300 underline">aishortsgenerators@gmail.com</a>. We will respond within statutory timeframes.</p>

      <h2 className="text-xl font-semibold mt-6 mb-2">7. Security</h2>
      <p className="text-gray-300 mb-4">We implement appropriate technical and organizational measures (encryption in transit, restricted access, backups) to protect your data.</p>

      <h2 className="text-xl font-semibold mt-6 mb-2">8. Cookies and tracking</h2>
      <p className="text-gray-300 mb-4">We use essential cookies required for site operation and optional analytics cookies. You can manage your preferences via the cookie banner. See our <a href="/legal/cookies" className="text-purple-300 underline">Cookies Policy</a> for details.</p>

      <h2 className="text-xl font-semibold mt-6 mb-2">9. Contact and complaints</h2>
      <p className="text-gray-300 mb-4">For questions about data protection: <a href="mailto:aishortsgenerators@gmail.com" className="text-purple-300 underline">aishortsgenerators@gmail.com</a>. You may also file a complaint with the competent supervisory authority.</p>

      <p className="text-gray-300 mt-6">Back to <Link to="/" className="text-purple-400 underline">home</Link>.</p>
    </main>
  )
}

