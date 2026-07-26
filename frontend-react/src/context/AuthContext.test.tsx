import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, beforeEach, expect, it, vi } from 'vitest'
import { AuthProvider, useAuth } from './AuthContext'

const mocks = vi.hoisted(() => ({
  me: vi.fn(),
  login: vi.fn(),
  createSession: vi.fn(),
  logout: vi.fn(),
  showToast: vi.fn(),
}))

vi.mock('../api', () => ({
  authApi: {
    me: mocks.me,
    login: mocks.login,
    createSession: mocks.createSession,
    logout: mocks.logout,
  },
}))

vi.mock('./ToastContext', () => ({
  useToast: () => ({ showToast: mocks.showToast }),
}))

const user = {
  id: 1,
  email: 'user@example.test',
  full_name: null,
  avatar_url: null,
  plan: 'free' as const,
  generations_this_month: 0,
  free_generations_left: 2,
}

function deferred<T>() {
  let resolve: (value: T) => void
  const promise = new Promise<T>((done) => {
    resolve = done
  })
  return { promise, resolve: resolve! }
}

function Probe() {
  const auth = useAuth()
  return (
    <>
      <div data-testid="state">{`${auth.loading}:${auth.authChecked}:${auth.user?.email ?? 'none'}:${auth.authError ?? 'none'}:${auth.isLoggingOut}`}</div>
      <button onClick={() => { void auth.login('user@example.test', 'password').catch(() => undefined) }}>login</button>
      <button onClick={() => { void auth.logout().catch(() => undefined) }}>logout</button>
    </>
  )
}

