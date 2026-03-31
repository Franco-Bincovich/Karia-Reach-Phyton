import { useState } from 'react'
import api from '../hooks/useApi'
import { useToast } from '../context/ToastContext'
import { API_CONTACTS, API_CONTACTS_SEARCH_AI, API_CONTACTS_SAVE, API_CONTACTS_MANUAL, API_APOLLO_SEARCH } from '../constants/api'
import Button from '../components/UI/Button'
import Table from '../components/UI/Table'
import Modal from '../components/UI/Modal'
import LoadingSpinner from '../components/UI/LoadingSpinner'
import ConfidenceBadge from '../components/UI/ConfidenceBadge'

export default function BuscarContactos() {
  const toast = useToast()
  const [form, setForm] = useState({ rubro: '', ubicacion: '', cantidad: 10 })
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [showManual, setShowManual] = useState(false)
  const [manual, setManual] = useState({ nombre: '', empresa: '', email_empresarial: '', cargo: '' })

  const allSelected = results.length > 0 && results.every((c) => c._selected)
  const toggleAll = () => setResults((prev) => prev.map((c) => ({ ...c, _selected: !allSelected })))

  const COLUMNS = [
    { key: '_check', label: '', width: '40px',
      headerRender: () => (
        <input type="checkbox" checked={allSelected} onChange={toggleAll} aria-label="Seleccionar todos" />
      ),
      render: (_, row) => (
        <input type="checkbox" checked={row._selected || false} readOnly
          aria-label={`Seleccionar ${row.nombre || 'contacto'}`} />
      ),
    },
    { key: 'nombre', label: 'Nombre' },
    { key: 'empresa', label: 'Empresa' },
    { key: 'cargo', label: 'Cargo' },
    { key: 'email_empresarial', label: 'Email Corp.' },
    { key: 'email_personal', label: 'Email Personal' },
    { key: 'telefono_empresa', label: 'Tel. Empresa' },
    { key: 'telefono_personal', label: 'Tel. Personal' },
    { key: 'linkedin_url', label: 'LinkedIn', render: (v) => v
      ? <a href={v} target="_blank" rel="noopener noreferrer" title="Ver LinkedIn">🔗</a>
      : '-'
    },
    { key: 'confianza', label: 'Confianza', render: (v) => <ConfidenceBadge value={v} /> },
  ]

  const buscar = async (source) => {
    if (!form.rubro.trim()) return toast.error('Ingresa un rubro o industria')
    if (!form.ubicacion.trim()) return toast.error('Ingresa una ubicacion')
    setLoading(true)
    try {
      const endpoint = source === 'apollo' ? API_APOLLO_SEARCH : API_CONTACTS_SEARCH_AI
      const { data } = await api.post(endpoint, form)
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
    const sel = results.filter((c) => c._selected).map(({ _selected, ...rest }) => rest)
    if (!sel.length) return toast.error('Selecciona al menos un contacto')
    try {
      const { data } = await api.post(API_CONTACTS_SAVE, { contactos: sel })
      toast.success(`${data.guardados} contactos guardados`)
      setResults([])
    } catch (err) { toast.error(err.message) }
  }

  const agregarManual = async () => {
    try {
      await api.post(API_CONTACTS_MANUAL, manual)
      toast.success('Contacto agregado')
      setShowManual(false)
      setManual({ nombre: '', empresa: '', email_empresarial: '', cargo: '' })
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
        <div className="flex gap-sm">
          <Button onClick={() => buscar('ai')}>Buscar con IA</Button>
          <Button variant="teal" onClick={() => buscar('apollo')}>Buscar con Apollo</Button>
          <Button variant="ghost" onClick={() => setShowManual(true)}>+ Manual</Button>
        </div>
      </div>

      {results.length > 0 && (
        <div className="card">
          <div className="flex-between mb-md">
            <span className="text-sm text-secondary">{results.filter((c) => c._selected).length} seleccionados</span>
            <Button size="sm" onClick={guardar}>Guardar seleccion</Button>
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
    </div>
  )
}
