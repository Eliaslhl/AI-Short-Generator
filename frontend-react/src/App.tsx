import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { useEffect } from 'react'
import { AuthProvider } from './context/AuthContext'
import { ToastProvider } from './context/ToastContext'
import Navbar from './components/Navbar'
import ProtectedRoute from './components/ProtectedRoute'
import LandingPage from './pages/LandingPage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import ForgotPasswordPage from './pages/ForgotPasswordPage'
import ResetPasswordPage from './pages/ResetPasswordPage'
import GeneratorPage from './pages/GeneratorPage'
import SourceSelectorPage from './pages/SourceSelectorPage'
import YouTubeGeneratorPage from './pages/YouTubeGeneratorPage'
import TwitchGeneratorPage from './pages/TwitchGeneratorPage'
import DashboardPage from './pages/DashboardPage'
import AuthCallbackPage from './pages/AuthCallbackPage'
import YoutubeShortsGenerator from './pages/YoutubeShortsGenerator'
import YoutubeVideoToShorts from './pages/YoutubeVideoToShorts'
import AiClipGenerator from './pages/AiClipGenerator'
import AiShortsGeneratorSEO from './pages/seo/AiShortsGeneratorSEO'
import YoutubeShortsGeneratorSEO from './pages/seo/YoutubeShortsGeneratorSEO'
import ConvertYoutubeToShortsSEO from './pages/seo/ConvertYoutubeToShortsSEO'
import CookieConsent from './components/CookieConsent'
import PrivacyPolicy from './pages/PrivacyPolicy'
import MentionsLegales from './pages/MentionsLegales'
import CGU from './pages/CGU'
import CookiesPolicy from './pages/CookiesPolicy'
import SitemapPage from './pages/SitemapPage'
import JobDetailPage from './pages/JobDetailPage'
import Footer from './components/Footer'
import LegalHub from './pages/LegalHub'

export default function App() {
  // Scroll to hash on navigation (e.g. /#pricing) to support SPA anchor links
  function ScrollToHash() {
    const { hash, pathname } = useLocation()
    useEffect(() => {
      if (!hash) return
      // small timeout to allow route renders, then retry via RAF until element is mounted
      const id = hash.replace('#', '')
      let mounted = true

      const tryScroll = () => {
        try {
          const el = document.getElementById(id)
          if (el && typeof (el as Element).scrollIntoView === 'function') {
            ;(el as Element).scrollIntoView({ behavior: 'smooth', block: 'start' })
            return
          }
        } catch (e) {
          // ignore any DOM errors
        }
        if (mounted) requestAnimationFrame(tryScroll)
      }

      const t = setTimeout(tryScroll, 50)
      return () => {
        mounted = false
        clearTimeout(t)
      }
    }, [hash, pathname])
    return null
  }

  return (
    <BrowserRouter>
      <ScrollToHash />
      <ToastProvider>
        <AuthProvider>
          <div className="min-h-screen w-full bg-gray-950 text-white">
            <Navbar />
            <CookieConsent />
            <Routes>
              {/* Public */}
              <Route path="/" element={<LandingPage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route path="/forgot-password" element={<ForgotPasswordPage />} />
              <Route path="/reset-password" element={<ResetPasswordPage />} />
              <Route path="/auth/callback" element={<AuthCallbackPage />} />
              <Route path="/youtube-shorts-generator" element={<YoutubeShortsGenerator />} />
              <Route path="/youtube-video-to-shorts" element={<YoutubeVideoToShorts />} />
              <Route path="/ai-clip-generator" element={<AiClipGenerator />} />

              {/* SEO landing pages */}
              <Route path="/seo/ai-shorts-generator" element={<AiShortsGeneratorSEO />} />
              <Route path="/seo/youtube-shorts-generator" element={<YoutubeShortsGeneratorSEO />} />
              <Route path="/seo/convert-youtube-to-shorts" element={<ConvertYoutubeToShortsSEO />} />

              {/* Protected */}
              <Route path="/generate" element={<ProtectedRoute><SourceSelectorPage /></ProtectedRoute>} />
              <Route path="/generate/youtube" element={<ProtectedRoute><YouTubeGeneratorPage /></ProtectedRoute>} />
              <Route path="/generate/twitch" element={<ProtectedRoute><TwitchGeneratorPage /></ProtectedRoute>} />
              <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
              <Route path="/jobs/:jobId" element={<ProtectedRoute><JobDetailPage /></ProtectedRoute>} />

              {/* Individual legal pages (each has its own URL) */}
              <Route path="/privacy" element={<PrivacyPolicy />} />
              <Route path="/sitemap" element={<SitemapPage />} />

              <Route path="/legal/mentions" element={<MentionsLegales />} />
              <Route path="/legal/cgu" element={<CGU />} />
              <Route path="/legal/privacy" element={<PrivacyPolicy />} />
              <Route path="/legal/cookies" element={<CookiesPolicy />} />
              <Route path="/legal/sitemap" element={<SitemapPage />} />

              {/* Legal hub routes: renders the navigation + content */}
              <Route path="/legal" element={<LegalHub />} />
              <Route path="/legal/:page" element={<LegalHub />} />

              {/* Fallback */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
            <Footer />
           </div>
         </AuthProvider>
       </ToastProvider>
     </BrowserRouter>
   )
 }

