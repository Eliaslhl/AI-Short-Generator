import { createContext, useContext, useState, useEffect, useRef, type ReactNode } from 'react'
import { isAxiosError } from 'axios'
import { authApi } from '../api'
import type { User } from '../types'
import { useToast } from './ToastContext'

interface AuthContextValue {
  user: User | null
  isAuthenticated: boolean
  loading: boolean
  authChecked: boolean
  authError: string | null
  isLoggingOut: boolean
  login: (email: string, password: string) => Promise<User>
  confirmEmail: (token: string) => Promise<{ message: string }>
  logout: () => Promise<void>
  refreshUser: () => Promise<User>
  retryAuth: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [authChecked, setAuthChecked] = useState(false)
  const [authError, setAuthError] = useState<string | null>(null)
  const [isLoggingOut, setIsLoggingOut] = useState(false)
  const authCheckRequest = useRef<Promise<void> | null>(null)
  const authVersion = useRef(0)
  const logoutRequest = useRef<Promise<void> | null>(null)
  const mounted = useRef(false)
  const { showToast } = useToast()

  const clearLegacyAuthStorage = (): void => {
    // These are the only historical authentication keys found in this client.
    localStorage.removeItem('token')
    localStorage.removeItem('access_token')
    localStorage.removeItem('token_type')
  }

  const isAuthenticationFailure = (error: unknown): boolean =>
    isAxiosError(error) && (error.response?.status === 401 || error.response?.status === 403)

  const beginAuthOperation = (): number => {
    authVersion.current += 1
    return authVersion.current
  }

  const isCurrentAuthOperation = (operation: number): boolean =>
    mounted.current && authVersion.current === operation

  const loadCurrentUser = async (operation: number): Promise<void> => {
    if (mounted.current) {
      setLoading(true)
      setAuthError(null)
    }
    try {
      const response = await authApi.me()
      if (isCurrentAuthOperation(operation)) setUser(response.data)
    } catch (error) {
      if (!isCurrentAuthOperation(operation)) return
      if (isAuthenticationFailure(error)) {
        setUser(null)
      } else {
        setAuthError('Unable to verify your session. Please try again.')
      }
    } finally {
      if (isCurrentAuthOperation(operation)) {
        setAuthChecked(true)
        setLoading(false)
      }
    }
  }

  const runAuthCheck = (): Promise<void> => {
    if (authCheckRequest.current) return authCheckRequest.current

    const operation = beginAuthOperation()
    const request = loadCurrentUser(operation)
    authCheckRequest.current = request
    void request.finally(() => {
      if (authCheckRequest.current === request) authCheckRequest.current = null
    })
    return request
  }

  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
    }
  }, [])

  useEffect(() => {
    clearLegacyAuthStorage()
    void runAuthCheck()
  }, [])

  const refreshUserForOperation = async (operation: number): Promise<User> => {
    const res = await authApi.me()
    if (!isCurrentAuthOperation(operation)) {
      throw new Error('Authentication request superseded')
    }
    setUser(res.data)
    setAuthError(null)
    setAuthChecked(true)
    setLoading(false)
    return res.data
  }

  const refreshUser = async (): Promise<User> => refreshUserForOperation(beginAuthOperation())

  const login = async (email: string, password: string): Promise<User> => {
    const operation = beginAuthOperation()
    await authApi.login(email, password)
    if (!isCurrentAuthOperation(operation)) {
      throw new Error('Authentication request superseded')
    }
    const authenticatedUser = await refreshUserForOperation(operation)
    showToast('Connexion réussie 👋', 'success')
    return authenticatedUser
  }

  const confirmEmail = async (token: string): Promise<{ message: string }> => {
    const operation = beginAuthOperation()
    const response = await authApi.confirmEmail(token)
    if (!isCurrentAuthOperation(operation)) {
      throw new Error('Authentication request superseded')
    }
    await refreshUserForOperation(operation)
    return { message: response.data.message }
  }

  const logout = async (): Promise<void> => {
    if (logoutRequest.current) return logoutRequest.current

    const operation = beginAuthOperation()
    setIsLoggingOut(true)
    const request = (async (): Promise<void> => {
      try {
        await authApi.logout()
      } catch (error) {
        if (!isAuthenticationFailure(error)) {
          if (isCurrentAuthOperation(operation)) {
            showToast('Unable to sign out. Please try again.', 'error')
          }
          throw error
        }
      }

      if (!isCurrentAuthOperation(operation)) return
      clearLegacyAuthStorage()
      setUser(null)
      setAuthError(null)
      setAuthChecked(true)
      setLoading(false)
      showToast('Déconnexion réussie', 'info')
    })()
    logoutRequest.current = request
    try {
      await request
    } finally {
      if (logoutRequest.current === request) {
        logoutRequest.current = null
        setIsLoggingOut(false)
      }
    }
  }

  const retryAuth = async (): Promise<void> => runAuthCheck()

  return (
    <AuthContext.Provider value={{
      user,
      isAuthenticated: user !== null,
      loading,
      authChecked,
      authError,
      isLoggingOut,
      login,
      confirmEmail,
      logout,
      refreshUser,
      retryAuth,
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
