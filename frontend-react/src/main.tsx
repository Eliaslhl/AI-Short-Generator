import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import ErrorBoundary from './components/ErrorBoundary'

// Global error handlers (dev-friendly) — capture uncaught errors and promise rejections
if (typeof window !== 'undefined') {
  window.addEventListener('error', (ev) => {
    // eslint-disable-next-line no-console
    console.error('Global window error:', ev.error ?? ev.message, ev)
  })
  window.addEventListener('unhandledrejection', (ev) => {
    // eslint-disable-next-line no-console
    console.error('Unhandled promise rejection:', ev.reason)
  })
}

// eslint-disable-next-line @typescript-eslint/no-non-null-assertion
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </StrictMode>,
)
