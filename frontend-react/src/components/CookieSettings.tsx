type Props = {
  open: boolean
  onClose: () => void
}

export default function CookieSettings({ open, onClose }: Props) {
  if (!open) return null

  function revoke() {
    // 1. Set localStorage flag to false
    try { localStorage.setItem('cookie_consent', 'false') } catch (e) {}

    // 2. Remove all tracking-related cookies
    try {
      const cookiesToRemove = ['_ga', '_gid', '_gat', '__utma', '__utmb', '__utmc', '__utmt', '__utmz', '_ga_*']
      cookiesToRemove.forEach(name => {
        // Remove from root domain
        document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`
        document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; domain=${window.location.hostname};`
        // Also try removing from parent domain
        const domain = window.location.hostname.split('.').slice(-2).join('.')
        if (domain !== window.location.hostname) {
          document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; domain=${domain};`
        }
      })
    } catch (e) {}

    // 3. Remove analytics scripts if present
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

    // 4. Show confirmation message
    alert('✅ Cookies analytiques révoqués. Les scripts de suivi ont été supprimés.')
    onClose()
  }

  return (
    <>
      <style>{`
        @keyframes slideDownFade {
          from {
            opacity: 0;
            transform: translateY(-30px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        .cookie-modal {
          animation: slideDownFade 0.3s ease-out;
        }
      `}</style>
      <div className="fixed inset-0 z-60 flex items-end sm:items-center justify-center p-0 sm:p-4">
        <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
        <div className="cookie-modal relative w-full sm:max-w-md bg-gray-900 text-white rounded-t-2xl sm:rounded-xl shadow-2xl z-10 border-t sm:border border-white/10 p-6 sm:p-8 max-h-[90vh] overflow-y-auto">
          <button 
            onClick={onClose}
            className="absolute top-3 right-3 sm:top-4 sm:right-4 text-gray-400 hover:text-white transition text-xl"
          >
            ✕
          </button>
          
          <h3 className="text-lg sm:text-xl font-bold mb-3 pr-8">Gérer les cookies</h3>
          <div className="space-y-4 mb-6">
            <p className="text-xs sm:text-sm text-gray-300 leading-relaxed">
              Nous utilisons des cookies pour améliorer votre expérience et analyser le trafic.
            </p>
            <p className="text-xs sm:text-sm text-gray-300 leading-relaxed">
              Vous pouvez révoquer votre consentement aux cookies analytiques. Cela supprimera les scripts de suivi chargés et empêchera de futurs chargements.
            </p>
          </div>

          <div className="flex gap-2 flex-col-reverse sm:flex-row sm:justify-end">
            <button 
              onClick={onClose} 
              className="px-4 py-2.5 bg-gray-700 hover:bg-gray-600 rounded-lg text-xs sm:text-sm font-medium transition"
            >
              Fermer
            </button>
            <button 
              onClick={revoke} 
              className="px-4 py-2.5 bg-red-600 hover:bg-red-700 rounded-lg text-xs sm:text-sm font-medium transition shadow-lg"
            >
              Révoquer
            </button>
          </div>
        </div>
      </div>
    </>
  )
}
