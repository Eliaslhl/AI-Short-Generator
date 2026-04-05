import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useSeoTags } from '../hooks/useSeoTags'

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export default function ConfirmEmailPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [message, setMessage] = useState('')

  useSeoTags({
    title: 'Confirm Email - AI Shorts Generator',
    description: 'Confirm your email address to activate your account.',
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
    const confirmEmail = async () => {
      const token = searchParams.get('token')
      
      if (!token) {
        setStatus('error')
        setMessage('No confirmation token found')
        return
      }

      try {
        const response = await fetch(`${API_BASE}/auth/confirm-email`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ token }),
        })

        const data = await response.json()

        if (!response.ok) {
          setStatus('error')
          setMessage(data.detail || 'Failed to confirm email')
          return
        }

        // Save token to localStorage
        if (data.access_token) {
          localStorage.setItem('access_token', data.access_token)
          localStorage.setItem('token_type', data.token_type)
        }

        setStatus('success')
        setMessage(data.message || 'Email confirmed successfully!')
        
        // Redirect to dashboard after 2 seconds
        setTimeout(() => {
          navigate('/dashboard')
        }, 2000)
      } catch (error) {
        setStatus('error')
        setMessage('An error occurred while confirming your email')
        console.error('Confirmation error:', error)
      }
    }

    confirmEmail()
  }, [searchParams, navigate])

  return (
    <div className="min-h-screen bg-black flex items-center justify-center px-4">
      <div className="max-w-md w-full">
        {status === 'loading' && (
          <div className="text-center">
            <div className="inline-block">
              <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-purple-500"></div>
            </div>
            <p className="mt-4 text-white text-lg">Confirming your email...</p>
          </div>
        )}

        {status === 'success' && (
          <div className="text-center">
            <div className="inline-block">
              <span className="text-5xl">✓</span>
            </div>
            <h1 className="mt-4 text-2xl font-bold text-white">Email Confirmed!</h1>
            <p className="mt-2 text-gray-300">{message}</p>
            <p className="mt-4 text-sm text-gray-400">Redirecting to dashboard...</p>
          </div>
        )}

        {status === 'error' && (
          <div className="text-center">
            <div className="inline-block">
              <span className="text-5xl">✕</span>
            </div>
            <h1 className="mt-4 text-2xl font-bold text-white">Confirmation Failed</h1>
            <p className="mt-2 text-gray-300">{message}</p>
            <button
              onClick={() => navigate('/login')}
              className="mt-6 w-full py-2 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white font-semibold rounded-lg transition"
            >
              Back to Login
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
