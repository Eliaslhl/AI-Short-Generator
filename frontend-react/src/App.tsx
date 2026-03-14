import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
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
import DashboardPage from './pages/DashboardPage'
import AuthCallbackPage from './pages/AuthCallbackPage'
import YoutubeShortsGenerator from './pages/YoutubeShortsGenerator'
import YoutubeVideoToShorts from './pages/YoutubeVideoToShorts'
import AiClipGenerator from './pages/AiClipGenerator'

export default function App() {
  return (
    <BrowserRouter>
      <ToastProvider>
        <AuthProvider>
          <div className="min-h-screen w-full bg-gray-950 text-white">
            <Navbar />
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

              {/* Protected */}
              <Route path="/generate" element={
                <ProtectedRoute><GeneratorPage /></ProtectedRoute>
              } />
              <Route path="/dashboard" element={
                <ProtectedRoute><DashboardPage /></ProtectedRoute>
              } />

              {/* Fallback */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </div>
        </AuthProvider>
      </ToastProvider>
    </BrowserRouter>
  )
}

