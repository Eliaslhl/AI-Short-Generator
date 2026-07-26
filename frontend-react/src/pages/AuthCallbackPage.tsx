import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { useSeoTags } from '../hooks/useSeoTags'

// The backend has already set the HttpOnly session cookie before this route loads.
export default function AuthCallbackPage() {
  const navigate = useNavigate()
  const { refreshUser } = useAuth()
  const { showToast } = useToast()
  const handled = useRef(false)
  const [failed, setFailed] = useState(false)

  useSeoTags({
    title: 'Auth Callback - AI Shorts Generator',
    description: 'Processing authentication...',
  })

  // Add noindex meta tag
  useEffect(() => {
    let robotsMeta = document.querySelector('meta[name="robots"]')
    if (!robotsMeta) {
      robotsMeta = document.createElement('meta')
      robotsMeta.setAttribute('name', 'robots')
      document.head.appendChild(robotsMeta)
    }
    robotsMeta.setAttribute('content', 'noindex, nofollow')
  }, [])

  useEffect(() => {
    if (handled.current) return
    handled.current = true

    // Legacy callbacks may still contain a JWT query parameter. Never read it;
    // remove all callback query data before the authenticated session check.
    if (window.location.search) {
      window.history.replaceState({}, document.title, window.location.pathname)
    }

    refreshUser()
      .then(() => {
        showToast('Google sign-in successful 👋', 'success')
        navigate('/dashboard', { replace: true })
      })
      .catch(() => {
        // Do not surface backend details or automatically redirect into a callback loop.
        setFailed(true)
      })
  }, [navigate, refreshUser, showToast])

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center">
      <div className="text-center">
        <div className="w-10 h-10 border-2 border-purple-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        {failed ? (
          <>
            <p className="text-gray-400">Unable to complete Google sign-in.</p>
            <button
              type="button"
              onClick={() => navigate('/login', { replace: true })}
              className="mt-4 rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-500"
            >
              Back to sign in
            </button>
          </>
        ) : (
          <p className="text-gray-400">Signing in...</p>
        )}
      </div>
    </div>
  )
}
