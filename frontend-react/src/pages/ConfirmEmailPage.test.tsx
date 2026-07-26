import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ConfirmEmailPage from './ConfirmEmailPage'

const mocks = vi.hoisted(() => ({
  confirmEmail: vi.fn(),
}))

vi.mock('../context/AuthContext', () => ({ useAuth: () => ({ confirmEmail: mocks.confirmEmail }) }))
vi.mock('../hooks/useSeoTags', () => ({ useSeoTags: vi.fn() }))

describe('ConfirmEmailPage', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('uses the cookie set by email confirmation without a JWT exchange', async () => {
    mocks.confirmEmail.mockResolvedValue({ message: 'confirmed' })

    render(
      <MemoryRouter initialEntries={['/confirm-email?token=email-confirmation-token']}>
        <Routes><Route path="/confirm-email" element={<ConfirmEmailPage />} /></Routes>
      </MemoryRouter>,
    )

    await screen.findByText('Email Confirmed!')
    expect(mocks.confirmEmail).toHaveBeenCalledWith('email-confirmation-token')
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
