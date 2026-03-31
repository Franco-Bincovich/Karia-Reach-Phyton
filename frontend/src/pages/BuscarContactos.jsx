import { useState, useEffect } from 'react'
import api from '../hooks/useApi'
import { useToast } from '../context/ToastContext'
import { API_CONTACTS, API_CONTACTS_SEARCH_AI, API_CONTACTS_SAVE, API_CONTACTS_MANUAL, API_APOLLO_SEARCH, API_APOLLO_STATUS, API_PERPLEXITY_SEARCH, API_PERPLEXITY_STATUS, API_BLOQUES, API_BLOQUE_CONTACTOS } from '../constants/api'
import Button from '../components/UI/Button'
import Table from '../components/UI/Table'
import Modal from '../components/UI/Modal'
import LoadingSpinner from '../components/UI/LoadingSpinner'
import ConfidenceBadge from '../components/UI/ConfidenceBadge'

export default function BuscarContactos() {
  const toast = useToast()
  const [form, setForm] = useState({ rubro: '', ubicacion: '', cantidad: 10, prompt_personalizado: '' })
  const [metodo, setMetodo] = useState('ai')
  const [apolloOk, setApolloOk] = useState(null)
  const [perplexityOk, setPerplexityOk] = useState(null)
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [showManual, setShowManual] = useState(false)
  const [manual, setManual] = useState({ nombre: '', empresa: '', email_empresarial: '', cargo: '' })
  const [showBloque, setShowBloque] = useState(false)
  const [nombreBloque, setNombreBloque] = useState('')

  useEffect(() => {
    api.get(API_APOLLO_STATUS)
      .then(({ data }) => setApolloOk(!!data?.data?.configurado))
      .catch(() => setApolloOk(false))
    api.get(API_PERPLEXITY_STATUS)
      .then(({ data }) => setPerplexityOk(!!data?.data?.configurado))
      .catch(() => setPerplexityOk(false))
  }, [])

  const allSelected = results.length > 0 && results.every((c) => c._selected)
  const toggleAll = () => setResults((prev) => prev.map((c) => ({ ...c, _selected: !allSelected })))
  const selCount = results.filter((c) => c._selected).length

  const COLUMNS = [
    { key: '_check', label: '', width: '40px',
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
  ]

  const buscar = async () => {
    if (!form.rubro.trim() && !form.prompt_personalizado?.trim()) return toast.error('Ingresa un rubro o un prompt personalizado')
    if (!form.ubicacion.trim() && !form.prompt_personalizado?.trim()) return toast.error('Ingresa una ubicacion')
    console.log("Método seleccionado:", metodo, "perplexityOk:", perplexityOk, "apolloOk:", apolloOk)
    if (metodo === 'apollo' && !apolloOk) return toast.error('Configurá tu API key de Apollo en Configuración')
    if (metodo === 'perplexity' && !perplexityOk) return toast.error('Configurá tu API key de Perplexity en Configuración')
    setLoading(true)
    try {
      const endpoints = { ai: API_CONTACTS_SEARCH_AI, apollo: API_APOLLO_SEARCH, perplexity: API_PERPLEXITY_SEARCH }
      const endpoint = endpoints[metodo]
      const payload = { ...form }
      if (!payload.prompt_personalizado?.trim()) delete payload.prompt_personalizado
      const { data } = await api.post(endpoint, payload)
      setResults((data.data || []).map((c) => ({ ...c, _selected: false })))
      toast.success(`${data.total} contactos encontrados`)
    } catch (err) { toast.error(err.message) }
    finally { setLoading(false) }
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
      // Primero guardar contactos, luego crear bloque y agregar
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
            <input id="buscar-cantidad" type="number" min={5} max={50} value={form.cantidad} onChange={(e) => setForm({ ...form, cantidad: +e.target.value })} />
          </div>
        </div>
        <div className="form-group">
          <label htmlFor="buscar-prompt">Prompt personalizado (opcional)</label>
          <input id="buscar-prompt" value={form.prompt_personalizado}
            onChange={(e) => setForm({ ...form, prompt_personalizado: e.target.value })}
            placeholder="Ej: Solo directores o gerentes generales, con más de 10 años de experiencia, de empresas con más de 50 empleados" />
        </div>
        <div className="flex gap-sm">
          <Button variant={metodo === 'ai' ? 'primary' : 'ghost'} size="sm" onClick={() => setMetodo('ai')}>Claude (IA)</Button>
          <Button variant={metodo === 'apollo' ? 'primary' : 'ghost'} size="sm" onClick={() => setMetodo('apollo')}>Apollo</Button>
          <Button variant={metodo === 'perplexity' ? 'primary' : 'ghost'} size="sm" onClick={() => setMetodo('perplexity')}>Perplexity</Button>
          <div style={{ flex: 1 }} />
          <Button onClick={() => { console.log("CLICK BUSCAR - metodo:", metodo); buscar(); }}>Buscar</Button>
          <Button variant="ghost" onClick={() => setShowManual(true)}>+ Manual</Button>
        </div>
        {metodo === 'apollo' && apolloOk === false && (
          <p className="text-sm text-secondary" style={{ marginTop: '0.5rem' }}>Configurá tu API key de Apollo en Configuración</p>
        )}
        {metodo === 'perplexity' && perplexityOk === false && (
          <p className="text-sm text-secondary" style={{ marginTop: '0.5rem' }}>Configurá tu API key de Perplexity en Configuración</p>
        )}
      </div>

      {results.length > 0 && (
        <div className="card">
          <div className="flex-between mb-md">
            <span className="text-sm text-secondary">{selCount} seleccionados</span>
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
