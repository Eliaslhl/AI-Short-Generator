import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ConfirmEmailPage from './ConfirmEmailPage'

const mocks = vi.hoisted(() => ({
  confirmEmail: vi.fn(),
  establishSession: vi.fn(),
}))

vi.mock('../api', () => ({ authApi: { confirmEmail: mocks.confirmEmail } }))
vi.mock('../context/AuthContext', () => ({ useAuth: () => ({ establishSession: mocks.establishSession }) }))
vi.mock('../hooks/useSeoTags', () => ({ useSeoTags: vi.fn() }))

describe('ConfirmEmailPage', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('exchanges the confirmation JWT for a cookie session without persisting it', async () => {
    mocks.confirmEmail.mockResolvedValue({
      data: { access_token: 'temporary-jwt', token_type: 'bearer', user: {}, message: 'confirmed' },
    })
    mocks.establishSession.mockResolvedValue({})

    render(
      <MemoryRouter initialEntries={['/confirm-email?token=email-confirmation-token']}>
        <Routes><Route path="/confirm-email" element={<ConfirmEmailPage />} /></Routes>
      </MemoryRouter>,
    )

    await screen.findByText('Email Confirmed!')
    expect(mocks.confirmEmail).toHaveBeenCalledWith('email-confirmation-token')
    expect(mocks.establishSession).toHaveBeenCalledWith('temporary-jwt')
    expect(localStorage.getItem('access_token')).toBeNull()
    expect(localStorage.getItem('token_type')).toBeNull()
  })

  it('uses a generic failure message', async () => {
    mocks.confirmEmail.mockRejectedValue(new Error('internal detail'))

    render(
      <MemoryRouter initialEntries={['/confirm-email?token=email-confirmation-token']}>
        <Routes><Route path="/confirm-email" element={<ConfirmEmailPage />} /></Routes>
      </MemoryRouter>,
    )

    await waitFor(() => expect(screen.getByText('An error occurred while confirming your email')).toBeDefined())
    expect(screen.queryByText('internal detail')).toBeNull()
  })
})
