import { StrictMode } from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import AuthCallbackPage from './AuthCallbackPage'

const mocks = vi.hoisted(() => ({
  refreshUser: vi.fn(),
  showToast: vi.fn(),
}))

vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({ refreshUser: mocks.refreshUser }),
}))

vi.mock('../context/ToastContext', () => ({
  useToast: () => ({ showToast: mocks.showToast }),
}))

vi.mock('../hooks/useSeoTags', () => ({ useSeoTags: vi.fn() }))

function renderCallback(path = '/auth/callback') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/auth/callback" element={<AuthCallbackPage />} />
        <Route path="/dashboard" element={<p>dashboard</p>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('AuthCallbackPage', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('uses the pre-existing cookie session and ignores a legacy query token', async () => {
    mocks.refreshUser.mockResolvedValue({ id: 1 })
    window.history.replaceState({}, document.title, '/auth/callback?token=legacy-jwt')
    const replaceState = vi.spyOn(window.history, 'replaceState')

    renderCallback('/auth/callback?token=legacy-jwt')

    await screen.findByText('dashboard')
    expect(mocks.refreshUser).toHaveBeenCalledTimes(1)
    expect(localStorage.getItem('token')).toBeNull()
    expect(mocks.showToast).toHaveBeenCalledTimes(1)
    expect(replaceState).toHaveBeenCalledWith({}, document.title, window.location.pathname)
    replaceState.mockRestore()
    window.history.replaceState({}, document.title, '/')
  })

  it('shows a generic retry-safe failure without redirecting in a loop', async () => {
    mocks.refreshUser.mockRejectedValue(new Error('backend detail'))

    renderCallback()

    await screen.findByText('Unable to complete Google sign-in.')
    expect(mocks.refreshUser).toHaveBeenCalledTimes(1)
    expect(screen.queryByText('backend detail')).toBeNull()
  })

  it('does not duplicate the callback exchange during StrictMode effect replay', async () => {
    mocks.refreshUser.mockResolvedValue({ id: 1 })

    render(
      <StrictMode>
        <MemoryRouter initialEntries={['/auth/callback']}>
          <Routes>
            <Route path="/auth/callback" element={<AuthCallbackPage />} />
            <Route path="/dashboard" element={<p>dashboard</p>} />
          </Routes>
        </MemoryRouter>
      </StrictMode>,
    )

    await waitFor(() => expect(mocks.refreshUser).toHaveBeenCalledTimes(1))
  })
})
