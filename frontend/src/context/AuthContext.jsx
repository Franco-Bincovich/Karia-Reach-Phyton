import { createContext, useContext, useState, useCallback } from 'react'
import axios from 'axios'
import { API_AUTH_LOGIN } from '../constants/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [authenticated, setAuthenticated] = useState(
    () => !!sessionStorage.getItem('karia_token')
  )
  const [user, setUser] = useState(() => {
    const raw = sessionStorage.getItem('karia_user')
    return raw ? JSON.parse(raw) : null
  })

  const login = useCallback(async (email, password) => {
    // POST real al backend — no se necesita token para /api/auth/login
    const response = await axios.post(API_AUTH_LOGIN, { email, password })
    const { token, usuario } = response.data.data
    sessionStorage.setItem('karia_token', token)
    sessionStorage.setItem('karia_user', JSON.stringify(usuario))
    setAuthenticated(true)
    setUser(usuario)
  }, [])

  const logout = useCallback(() => {
    sessionStorage.removeItem('karia_token')
    sessionStorage.removeItem('karia_user')
    setAuthenticated(false)
    setUser(null)
  }, [])

  // Debe coincidir con METODOS_BUSQUEDA_VALIDOS en backend/utils/db.py
  const TODOS_METODOS = ['claude_ai', 'apollo', 'perplexity', 'apify', 'scraping_web', 'carga_manual']
  const metodos = (user?.metodos_habilitados?.length ? user.metodos_habilitados : TODOS_METODOS)

  return (
    <AuthContext.Provider value={{ isAuthenticated: authenticated, user, login, logout, metodos }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth debe usarse dentro de AuthProvider')
  return ctx
}
