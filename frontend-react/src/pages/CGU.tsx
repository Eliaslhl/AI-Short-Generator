import { useEffect } from 'react'
import { Link } from 'react-router-dom'

export default function CGU() {
  useEffect(() => {
    document.title = 'Terms of Use'
  }, [])
  return (
    <main className="max-w-4xl mx-auto px-6 py-16 text-white">
      <h1 className="text-3xl font-bold mb-4">Terms of Use</h1>

      <p className="text-gray-300 mb-4">These Terms of Use govern access to and use of the AI Shorts Generator service. By using the service you agree to these terms.</p>

      <h2 className="text-xl font-semibold mt-6 mb-2">1. Purpose</h2>
      <p className="text-gray-300 mb-4">AI Shorts Generator provides automated tools to convert long videos into short clips (shorts) using audio-visual processing and AI.</p>

      <h2 className="text-xl font-semibold mt-6 mb-2">2. Access and account</h2>
      <p className="text-gray-300 mb-4">Some features require an account. You are responsible for keeping your credentials confidential and for all activities that occur under your account.</p>

      <h2 className="text-xl font-semibold mt-6 mb-2">3. User content</h2>
      <p className="text-gray-300 mb-4">You warrant that you have the necessary rights for any videos you submit (copyright, personality rights). You agree not to submit illegal, pornographic, defamatory, or other content that infringes third-party rights.</p>

      <h2 className="text-xl font-semibold mt-6 mb-2">4. Intellectual property</h2>
      <p className="text-gray-300 mb-4">We retain ownership of the service code and related assets. Generated clips may remain subject to their original authors' rights; users remain responsible for how they use generated content.</p>

      <h2 className="text-xl font-semibold mt-6 mb-2">5. Payments and subscriptions</h2>
      <p className="text-gray-300 mb-4">If applicable, payment terms are presented at checkout. Payments are handled by third-party providers (e.g., Stripe) and are subject to their terms.</p>

      <h2 className="text-xl font-semibold mt-6 mb-2">6. Liability</h2>
      <p className="text-gray-300 mb-4">To the extent permitted by law, AI Shorts Generator is not liable for indirect damages arising from use of the service. We strive to ensure availability and quality, but interruptions may occur.</p>

      <h2 className="text-xl font-semibold mt-6 mb-2">7. Termination</h2>
      <p className="text-gray-300 mb-4">We may suspend or terminate accounts for violations of these terms. You may delete your account according to the procedure available in settings.</p>

      <h2 className="text-xl font-semibold mt-6 mb-2">8. Governing law</h2>
      <p className="text-gray-300 mb-4">These Terms are governed by applicable law. Disputes will be resolved by the competent courts, except where mandatory public law provides otherwise.</p>

      <p className="text-gray-300 mt-6">Back to <Link to="/" className="text-purple-400 underline">home</Link>.</p>
    </main>
  )
}
