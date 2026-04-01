import { useState, useEffect } from 'react'
import api from '../hooks/useApi'
import { useToast } from '../context/ToastContext'
import { API_APOLLO_STATUS, API_APOLLO_CONFIG, API_PERPLEXITY_STATUS, API_PERPLEXITY_CONFIG, API_APIFY_STATUS, API_APIFY_CONFIG } from '../constants/api'
import Button from '../components/UI/Button'
import Badge from '../components/UI/Badge'
import ConfirmModal from '../components/UI/ConfirmModal'

export default function Configuracion() {
  const toast = useToast()
  const [apolloStatus, setApolloStatus] = useState(false)
  const [apolloKey, setApolloKey] = useState('')
  const [perplexityStatus, setPerplexityStatus] = useState(false)
  const [perplexityKey, setPerplexityKey] = useState('')
  const [apifyStatus, setApifyStatus] = useState(false)
  const [apifyKey, setApifyKey] = useState('')
  const [loading, setLoading] = useState(false)
  const [showConfirm, setShowConfirm] = useState(null)

  useEffect(() => { checkStatus() }, [])

  const checkStatus = async () => {
    api.get(API_APOLLO_STATUS)
      .then(({ data }) => setApolloStatus(!!data.data?.configurado))
      .catch(() => setApolloStatus(false))
    api.get(API_PERPLEXITY_STATUS)
      .then(({ data }) => setPerplexityStatus(!!data.data?.configurado))
      .catch(() => setPerplexityStatus(false))
    api.get(API_APIFY_STATUS)
      .then(({ data }) => setApifyStatus(!!data.data?.configurado))
      .catch(() => setApifyStatus(false))
  }

  const guardarApollo = async () => {
    if (apolloKey.length < 10) return toast.error('API key debe tener al menos 10 caracteres')
    setLoading(true)
    try {
      await api.post(API_APOLLO_CONFIG, { api_key: apolloKey })
      toast.success('API key de Apollo guardada'); setApolloKey(''); checkStatus()
    } catch (err) { toast.error(err.message) }
    finally { setLoading(false) }
  }

  const guardarPerplexity = async () => {
    if (perplexityKey.length < 10) return toast.error('API key debe tener al menos 10 caracteres')
    setLoading(true)
    try {
      await api.post(API_PERPLEXITY_CONFIG, { api_key: perplexityKey })
      toast.success('API key de Perplexity guardada'); setPerplexityKey(''); checkStatus()
    } catch (err) { toast.error(err.message) }
    finally { setLoading(false) }
  }

  const guardarApify = async () => {
    if (apifyKey.length < 10) return toast.error('API key debe tener al menos 10 caracteres')
    setLoading(true)
    try {
      await api.post(API_APIFY_CONFIG, { api_key: apifyKey })
      toast.success('API key de Apify guardada'); setApifyKey(''); checkStatus()
    } catch (err) { toast.error(err.message) }
    finally { setLoading(false) }
  }

  const eliminar = async (servicio) => {
    setShowConfirm(null)
    try {
      const endpoints = { apollo: API_APOLLO_CONFIG, perplexity: API_PERPLEXITY_CONFIG, apify: API_APIFY_CONFIG }
      await api.delete(endpoints[servicio])
      toast.success(`API key de ${servicio} eliminada`)
      checkStatus()
    } catch (err) { toast.error(err.message) }
  }

  return (
    <div>
      <div className="card mb-md" style={{ maxWidth: 600 }}>
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
          <Button loading={loading} onClick={guardarApollo}>Guardar</Button>
          {apolloStatus && <Button variant="danger" onClick={() => setShowConfirm('apollo')}>Eliminar</Button>}
        </div>
      </div>

      <div className="card mb-md" style={{ maxWidth: 600 }}>
        <div className="flex-between mb-md">
          <h3>Perplexity</h3>
          <Badge variant={perplexityStatus ? 'success' : 'error'}>
            {perplexityStatus ? 'Configurado' : 'No configurado'}
          </Badge>
        </div>
        <p className="text-sm text-secondary mb-md">
          Perplexity usa el modelo sonar con busqueda web integrada para encontrar
          contactos comerciales con datos actualizados.
        </p>
        <div className="form-group">
          <label htmlFor="perplexity-key">API Key</label>
          <input id="perplexity-key" type="password" value={perplexityKey} onChange={(e) => setPerplexityKey(e.target.value)} placeholder="Pega tu API key de Perplexity" />
        </div>
        <div className="flex gap-sm">
          <Button loading={loading} onClick={guardarPerplexity}>Guardar</Button>
          {perplexityStatus && <Button variant="danger" onClick={() => setShowConfirm('perplexity')}>Eliminar</Button>}
        </div>
      </div>

      <div className="card mb-md" style={{ maxWidth: 600 }}>
        <div className="flex-between mb-md">
          <h3>Apify</h3>
          <Badge variant={apifyStatus ? 'success' : 'error'}>
            {apifyStatus ? 'Configurado' : 'No configurado'}
          </Badge>
        </div>
        <p className="text-sm text-secondary mb-md">
          Apify permite enriquecer contactos automáticamente usando web scraping
          de Google Maps, Instagram, Facebook, LinkedIn y más.
        </p>
        <div className="form-group">
          <label htmlFor="apify-key">API Key</label>
          <input id="apify-key" type="password" value={apifyKey} onChange={(e) => setApifyKey(e.target.value)} placeholder="Pegá tu API key de Apify" />
        </div>
        <div className="flex gap-sm">
          <Button loading={loading} onClick={guardarApify}>Guardar</Button>
          {apifyStatus && <Button variant="danger" onClick={() => setShowConfirm('apify')}>Eliminar</Button>}
        </div>
      </div>

      {showConfirm && (
        <ConfirmModal
          message={`La API key de ${showConfirm} sera eliminada.`}
          onConfirm={() => eliminar(showConfirm)} onCancel={() => setShowConfirm(null)} />
      )}
    </div>
  )
}
