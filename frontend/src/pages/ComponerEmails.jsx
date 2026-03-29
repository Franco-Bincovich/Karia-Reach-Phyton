import { useState, useEffect } from 'react'
import api from '../hooks/useApi'
import { useToast } from '../context/ToastContext'
import { API_CONTACTS, API_COMPOSE_GENERATE, API_COMPOSE_FROM_CONTACTS, API_COMPOSE_TEMPLATES } from '../constants/api'
import Button from '../components/UI/Button'
import LoadingSpinner from '../components/UI/LoadingSpinner'
import TemplateList from '../components/TemplateList'
import ContactSelector from '../components/ContactSelector'

const TONOS = ['formal', 'amigable', 'persuasivo', 'directo', 'casual']
const OBJETIVOS = ['agendar_reunion', 'vender', 'informar', 'seguimiento', 'presentacion']
const MODOS = ['formal', 'casual', 'directo']

export default function ComponerEmails() {
  const toast = useToast()
  const [tab, setTab] = useState('variantes')
  const [form, setForm] = useState({ descripcion: '', tono: 'formal', objetivo: 'vender', variantes: 3 })
  const [contactos, setContactos] = useState([])
  const [producto, setProducto] = useState('')
  const [modoEmail, setModoEmail] = useState('formal')
  const [results, setResults] = useState([])
  const [templates, setTemplates] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => { cargarTemplates() }, [])

  const cargarTemplates = async () => {
    try { const { data } = await api.get(API_COMPOSE_TEMPLATES); setTemplates(data.data || []) }
    catch (err) { toast.error(err.message) }
  }
  const cargarContactos = async () => {
    try { const { data } = await api.get(API_CONTACTS); setContactos((data.data || []).map((c) => ({ ...c, _selected: false }))) }
    catch (err) { toast.error(err.message) }
  }

  const generar = async () => {
    setLoading(true)
    try {
      if (tab === 'variantes') {
        const { data } = await api.post(API_COMPOSE_GENERATE, form)
        setResults(data.data || [])
      } else {
        const sel = contactos.filter((c) => c._selected)
        if (!sel.length) { setLoading(false); return toast.error('Selecciona contactos') }
        const { data } = await api.post(API_COMPOSE_FROM_CONTACTS, {
          contactos: sel.map(({ nombre, empresa, cargo, email_empresarial }) =>
            ({ nombre, empresa, cargo, email: email_empresarial || '' })),
          producto, modo: modoEmail,
        })
        setResults(data.data || [])
      }
      toast.success('Variantes generadas')
    } catch (err) { toast.error(err.message) }
    finally { setLoading(false) }
  }

  const guardarTemplate = async (r) => {
    try {
      await api.post(API_COMPOSE_TEMPLATES, {
        nombre: r.asunto?.slice(0, 50) || 'Sin nombre',
        asunto: r.asunto || r.destinatario || '', cuerpo: r.cuerpo || '',
        tono: form.tono, objetivo: form.objetivo,
      })
      toast.success('Plantilla guardada'); cargarTemplates()
    } catch (err) { toast.error(err.message) }
  }
  const eliminarTemplate = async (id) => {
    try { await api.delete(`${API_COMPOSE_TEMPLATES}/${id}`); toast.success('Eliminada'); cargarTemplates() }
    catch (err) { toast.error(err.message) }
  }

  return (
    <div>
      <div className="card mb-md">
        <div className="flex gap-sm mb-md">
          <Button variant={tab === 'variantes' ? 'primary' : 'ghost'} size="sm" onClick={() => setTab('variantes')}>Generar variantes</Button>
          <Button variant={tab === 'contactos' ? 'primary' : 'ghost'} size="sm" onClick={() => { setTab('contactos'); cargarContactos() }}>Desde contactos</Button>
        </div>

        {tab === 'variantes' ? (
          <>
            <div className="form-group">
              <label htmlFor="comp-desc">Descripcion del producto/servicio</label>
              <textarea id="comp-desc" rows={3} value={form.descripcion} onChange={(e) => setForm({ ...form, descripcion: e.target.value })} />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="comp-tono">Tono</label>
                <select id="comp-tono" value={form.tono} onChange={(e) => setForm({ ...form, tono: e.target.value })}>
                  {TONOS.map((t) => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label htmlFor="comp-obj">Objetivo</label>
                <select id="comp-obj" value={form.objetivo} onChange={(e) => setForm({ ...form, objetivo: e.target.value })}>
                  {OBJETIVOS.map((o) => <option key={o} value={o}>{o.replaceAll('_', ' ')}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label htmlFor="comp-var">Variantes</label>
                <input id="comp-var" type="number" min={1} max={5} value={form.variantes} onChange={(e) => setForm({ ...form, variantes: +e.target.value })} />
              </div>
            </div>
          </>
        ) : (
          <>
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="comp-prod">Producto/servicio</label>
                <input id="comp-prod" value={producto} onChange={(e) => setProducto(e.target.value)} />
              </div>
              <div className="form-group">
                <label htmlFor="comp-modo">Modo de escritura</label>
                <select id="comp-modo" value={modoEmail} onChange={(e) => setModoEmail(e.target.value)}>
                  {MODOS.map((m) => <option key={m} value={m}>{m}</option>)}
                </select>
              </div>
            </div>
            <div className="form-group">
              <label>Contactos</label>
              <ContactSelector contactos={contactos} onChange={setContactos} />
            </div>
          </>
        )}
        <Button loading={loading} onClick={generar}>Generar</Button>
      </div>

      {loading && <LoadingSpinner text="Generando con IA..." />}

      {results.map((r, i) => (
        <div key={i} className="card mb-md">
          <div className="flex-between mb-md">
            <strong>{r.asunto || r.destinatario}</strong>
            <Button size="sm" variant="ghost" onClick={() => guardarTemplate(r)}>Guardar plantilla</Button>
          </div>
          <div className="text-sm" style={{ whiteSpace: 'pre-wrap' }}>{r.cuerpo}</div>
        </div>
      ))}

      <TemplateList templates={templates} onEliminar={eliminarTemplate} />
    </div>
  )
}
