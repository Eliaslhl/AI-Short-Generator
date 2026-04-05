import { Link } from 'react-router-dom'
import { useEffect } from 'react'

export default function MentionsLegales() {
  useEffect(() => {
    document.title = 'Legal Notice'
  }, [])
  return (
    <main className="max-w-4xl mx-auto px-6 py-16 text-white">
      <h1 className="text-3xl font-bold mb-4">Legal Notice</h1>

      <p className="text-gray-300 mb-4"><strong>AI Shorts Generator</strong><br/>Address: 4 rue des marronniers, Coutevroult 77580<br/>Phone: <a href="tel:+33669741360" className="text-purple-300 underline">06 69 74 13 60</a><br/>Contact: <a href="mailto:aishortsgenerators@gmail.com" className="text-purple-300 underline">aishortsgenerators@gmail.com</a></p>

      <h2 className="text-xl font-semibold mt-6 mb-2">Publisher</h2>
      <p className="text-gray-300 mb-4">This site is published by AI Shorts Generator, represented by its publication director.</p>

      <h2 className="text-xl font-semibold mt-6 mb-2">Hosting</h2>
      <p className="text-gray-300 mb-4">Host: Example Host<br/>Address: 123 Hosting Street<br/>Phone: +33 1 23 45 67 89</p>

      <h2 className="text-xl font-semibold mt-6 mb-2">Intellectual property</h2>
      <p className="text-gray-300 mb-4">All site content (text, logos, images, code) is the property of AI Shorts Generator or its partners and is protected by intellectual property law. Reproduction is prohibited without express permission.</p>

      <h2 className="text-xl font-semibold mt-6 mb-2">Limitation of liability</h2>
      <p className="text-gray-300 mb-4">AI Shorts Generator makes every effort to ensure information accuracy but cannot guarantee the absence of errors. Use of the site is at the user's sole risk.</p>

      <p className="text-gray-300 mt-6">Back to <Link to="/" className="text-purple-400 underline">home</Link>.</p>
    </main>
  )
}
