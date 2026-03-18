import { useEffect } from 'react'
import { Link } from 'react-router-dom'

export default function CookiesPolicy() {
  useEffect(() => {
    document.title = 'Cookies Policy'
  }, [])
  return (
    <main className="max-w-4xl mx-auto px-6 py-16 text-white">
      <h1 className="text-3xl font-bold mb-4">Cookies Policy</h1>
      <p className="text-gray-300 mb-4">We use cookies and similar technologies to make the site work, measure usage, and personalize the experience. This page explains the types of cookies used, their purposes, and how to manage your preferences.</p>

      <h2 className="text-xl font-semibold mt-6 mb-2">Types of cookies used</h2>
      <ul className="list-disc ml-6 text-gray-300 mb-4">
        <li><strong>Essential cookies:</strong> required for site functionality (e.g., session, authentication).</li>
        <li><strong>Performance / analytics cookies:</strong> used to measure usage and improve the service (e.g., Google Analytics).</li>
        <li><strong>Functional cookies:</strong> used to remember your preferences (e.g., language, display settings).</li>
      </ul>

      <h2 className="text-xl font-semibold mt-6 mb-2">Examples of cookies</h2>
      <ul className="list-disc ml-6 text-gray-300 mb-4">
        <li><code>session</code> — session cookie to keep the user signed in (essential).</li>
        <li><code>_ga, _gid</code> — Google Analytics (analytics, optional).</li>
      </ul>

      <h2 className="text-xl font-semibold mt-6 mb-2">Consent and management</h2>
      <p className="text-gray-300 mb-4">On first visit a banner allows you to accept or decline analytics cookies. You can change your choice at any time via cookie settings (if available) or by configuring your browser to block or remove cookies.</p>

      <h2 className="text-xl font-semibold mt-6 mb-2">Disabling via browser</h2>
      <p className="text-gray-300 mb-4">Most browsers let you manage or remove cookies (settings → privacy). Note that disabling essential cookies may affect site functionality.</p>

      <p className="text-gray-300 mt-6">Back to <Link to="/" className="text-purple-400 underline">home</Link>.</p>
    </main>
  )
}
