import { useEffect, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { useSeoTags } from '../hooks/useSeoTags'

// Handles the redirect from Google OAuth: /auth/callback?token=XXX
export default function AuthCallbackPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { refreshUser } = useAuth()
  const { showToast } = useToast()
  const handled = useRef(false)

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

    const token = searchParams.get('token')
    if (token) {
      localStorage.setItem('token', token)
      refreshUser()
        .then(() => {
          showToast('Google sign-in successful 👋', 'success')
          navigate('/dashboard', { replace: true })
        })
        .catch(() => navigate('/login', { replace: true }))
    } else {
      navigate('/login', { replace: true })
    }
  }, [navigate, refreshUser, searchParams, showToast])

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center">
      <div className="text-center">
        <div className="w-10 h-10 border-2 border-purple-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-gray-400">Signing in...</p>
      </div>
    </div>
  )
}
