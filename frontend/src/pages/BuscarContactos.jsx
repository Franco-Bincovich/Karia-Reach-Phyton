import { useState, useEffect } from 'react'
import api from '../hooks/useApi'
import { useToast } from '../context/ToastContext'
import { useAuth } from '../context/AuthContext'
import {
  API_CONTACTS_SEARCH_AI, API_CONTACTS_SAVE, API_CONTACTS_MANUAL,
  API_APOLLO_SEARCH, API_APOLLO_STATUS, API_PERPLEXITY_SEARCH, API_PERPLEXITY_STATUS,
  API_APIFY_STATUS, API_APIFY_SEARCH, API_BLOQUES, API_BLOQUE_CONTACTOS,
  API_CONTACT_ENRICH, API_SCRAPING_BUSCAR,
} from '../constants/api'
import Button from '../components/UI/Button'
import Table from '../components/UI/Table'
import Modal from '../components/UI/Modal'
import LoadingSpinner from '../components/UI/LoadingSpinner'
import ConfidenceBadge from '../components/UI/ConfidenceBadge'

const TAMANO_OPCIONES = [
  { value: '', label: 'Cualquier tamaño' },
  { value: 'micro', label: 'Micro (1-10)' },
  { value: 'pequena', label: 'Pequeña (11-50)' },
  { value: 'mediana', label: 'Mediana (51-500)' },
  { value: 'grande', label: 'Grande (501-5000)' },
  { value: 'enterprise', label: 'Enterprise (5000+)' },
]

