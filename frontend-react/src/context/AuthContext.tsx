import { createContext, useContext, useState, useEffect, type ReactNode } from 'react'
import { authApi } from '../api'
import type { User } from '../types'

interface AuthContextValue {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<User>
  register: (email: string, password: string, fullName: string) => Promise<User>
  logout: () => void
  refreshUser: () => Promise<User>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  // Start as true only when a token exists — avoids the sync setState-in-effect
  const [loading, setLoading] = useState(() => !!localStorage.getItem('token'))

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) return // loading is already false from initialiser above

    authApi
      .me()
      .then((res) => setUser(res.data))
      .catch(() => localStorage.removeItem('token'))
      .finally(() => setLoading(false))
  }, [])

  const login = async (email: string, password: string): Promise<User> => {
    const res = await authApi.login(email, password)
    localStorage.setItem('token', res.data.access_token)
    setUser(res.data.user)
    return res.data.user
  }

  const register = async (email: string, password: string, fullName: string): Promise<User> => {
    const res = await authApi.register(email, password, fullName)
    localStorage.setItem('token', res.data.access_token)
    setUser(res.data.user)
    return res.data.user
  }

  const logout = (): void => {
    localStorage.removeItem('token')
    setUser(null)
  }

  const refreshUser = async (): Promise<User> => {
    const res = await authApi.me()
    setUser(res.data)
    return res.data
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
