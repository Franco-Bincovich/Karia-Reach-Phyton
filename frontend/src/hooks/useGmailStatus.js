import { useState, useEffect, useCallback } from 'react'
import api from './useApi'
import { API_GMAIL_STATUS } from '../constants/api'

export function useGmailStatus() {
  const [estado, setEstado] = useState(null) // { conectado, email, ultimo_uso }
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState(null)

  const refrescar = useCallback(async () => {
    setCargando(true)
    try {
      const resp = await api.get(API_GMAIL_STATUS)
      setEstado(resp.data.data)
      setError(null)
    } catch (e) {
      setError(e.message)
    } finally {
      setCargando(false)
    }
  }, [])

  useEffect(() => { refrescar() }, [refrescar])

  return { estado, cargando, error, refrescar }
}
