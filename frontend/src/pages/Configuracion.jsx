import { useState, useEffect } from 'react'
import api from '../hooks/useApi'
import { useToast } from '../context/ToastContext'
import { API_APOLLO_STATUS, API_APOLLO_CONFIG } from '../constants/api'
import Button from '../components/UI/Button'
import Badge from '../components/UI/Badge'
import ConfirmModal from '../components/UI/ConfirmModal'

export default function Configuracion() {
  const toast = useToast()
  const [apolloStatus, setApolloStatus] = useState(false)
  const [apolloKey, setApolloKey] = useState('')
  const [loading, setLoading] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)

  useEffect(() => { checkStatus() }, [])

  const checkStatus = async () => {
    try {
      const { data } = await api.get(API_APOLLO_STATUS)
      setApolloStatus(data.data?.configurado || false)
    } catch (err) { toast.error(err.message) }
  }

  const guardar = async () => {
    if (apolloKey.length < 10) return toast.error('API key debe tener al menos 10 caracteres')
    setLoading(true)
    try {
      await api.post(API_APOLLO_CONFIG, { api_key: apolloKey })
      toast.success('API key de Apollo guardada')
      setApolloKey('')
      checkStatus()
    } catch (err) { toast.error(err.message) }
    finally { setLoading(false) }
  }

  const eliminar = async () => {
    setShowConfirm(false)
    try {
      await api.delete(API_APOLLO_CONFIG)
      toast.success('API key de Apollo eliminada')
      checkStatus()
    } catch (err) { toast.error(err.message) }
  }

  return (
    <div>
      <div className="card" style={{ maxWidth: 600 }}>
        <div className="flex-between mb-md">
          <h3>Apollo.io</h3>
          <Badge variant={apolloStatus ? 'success' : 'error'}>
            {apolloStatus ? 'Configurado' : 'No configurado'}
          </Badge>
        </div>
        <p className="text-sm text-secondary mb-md">
          Apollo.io permite buscar contactos verificados y enriquecer datos existentes
          con emails corporativos, telefonos y cargos actualizados.
        </p>
        <div className="form-group">
          <label htmlFor="apollo-key">API Key</label>
          <input id="apollo-key" type="password" value={apolloKey} onChange={(e) => setApolloKey(e.target.value)} placeholder="Pega tu API key de Apollo.io" />
        </div>
        <div className="flex gap-sm">
          <Button loading={loading} onClick={guardar}>Guardar</Button>
          {apolloStatus && <Button variant="danger" onClick={() => setShowConfirm(true)}>Eliminar</Button>}
        </div>
      </div>

      {showConfirm && (
        <ConfirmModal message="La API key de Apollo sera eliminada."
          onConfirm={eliminar} onCancel={() => setShowConfirm(false)} />
      )}
    </div>
  )
}
