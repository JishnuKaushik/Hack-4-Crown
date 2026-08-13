import { createContext, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { apiClient, AUTH_TOKEN_KEY } from '../api/client'

export interface AuthUser {
  id: number
  name: string
  email: string
  role: string
  created_at: string
}

interface TokenResponse {
  access_token: string
  token_type: string
  user: AuthUser
}

interface AuthContextValue {
  user: AuthUser | null
  token: string | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (name: string, email: string, password: string, role?: string) => Promise<void>
  logout: () => void
}

const USER_KEY = 'civiclens_user'

const AuthContext = createContext<AuthContextValue | null>(null)

function storeSession(data: TokenResponse) {
  localStorage.setItem(AUTH_TOKEN_KEY, data.access_token)
  localStorage.setItem(USER_KEY, JSON.stringify(data.user))
}

function clearSession() {
  localStorage.removeItem(AUTH_TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const storedToken = localStorage.getItem(AUTH_TOKEN_KEY)
    const storedUser = localStorage.getItem(USER_KEY)
    if (storedToken && storedUser) {
      setToken(storedToken)
      setUser(JSON.parse(storedUser))
    }
    setLoading(false)
  }, [])

  async function login(email: string, password: string) {
    const { data } = await apiClient.post<TokenResponse>('/auth/login', { email, password })
    storeSession(data)
    setToken(data.access_token)
    setUser(data.user)
  }

  async function register(name: string, email: string, password: string, role = 'citizen') {
    const { data } = await apiClient.post<TokenResponse>('/auth/register', {
      name,
      email,
      password,
      role,
    })
    storeSession(data)
    setToken(data.access_token)
    setUser(data.user)
  }

  function logout() {
    clearSession()
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, token, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
