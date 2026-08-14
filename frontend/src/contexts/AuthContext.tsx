import { createContext, useContext, useState, useEffect, type ReactNode } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import type { User } from '@/types'

interface AuthContextType {
  user: User | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (data: { email: string; employee_id: string; password: string; password_confirm: string; name: string; role: string; sector: string }) => Promise<void>
  logout: () => void
  /** Recarrega /auth/me (após trocar foto, dados de perfil etc). */
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const queryClient = useQueryClient()

  useEffect(() => {
    const token = localStorage.getItem('qwi_token')
    if (token) {
      api.get('/auth/me').then(res => setUser(res.data)).catch(() => {
        localStorage.removeItem('qwi_token')
      }).finally(() => setIsLoading(false))
    } else {
      setIsLoading(false)
    }
  }, [])

  const login = async (email: string, password: string) => {
    const { data } = await api.post('/auth/login', { email, password })
    localStorage.setItem('qwi_token', data.access_token)
    // Zera o cache de queries: sem isso, dados da conta ANTERIOR (agenda,
    // relatórios…) vazariam para a sessão da nova conta no mesmo navegador.
    queryClient.clear()
    const me = await api.get('/auth/me')
    setUser(me.data)
  }

  const register = async (data: { email: string; employee_id: string; password: string; password_confirm: string; name: string; role: string; sector: string }) => {
    await api.post('/auth/register', data)
    await login(data.email, data.password)
  }

  const logout = () => {
    localStorage.removeItem('qwi_token')
    queryClient.clear()
    setUser(null)
  }

  const refreshUser = async () => {
    const me = await api.get('/auth/me')
    setUser(me.data)
  }

  return (
    <AuthContext.Provider value={{ user, isLoading, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
