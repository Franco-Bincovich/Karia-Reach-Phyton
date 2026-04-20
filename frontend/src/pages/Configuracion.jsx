import { useState, useEffect } from 'react'
import api from '../hooks/useApi'
import { useToast } from '../context/ToastContext'
import { API_APOLLO_STATUS, API_APOLLO_CONFIG, API_PERPLEXITY_STATUS, API_PERPLEXITY_CONFIG, API_APIFY_STATUS, API_APIFY_CONFIG, API_SCRAPING_PREFERENCIAS } from '../constants/api'
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
  const [loadingStatus, setLoadingStatus] = useState(true)
  const [showConfirm, setShowConfirm] = useState(null)
  const [scrapingPrefs, setScrapingPrefs] = useState({ extraer_emails: true, extraer_telefonos: true, extraer_autoridades: true, extraer_direcciones: false, max_paginas: 60, profundidad: 3, guardar_directo: false })
  const [loadingPrefs, setLoadingPrefs] = useState(false)

  useEffect(() => {
    checkStatus()
    api.get(API_SCRAPING_PREFERENCIAS).then(({ data }) => setScrapingPrefs(data.data)).catch(() => {})
  }, [])

  const checkStatus = async () => {
    setLoadingStatus(true)
    Promise.all([
      api.get(API_APOLLO_STATUS).then(({ data }) => setApolloStatus(!!data.data?.configurado)).catch(() => setApolloStatus(false)),
      api.get(API_PERPLEXITY_STATUS).then(({ data }) => setPerplexityStatus(!!data.data?.configurado)).catch(() => setPerplexityStatus(false)),
      api.get(API_APIFY_STATUS).then(({ data }) => setApifyStatus(!!data.data?.configurado)).catch(() => setApifyStatus(false)),
    ]).finally(() => setLoadingStatus(false))
  }

  const guardarIntegracion = async (servicio, endpoint, apiKey, clearKey) => {
    if (apiKey.length < 10) return toast.error('API key debe tener al menos 10 caracteres')
    setLoading(true)
    try {
      await api.post(endpoint, { api_key: apiKey })
      toast.success(`API key de ${servicio} guardada`); clearKey(''); checkStatus()
    } catch (err) { toast.error(err.message) }
    finally { setLoading(false) }
  }

  const guardarScrapingPrefs = async () => {
    setLoadingPrefs(true)
    try {
      await api.post(API_SCRAPING_PREFERENCIAS, scrapingPrefs)
      toast.success('Preferencias de scraping guardadas')
    } catch (err) { toast.error(err.message) }
    finally { setLoadingPrefs(false) }
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
          <Badge variant={loadingStatus ? 'info' : apolloStatus ? 'success' : 'error'}>
            {loadingStatus ? '...' : apolloStatus ? 'Configurado' : 'No configurado'}
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
          <Button loading={loading} onClick={() => guardarIntegracion('Apollo', API_APOLLO_CONFIG, apolloKey, setApolloKey)}>Guardar</Button>
          {apolloStatus && <Button variant="danger" onClick={() => setShowConfirm('apollo')}>Eliminar</Button>}
        </div>
      </div>

      <div className="card mb-md" style={{ maxWidth: 600 }}>
        <div className="flex-between mb-md">
          <h3>Perplexity</h3>
          <Badge variant={loadingStatus ? 'info' : perplexityStatus ? 'success' : 'error'}>
            {loadingStatus ? '...' : perplexityStatus ? 'Configurado' : 'No configurado'}
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
          <Button loading={loading} onClick={() => guardarIntegracion('Perplexity', API_PERPLEXITY_CONFIG, perplexityKey, setPerplexityKey)}>Guardar</Button>
          {perplexityStatus && <Button variant="danger" onClick={() => setShowConfirm('perplexity')}>Eliminar</Button>}
        </div>
      </div>

      <div className="card mb-md" style={{ maxWidth: 600 }}>
        <div className="flex-between mb-md">
          <h3>Apify</h3>
          <Badge variant={loadingStatus ? 'info' : apifyStatus ? 'success' : 'error'}>
            {loadingStatus ? '...' : apifyStatus ? 'Configurado' : 'No configurado'}
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
          <Button loading={loading} onClick={() => guardarIntegracion('Apify', API_APIFY_CONFIG, apifyKey, setApifyKey)}>Guardar</Button>
          {apifyStatus && <Button variant="danger" onClick={() => setShowConfirm('apify')}>Eliminar</Button>}
        </div>
      </div>

      <div className="card mb-md" style={{ maxWidth: 600 }}>
        <h3 className="mb-md">Preferencias de scraping</h3>
        <p className="text-sm text-secondary mb-md">
          Configurá qué datos extraer al usar el método Scraping Web en Buscar Contactos.
        </p>
        {[
          { key: 'extraer_emails', label: 'Extraer emails' },
          { key: 'extraer_telefonos', label: 'Extraer teléfonos' },
          { key: 'extraer_autoridades', label: 'Extraer nombres de autoridades' },
          { key: 'extraer_direcciones', label: 'Extraer direcciones' },
          { key: 'guardar_directo', label: 'Guardar contactos directo sin mostrar' },
        ].map(({ key, label }) => (
          <div className="form-group" key={key}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
              <input type="checkbox" checked={!!scrapingPrefs[key]}
                onChange={(e) => setScrapingPrefs({ ...scrapingPrefs, [key]: e.target.checked })} />
              {label}
            </label>
          </div>
        ))}
        <div className="form-row">
          <div className="form-group">
            <label htmlFor="scraping-max-paginas">Páginas máximas (10-100)</label>
            <input id="scraping-max-paginas" type="number" min={10} max={100}
              value={scrapingPrefs.max_paginas}
              onChange={(e) => setScrapingPrefs({ ...scrapingPrefs, max_paginas: Math.min(100, Math.max(10, +e.target.value || 60)) })} />
          </div>
          <div className="form-group">
            <label htmlFor="scraping-profundidad">Profundidad de crawl (1-5)</label>
            <input id="scraping-profundidad" type="number" min={1} max={5}
              value={scrapingPrefs.profundidad}
              onChange={(e) => setScrapingPrefs({ ...scrapingPrefs, profundidad: Math.min(5, Math.max(1, +e.target.value || 3)) })} />
          </div>
        </div>
        <Button loading={loadingPrefs} onClick={guardarScrapingPrefs}>Guardar preferencias</Button>
      </div>

      {showConfirm && (
        <ConfirmModal
          message={`La API key de ${showConfirm} sera eliminada.`}
          onConfirm={() => eliminar(showConfirm)} onCancel={() => setShowConfirm(null)} />
      )}
    </div>
  )
}
