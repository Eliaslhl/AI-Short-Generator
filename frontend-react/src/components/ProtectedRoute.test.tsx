import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ProtectedRoute from './ProtectedRoute'

const mocks = vi.hoisted(() => ({ auth: vi.fn() }))

vi.mock('../context/AuthContext', () => ({ useAuth: mocks.auth }))

function renderRoute() {
  return render(
    <MemoryRouter initialEntries={['/protected']}>
      <Routes>
        <Route path="/login" element={<p>login</p>} />
        <Route path="/protected" element={<ProtectedRoute><p>protected content</p></ProtectedRoute>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('ProtectedRoute', () => {
  beforeEach(() => {
    mocks.auth.mockReturnValue({ retryAuth: vi.fn() })
  })

  it('waits for the initial auth check before redirecting or rendering protected content', () => {
    mocks.auth.mockReturnValue({ user: null, loading: true, authChecked: false, authError: null, retryAuth: vi.fn() })
    renderRoute()

    expect(screen.queryByText('login')).toBeNull()
    expect(screen.queryByText('protected content')).toBeNull()
  })

  it('does not mistake a session-check failure for a logout', () => {
    mocks.auth.mockReturnValue({
      user: null,
      loading: false,
      authChecked: true,
      authError: 'Unable to verify your session. Please try again.',
      retryAuth: vi.fn(),
    })
    renderRoute()

    expect(screen.getByText('Unable to verify your session. Please try again.')).toBeDefined()
    expect(screen.queryByText('login')).toBeNull()
  })
})