export default function BuscarContactos() {
  const toast = useToast()
  const { metodos } = useAuth()
  const [form, setForm] = useState({ rubro: '', ubicacion: '', cantidad: 10, prompt_personalizado: '' })
  const [apolloForm, setApolloForm] = useState({ cargo: '', tamano_empresa: '', solo_email_verificado: false })
  const [scrapingForm, setScrapingForm] = useState({ entradas: '' })
  const [pais, setPais] = useState('')
  const [metodo, setMetodo] = useState('ai')
  const [apolloOk, setApolloOk] = useState(null)
  const [perplexityOk, setPerplexityOk] = useState(null)
  const [apifyOk, setApifyOk] = useState(null)
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [enrichingId, setEnrichingId] = useState(null)
  const [showManual, setShowManual] = useState(false)
  const [manual, setManual] = useState({ nombre: '', empresa: '', email_empresarial: '', cargo: '' })
  const [showBloque, setShowBloque] = useState(false)
  const [nombreBloque, setNombreBloque] = useState('')

  useEffect(() => {
    const ctrl = new AbortController()
    const s = ctrl.signal
    api.get(API_APOLLO_STATUS, { signal: s })
      .then(({ data }) => setApolloOk(!!data?.data?.configurado))
      .catch(() => { if (!s.aborted) setApolloOk(false) })
    api.get(API_PERPLEXITY_STATUS, { signal: s })
      .then(({ data }) => setPerplexityOk(!!data?.data?.configurado))
      .catch(() => { if (!s.aborted) setPerplexityOk(false) })
    api.get(API_APIFY_STATUS, { signal: s })
      .then(({ data }) => setApifyOk(!!data?.data?.configurado))
      .catch(() => { if (!s.aborted) setApifyOk(false) })
    return () => ctrl.abort()
  }, [])

  const allSelected = results.length > 0 && results.every((c) => c._selected)
  const toggleAll = () => setResults((prev) => prev.map((c) => ({ ...c, _selected: !allSelected })))
  const selCount = results.filter((c) => c._selected).length

  const COLUMNS = [
    {
      key: '_check', label: '', width: '40px',
      headerRender: () => <input type="checkbox" checked={allSelected} onChange={toggleAll} aria-label="Seleccionar todos" />,
      render: (_, row) => <input type="checkbox" checked={row._selected || false} readOnly aria-label={`Seleccionar ${row.nombre || 'contacto'}`} />,
    },
    { key: 'nombre', label: 'Nombre' },
    { key: 'empresa', label: 'Empresa' },
    { key: 'cargo', label: 'Cargo' },
    { key: 'email_empresarial', label: 'Email Corp.' },
    { key: 'email_personal', label: 'Email Personal' },
    { key: 'telefono_empresa', label: 'Tel. Empresa' },
    { key: 'telefono_personal', label: 'Tel. Personal' },
    { key: 'linkedin_url', label: 'LinkedIn', render: (v) => v ? <a href={v} target="_blank" rel="noopener noreferrer" title="Ver LinkedIn">🔗</a> : '-' },
    { key: 'confianza', label: 'Confianza', render: (v) => <ConfidenceBadge value={v} /> },
    {
      key: '_estado', label: 'Estado', width: '130px',
      render: (_, row) => {
        if (row.ya_existe) {
          return (
            <div className="flex gap-sm" style={{ alignItems: 'center' }}>
              <span style={{
                fontSize: '0.72rem', fontWeight: 600, padding: '2px 7px',
                borderRadius: 10, background: '#D1FAE5', color: '#065F46', whiteSpace: 'nowrap',
              }}>Ya en KarIA</span>
              <button
                title="Enriquecer contacto existente"
                disabled={enrichingId === row.contact_id_existente}
                onClick={(e) => { e.stopPropagation(); enriquecerExistente(row) }}
                style={{
                  background: 'none', border: 'none', cursor: 'pointer', fontSize: '1rem',
                  opacity: enrichingId === row.contact_id_existente ? 0.4 : 1,
                }}
              >{enrichingId === row.contact_id_existente ? '...' : '⚡'}</button>
            </div>
          )
        }
        return <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>Nuevo</span>
      },
    },
  ]

  const buscar = async () => {
    if (metodo === 'scraping') {
      const entradas = scrapingForm.entradas.split('\n').map(l => l.trim()).filter(Boolean)
      if (!entradas.length) return toast.error('Ingresa al menos un sitio a scrapear')
      setLoading(true)
      try {
        const { data } = await api.post(API_SCRAPING_BUSCAR, { entradas })
        setResults((data.data || []).map((c) => ({ ...c, _selected: false })))
        toast.success(`${data.total} contactos encontrados`)
      } catch (err) { toast.error(err.message) }
      finally { setLoading(false) }
      return
    }
    if (!form.rubro.trim() && !form.prompt_personalizado?.trim()) return toast.error('Ingresa un rubro o un prompt personalizado')
    if (!form.ubicacion.trim() && !form.prompt_personalizado?.trim() && metodo !== 'apollo') return toast.error('Ingresa una ubicacion')
    if (metodo === 'apollo' && !apolloOk) return toast.error('Configurá tu API key de Apollo en Configuración')
    if (metodo === 'perplexity' && !perplexityOk) return toast.error('Configurá tu API key de Perplexity en Configuración')
    if (metodo === 'apify' && !apifyOk) return toast.error('Configurá tu API key de Apify en Configuración')
    setLoading(true)
    try {
      const endpoints = { ai: API_CONTACTS_SEARCH_AI, apollo: API_APOLLO_SEARCH, perplexity: API_PERPLEXITY_SEARCH, apify: API_APIFY_SEARCH }
      const endpoint = endpoints[metodo]
      const payload = { ...form }
      if (metodo === 'apify') payload.pais = pais
      if (metodo === 'apollo') {
        if (apolloForm.cargo.trim()) payload.cargo = apolloForm.cargo.trim()
        if (apolloForm.tamano_empresa) payload.tamano_empresa = apolloForm.tamano_empresa
        if (apolloForm.solo_email_verificado) payload.solo_email_verificado = true
      }
      if (!payload.prompt_personalizado?.trim()) delete payload.prompt_personalizado
      const { data } = await api.post(endpoint, payload)
      setResults((data.data || []).map((c) => ({ ...c, _selected: false })))
      toast.success(`${data.total} contactos encontrados`)
    } catch (err) { toast.error(err.message) }
    finally { setLoading(false) }
  }

  const enriquecerExistente = async (row) => {
    const cid = row.contact_id_existente
    if (!cid) return
    setEnrichingId(cid)
    try {
      await api.post(API_CONTACT_ENRICH(cid), { metodo })
      toast.success('Contacto enriquecido con los nuevos datos')
    } catch (err) { toast.error(err.message) }
    finally { setEnrichingId(null) }
  }

  const toggleSelect = (row) => {
    const key = row.id || row.email_empresarial || row.email_personal
    setResults((prev) => prev.map((c) => {
      const cKey = c.id || c.email_empresarial || c.email_personal
      return cKey === key ? { ...c, _selected: !c._selected } : c
    }))
  }

  const guardar = async () => {
    const sel = results.filter((c) => c._selected).map(({ _selected, ...rest }) => ({ ...rest, rubro: (rest.rubro && rest.rubro.trim()) ? rest.rubro : form.rubro }))
    if (!sel.length) return toast.error('Selecciona al menos un contacto')
    try {
      const { data } = await api.post(API_CONTACTS_SAVE, { contactos: sel })
      toast.success(`${data.guardados} contactos guardados`)
      setResults([])
    } catch (err) { toast.error(err.message) }
  }

  const armarBloque = async () => {
    if (!nombreBloque.trim()) return toast.error('Ingresa un nombre para el bloque')
    const sel = results.filter((c) => c._selected).map(({ _selected, ...rest }) => ({ ...rest, rubro: (rest.rubro && rest.rubro.trim()) ? rest.rubro : form.rubro }))
    try {
      const { data: saveData } = await api.post(API_CONTACTS_SAVE, { contactos: sel })
      const ids = (saveData.data || []).map((c) => c.id)
      if (ids.length) {
        const { data: bloqueData } = await api.post(API_BLOQUES, { nombre: nombreBloque.trim() })
        await api.post(API_BLOQUE_CONTACTOS(bloqueData.data.id), { contacto_ids: ids })
      }
      toast.success(`Bloque "${nombreBloque}" creado con ${ids.length} contactos`)
      setShowBloque(false); setNombreBloque(''); setResults([])
    } catch (err) { toast.error(err.message) }
  }

  const agregarManual = async () => {
    try {
      await api.post(API_CONTACTS_MANUAL, manual)
      toast.success('Contacto agregado')
      setShowManual(false); setManual({ nombre: '', empresa: '', email_empresarial: '', cargo: '' })
    } catch (err) { toast.error(err.message) }
  }

  if (loading) return <LoadingSpinner text="Buscando contactos..." />

  return (
    <div>
      <div className="card mb-md">
        {/* Formulario base compartido (no aplica en scraping) */}
        {metodo !== 'scraping' && (
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="buscar-rubro">Rubro / Industria</label>
              <input id="buscar-rubro" value={form.rubro} onChange={(e) => setForm({ ...form, rubro: e.target.value })} placeholder="Ej: Tecnologia" />
            </div>
            <div className="form-group">
              <label htmlFor="buscar-ubicacion">Ubicacion</label>
              <input id="buscar-ubicacion" value={form.ubicacion} onChange={(e) => setForm({ ...form, ubicacion: e.target.value })} placeholder="Ej: Buenos Aires" />
            </div>
            <div className="form-group">
              <label htmlFor="buscar-cantidad">Cantidad</label>
              <input id="buscar-cantidad" type="number" min={5} max={50} value={form.cantidad} onChange={(e) => { const v = Math.min(50, Math.max(5, +e.target.value || 5)); setForm({ ...form, cantidad: v }) }} />
            </div>
          </div>
        )}

        {/* Formulario específico por método */}
        {metodo === 'apollo' && (
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="apollo-cargo">Cargo específico</label>
              <input id="apollo-cargo" value={apolloForm.cargo} onChange={(e) => setApolloForm({ ...apolloForm, cargo: e.target.value })} placeholder="Ej: CEO, Director Comercial" />
            </div>
            <div className="form-group">
              <label htmlFor="apollo-tamano">Tamaño de empresa</label>
              <select id="apollo-tamano" value={apolloForm.tamano_empresa} onChange={(e) => setApolloForm({ ...apolloForm, tamano_empresa: e.target.value })}>
                {TAMANO_OPCIONES.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
            <div className="form-group" style={{ justifyContent: 'flex-end', paddingTop: '1.6rem' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                <input type="checkbox" checked={apolloForm.solo_email_verificado} onChange={(e) => setApolloForm({ ...apolloForm, solo_email_verificado: e.target.checked })} />
                Solo email verificado
              </label>
            </div>
          </div>
        )}

        {metodo === 'apify' && (
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="buscar-pais">País</label>
              <input id="buscar-pais" value={pais} onChange={(e) => setPais(e.target.value)} placeholder="Ej: Argentina, Chile, Uruguay..." />
            </div>
          </div>
        )}

        {metodo === 'scraping' && (
          <div className="form-group">
            <label htmlFor="scraping-entradas">Sitios a scrapear</label>
            <textarea
              id="scraping-entradas"
              rows={5}
              value={scrapingForm.entradas}
              onChange={(e) => setScrapingForm({ entradas: e.target.value })}
              placeholder={'https://municipio.gob.ar\nMunicipio de Río Cuarto Córdoba\nhttps://hotelxyz.com'}
              style={{ width: '100%', resize: 'vertical', fontFamily: 'inherit', padding: '0.5rem', borderRadius: 6, border: '1px solid var(--border)' }}
            />
            <p className="text-sm text-secondary" style={{ marginTop: '0.35rem' }}>
              Podés pegar URLs directas o escribir el nombre del lugar — lo buscamos automáticamente
            </p>
          </div>
        )}

        {metodo !== 'scraping' && (
          <div className="form-group">
            <label htmlFor="buscar-prompt">Prompt personalizado (opcional)</label>
            <input id="buscar-prompt" value={form.prompt_personalizado}
              onChange={(e) => setForm({ ...form, prompt_personalizado: e.target.value })}
              placeholder="Ej: Solo directores o gerentes generales, con más de 10 años de experiencia" />
          </div>
        )}

        <div className="flex gap-sm">
          {metodos.includes('claude_ai') && <Button variant={metodo === 'ai' ? 'primary' : 'ghost'} size="sm" onClick={() => setMetodo('ai')}>Claude (IA)</Button>}
          {metodos.includes('apollo') && <Button variant={metodo === 'apollo' ? 'primary' : 'ghost'} size="sm" onClick={() => setMetodo('apollo')}>Apollo</Button>}
          {metodos.includes('perplexity') && <Button variant={metodo === 'perplexity' ? 'primary' : 'ghost'} size="sm" onClick={() => setMetodo('perplexity')}>Perplexity</Button>}
          {metodos.includes('apify') && <Button variant={metodo === 'apify' ? 'primary' : 'ghost'} size="sm" onClick={() => setMetodo('apify')}>Apify</Button>}
          {metodos.includes('scraping_web') && <Button variant={metodo === 'scraping' ? 'primary' : 'ghost'} size="sm" onClick={() => setMetodo('scraping')}>Scraping Web</Button>}
          <div style={{ flex: 1 }} />
          <Button onClick={buscar}>Buscar</Button>
          {metodos.includes('carga_manual') && <Button variant="ghost" onClick={() => setShowManual(true)}>+ Manual</Button>}
        </div>
        {metodo === 'apollo' && apolloOk === false && (
          <p className="text-sm text-secondary" style={{ marginTop: '0.5rem' }}>Configurá tu API key de Apollo en Configuración</p>
        )}
        {metodo === 'perplexity' && perplexityOk === false && (
          <p className="text-sm text-secondary" style={{ marginTop: '0.5rem' }}>Configurá tu API key de Perplexity en Configuración</p>
        )}
        {metodo === 'apify' && apifyOk === false && (
          <p className="text-sm text-secondary" style={{ marginTop: '0.5rem' }}>Configurá tu API key de Apify en Configuración</p>
        )}
      </div>

      {results.length > 0 && (
        <div className="card">
          <div className="flex-between mb-md">
            <span className="text-sm text-secondary">{selCount} seleccionados · {results.filter(c => c.ya_existe).length} ya en KarIA</span>
            <div className="flex gap-sm">
              {selCount > 0 && <Button size="sm" variant="ghost" onClick={() => setShowBloque(true)}>Armar bloque</Button>}
              <Button size="sm" onClick={guardar}>Guardar seleccion</Button>
            </div>
          </div>
          <Table columns={COLUMNS} data={results} onRowClick={toggleSelect} />
        </div>
      )}

      {showManual && (
        <Modal title="Agregar contacto manual" onClose={() => setShowManual(false)}>
          {['nombre', 'empresa', 'email_empresarial', 'cargo'].map((f) => (
            <div className="form-group" key={f}>
              <label htmlFor={`manual-${f}`}>{f.replaceAll('_', ' ')}</label>
              <input id={`manual-${f}`} value={manual[f]} onChange={(e) => setManual({ ...manual, [f]: e.target.value })} />
            </div>
          ))}
          <Button onClick={agregarManual}>Guardar</Button>
        </Modal>
      )}

      {showBloque && (
        <Modal title="Armar bloque" onClose={() => setShowBloque(false)}>
          <div className="form-group">
            <label htmlFor="bloque-nombre">Nombre del bloque</label>
            <input id="bloque-nombre" value={nombreBloque} onChange={(e) => setNombreBloque(e.target.value)}
              placeholder="Ej: Hospitales Córdoba" />
          </div>
          <Button onClick={armarBloque}>Crear bloque con {selCount} contactos</Button>
        </Modal>
      )}
    </div>
  )
}
