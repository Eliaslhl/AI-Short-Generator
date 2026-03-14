import { useEffect, useState } from 'react'

export default function CookieConsent() {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    try {
      const seen = localStorage.getItem('cookie_consent')
      if (!seen) setVisible(true)
    } catch (e) {
      setVisible(true)
    }
  }, [])

  function accept() {
    try { localStorage.setItem('cookie_consent', 'true') } catch (e) {}
    // notify index.html script to load analytics
    try { window.dispatchEvent(new Event('cookie-consent')) } catch (e) {}
    setVisible(false)
  }

  function decline() {
    try { localStorage.setItem('cookie_consent', 'false') } catch (e) {}
    setVisible(false)
  }

  if (!visible) return null

  return (
    <div className="fixed bottom-4 left-4 right-4 md:left-auto md:right-6 md:bottom-6 z-50">
      <div className="max-w-3xl mx-auto bg-black/80 backdrop-blur-md text-white p-4 rounded-lg flex flex-col md:flex-row items-start md:items-center gap-3">
        <div className="flex-1 text-sm">
          Nous utilisons des cookies pour améliorer votre expérience et analyser le trafic. Acceptez-vous les cookies analytiques (Google Analytics) ?
        </div>
        <div className="flex-shrink-0 flex gap-2">
          <button onClick={decline} className="px-3 py-2 bg-white/5 text-gray-200 rounded-lg">Refuser</button>
          <button onClick={accept} className="px-3 py-2 bg-purple-600 text-white rounded-lg">Accepter</button>
        </div>
      </div>
    </div>
  )
}
