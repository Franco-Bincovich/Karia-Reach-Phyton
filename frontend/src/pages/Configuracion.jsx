import { useState, useEffect } from 'react'
import api from '../hooks/useApi'
import { useToast } from '../context/ToastContext'
import { API_APOLLO_STATUS, API_APOLLO_CONFIG, API_PERPLEXITY_STATUS, API_PERPLEXITY_CONFIG, API_APIFY_STATUS } from '../constants/api'
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
  const [loading, setLoading] = useState(false)
  const [showConfirm, setShowConfirm] = useState(null)

  useEffect(() => { checkStatus() }, [])

  const checkStatus = async () => {
    try {
      const [apollo, perplexity, apify] = await Promise.all([
        api.get(API_APOLLO_STATUS), api.get(API_PERPLEXITY_STATUS), api.get(API_APIFY_STATUS),
      ])
      setApolloStatus(apollo.data.data?.configurado || false)
      setPerplexityStatus(perplexity.data.data?.configurado || false)
      setApifyStatus(apify.data.data?.configurado || false)
    } catch (err) { toast.error(err.message) }
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

  const eliminar = async (servicio) => {
    setShowConfirm(null)
    try {
      const endpoint = servicio === 'apollo' ? API_APOLLO_CONFIG : API_PERPLEXITY_CONFIG
      await api.delete(endpoint)
      toast.success(`API key de ${servicio === 'apollo' ? 'Apollo' : 'Perplexity'} eliminada`)
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

      <div className="card" style={{ maxWidth: 600 }}>
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
        <p className="text-sm text-secondary">
          {apifyStatus
            ? 'La API key está configurada en el archivo .env del servidor.'
            : 'Agregá APIFY_API_KEY en el archivo .env del servidor para activar Apify.'}
        </p>
      </div>

      {showConfirm && (
        <ConfirmModal
          message={`La API key de ${showConfirm === 'apollo' ? 'Apollo' : 'Perplexity'} sera eliminada.`}
          onConfirm={() => eliminar(showConfirm)} onCancel={() => setShowConfirm(null)} />
      )}
    </div>
  )
}