describe('AuthProvider cookie session cutover', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('checks the cookie session at startup and removes only legacy auth keys', async () => {
    localStorage.setItem('token', 'legacy')
    localStorage.setItem('access_token', 'legacy')
    localStorage.setItem('token_type', 'bearer')
    localStorage.setItem('login_error', 'keep this')
    mocks.me.mockResolvedValue({ data: user })

    render(<AuthProvider><Probe /></AuthProvider>)

    await screen.findByText(`false:true:${user.email}:none:false`)
    expect(mocks.me).toHaveBeenCalledTimes(1)
    expect(localStorage.getItem('token')).toBeNull()
    expect(localStorage.getItem('access_token')).toBeNull()
    expect(localStorage.getItem('token_type')).toBeNull()
    expect(localStorage.getItem('login_error')).toBe('keep this')
  })

  it('does not treat an unavailable backend as a deliberate logout', async () => {
    mocks.me.mockRejectedValue({ response: { status: 500 } })

    render(<AuthProvider><Probe /></AuthProvider>)

    await screen.findByText('false:true:none:Unable to verify your session. Please try again.:false')
  })

  it('treats an expired or absent cookie as signed out', async () => {
    mocks.me.mockRejectedValue({ isAxiosError: true, response: { status: 401 } })

    render(<AuthProvider><Probe /></AuthProvider>)

    await screen.findByText('false:true:none:none:false')
  })

  it('keeps the password JWT in memory only while creating a cookie session', async () => {
    mocks.me.mockResolvedValueOnce({ data: user }).mockResolvedValueOnce({ data: user })
    mocks.login.mockResolvedValue({ data: { access_token: 'temporary-jwt', token_type: 'bearer', user } })
    mocks.createSession.mockResolvedValue({ data: { expires_at: '2030-01-01T00:00:00Z' } })

    render(<AuthProvider><Probe /></AuthProvider>)
    await screen.findByText(`false:true:${user.email}:none:false`)
    fireEvent.click(screen.getByRole('button', { name: 'login' }))

    await waitFor(() => expect(mocks.createSession).toHaveBeenCalledWith('temporary-jwt'))
    expect(mocks.me).toHaveBeenCalledTimes(2)
    expect(localStorage.getItem('token')).toBeNull()
    expect(localStorage.getItem('access_token')).toBeNull()
  })

  it('does not authenticate when the cookie session exchange fails', async () => {
    mocks.me.mockRejectedValueOnce({ isAxiosError: true, response: { status: 401 } })
    mocks.login.mockResolvedValue({ data: { access_token: 'temporary-jwt', token_type: 'bearer', user } })
    mocks.createSession.mockRejectedValue(new Error('session unavailable'))

    render(<AuthProvider><Probe /></AuthProvider>)
    await screen.findByText('false:true:none:none:false')
    fireEvent.click(screen.getByRole('button', { name: 'login' }))

    await waitFor(() => expect(mocks.createSession).toHaveBeenCalledWith('temporary-jwt'))
    expect(screen.getByTestId('state').textContent).toBe('false:true:none:none:false')
    expect(localStorage.getItem('token')).toBeNull()
  })

  it('clears state only after a confirmed or idempotent logout', async () => {
    mocks.me.mockResolvedValue({ data: user })
    mocks.logout.mockResolvedValue({ data: undefined })

    render(<AuthProvider><Probe /></AuthProvider>)
    await screen.findByText(`false:true:${user.email}:none:false`)
    fireEvent.click(screen.getByRole('button', { name: 'logout' }))

    await screen.findByText('false:true:none:none:false')
    expect(mocks.logout).toHaveBeenCalledTimes(1)
  })

  it('retains user state when server logout fails', async () => {
    mocks.me.mockResolvedValue({ data: user })
    mocks.logout.mockRejectedValue(new Error('database unavailable'))

    render(<AuthProvider><Probe /></AuthProvider>)
    await screen.findByText(`false:true:${user.email}:none:false`)
    fireEvent.click(screen.getByRole('button', { name: 'logout' }))

    await waitFor(() => expect(mocks.showToast).toHaveBeenCalledWith('Unable to sign out. Please try again.', 'error'))
    expect(screen.getByTestId('state').textContent).toBe(`false:true:${user.email}:none:false`)
  })

  it('ignores an initial session check that resolves after a successful login', async () => {
    const initialMe = deferred<{ data: typeof user }>()
    mocks.me.mockReturnValueOnce(initialMe.promise).mockResolvedValueOnce({ data: user })
    mocks.login.mockResolvedValue({ data: { access_token: 'temporary-jwt', token_type: 'bearer', user } })
    mocks.createSession.mockResolvedValue({ data: { expires_at: '2030-01-01T00:00:00Z' } })

    render(<AuthProvider><Probe /></AuthProvider>)
    fireEvent.click(screen.getByRole('button', { name: 'login' }))
    await screen.findByText(`false:true:${user.email}:none:false`)

    initialMe.resolve({ data: { ...user, email: 'stale@example.test' } })
    await waitFor(() => expect(screen.getByTestId('state').textContent).toBe(`false:true:${user.email}:none:false`))
  })

  it('ignores an initial session check that resolves after logout', async () => {
    const initialMe = deferred<{ data: typeof user }>()
    mocks.me.mockReturnValueOnce(initialMe.promise)
    mocks.logout.mockResolvedValue({ data: undefined })

    render(<AuthProvider><Probe /></AuthProvider>)
    fireEvent.click(screen.getByRole('button', { name: 'logout' }))
    await screen.findByText('false:true:none:none:false')

    initialMe.resolve({ data: user })
    await waitFor(() => expect(screen.getByTestId('state').textContent).toBe('false:true:none:none:false'))
  })

  it('deduplicates concurrent logout requests', async () => {
    const pendingLogout = deferred<{ data: undefined }>()
    mocks.me.mockResolvedValue({ data: user })
    mocks.logout.mockReturnValue(pendingLogout.promise)

    render(<AuthProvider><Probe /></AuthProvider>)
    await screen.findByText(`false:true:${user.email}:none:false`)
    fireEvent.click(screen.getByRole('button', { name: 'logout' }))
    fireEvent.click(screen.getByRole('button', { name: 'logout' }))

    expect(mocks.logout).toHaveBeenCalledTimes(1)
    expect(screen.getByTestId('state').textContent).toBe(`false:true:${user.email}:none:true`)
    pendingLogout.resolve({ data: undefined })
    await screen.findByText('false:true:none:none:false')
  })
})
