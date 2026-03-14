type Props = {
  open: boolean
  onClose: () => void
}

export default function CookieSettings({ open, onClose }: Props) {
  if (!open) return null

  function revoke() {
    try { localStorage.setItem('cookie_consent', 'false') } catch (e) {}
    // remove analytics scripts if present
    try {
      Array.from(document.querySelectorAll('script')).forEach(s => {
        const src = (s as HTMLScriptElement).src || ''
        if (src.includes('googletagmanager.com') || src.includes('gtag/js')) s.remove()
      })
      // clear dataLayer/gtag shim
      try { delete (window as any).gtag } catch (e) {}
      try { delete (window as any).dataLayer } catch (e) {}
      ;(window as any).__ai_shorts_gtm_loaded = false
      window.dispatchEvent(new Event('cookie-consent-removed'))
    } catch (e) {}
    onClose()
  }

  return (
    <div className="fixed inset-0 z-60 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className="relative max-w-lg w-full bg-gray-900 text-white rounded-lg p-6 z-10">
        <h3 className="text-lg font-semibold mb-2">Gérer les cookies</h3>
        <p className="text-sm text-gray-300 mb-4">Vous pouvez révoquer votre consentement aux cookies analytiques. Cela supprimera les scripts de suivi chargés et empêchera de futurs chargements tant que vous n'aurez pas accepté à nouveau.</p>

        <div className="flex gap-2 justify-end">
          <button onClick={onClose} className="px-3 py-2 bg-white/5 rounded text-sm">Fermer</button>
          <button onClick={revoke} className="px-3 py-2 bg-red-600 rounded text-sm">Révoquer le consentement</button>
        </div>
      </div>
    </div>
  )
}
