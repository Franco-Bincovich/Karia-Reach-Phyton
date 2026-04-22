import { useState, useEffect } from 'react'
import api from '../hooks/useApi'
import { useToast } from '../context/ToastContext'
import { API_CONTACTS, API_CONTACT_DELETE, API_BLOQUES, API_BLOQUE_CONTACTOS, API_CONTACT_ENRICH } from '../constants/api'
import Button from '../components/UI/Button'
import LoadingSpinner from '../components/UI/LoadingSpinner'
import ConfirmModal from '../components/UI/ConfirmModal'
import Modal from '../components/UI/Modal'
import ContactoDetalleRow from '../components/UI/ContactoDetalleRow'
import ContactoFiltros from '../components/UI/ContactoFiltros'
import { exportarContactosExcel } from '../utils/exportExcel'
import './Historial.css'

const PAGE_SIZE = 20

export default function Historial() {
  const toast = useToast()
  const [contactos, setContactos] = useState([])
  const [selected, setSelected] = useState(new Set())
  const [filtros, setFiltros] = useState({ texto: '', origen: 'todos', rubro: '' })
  const [page, setPage] = useState(1)
  const [expandedId, setExpandedId] = useState(null)
  const [deleteId, setDeleteId] = useState(null)
  const [loading, setLoading] = useState(true)
  const [enrichingId, setEnrichingId] = useState(null)
  const [enrichModalId, setEnrichModalId] = useState(null)
  const [enrichMetodo, setEnrichMetodo] = useState('claude')
  const [showBloque, setShowBloque] = useState(false)
  const [nombreBloque, setNombreBloque] = useState('')

  useEffect(() => {
    api.get(API_CONTACTS)
      .then(({ data }) => setContactos(data.data || []))
      .catch((err) => toast.error(err.message))
      .finally(() => setLoading(false))
  }, [])

  const eliminar = async () => {
    const id = deleteId; setDeleteId(null)
    try {
      await api.delete(API_CONTACT_DELETE(id))
      toast.success('Contacto eliminado')
      setContactos((prev) => prev.filter((c) => c.id !== id))
      setSelected((prev) => { const s = new Set(prev); s.delete(id); return s })
      if (expandedId === id) setExpandedId(null)
    } catch (err) { toast.error(err.message) }
  }

  const toggleSelect = (id) => setSelected((prev) => { const s = new Set(prev); s.has(id) ? s.delete(id) : s.add(id); return s })

  const enriquecer = async () => {
    const id = enrichModalId; setEnrichModalId(null); setEnrichingId(id)
    try {
      await api.post(API_CONTACT_ENRICH(id), { metodo: enrichMetodo })
      toast.success('Contacto enriquecido')
      const { data } = await api.get(API_CONTACTS)
      setContactos(data.data || [])
    } catch (err) { toast.error(err.message) }
    finally { setEnrichingId(null) }
  }

  const armarBloque = async () => {
    if (!nombreBloque.trim()) return toast.error('Ingresa un nombre para el bloque')
    try {
      const { data: bloqueData } = await api.post(API_BLOQUES, { nombre: nombreBloque.trim() })
      await api.post(API_BLOQUE_CONTACTOS(bloqueData.data.id), { contacto_ids: [...selected] })
      toast.success(`Bloque "${nombreBloque}" creado con ${selected.size} contactos`)
      setShowBloque(false); setNombreBloque(''); setSelected(new Set())
    } catch (err) { toast.error(err.message) }
  }

  const filtrados = contactos.filter((c) => {
    if (filtros.texto) {
      const q = filtros.texto.toLowerCase()
      if (![c.nombre, c.empresa, c.cargo, c.email_empresarial, c.email_personal].some((v) => v?.toLowerCase().includes(q))) return false
    }
    if (filtros.origen !== 'todos' && c.origen !== filtros.origen) return false
    if (filtros.rubro && !c.cargo?.toLowerCase().includes(filtros.rubro.toLowerCase())) return false
    return true
  })
  const totalPages = Math.ceil(filtrados.length / PAGE_SIZE) || 1
  const paginados = filtrados.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)
  useEffect(() => { setPage(1) }, [filtros])

  if (loading) return <LoadingSpinner />

  return (
    <div>
      <div className="card mb-md">
        <div className="flex-between mb-md">
          <label htmlFor="hist-filtro" className="text-sm text-secondary">Filtros</label>
          <div className="flex gap-sm">
            {selected.size > 0 && <Button size="sm" variant="ghost" onClick={() => setShowBloque(true)}>Armar bloque ({selected.size})</Button>}
            <Button size="sm" variant="ghost" disabled={!contactos.length} onClick={() => exportarContactosExcel(contactos)}>Exportar Excel</Button>
          </div>
        </div>
        <ContactoFiltros filtros={filtros} onChange={setFiltros} />
      </div>
      <div className="card historial-card">
        <div className="flex-between mb-md">
          <span className="text-sm text-secondary">{filtrados.length} contactos</span>
        </div>
        <div className="historial-table-wrap">
          <table className="historial-table">
            <thead>
              <tr>
                <th style={{ width: 36 }}></th>
                <th style={{ width: 36 }} aria-label="Seleccionar"></th>
                <th>Nombre</th><th>Empresa</th><th>Email Personal</th>
                <th style={{ width: 90 }}>Confianza</th><th style={{ width: 80 }}>Origen</th>
                <th style={{ width: 72 }} aria-label="Acciones"></th>
              </tr>
            </thead>
            <tbody>
              {paginados.map((c) => (
                <ContactoDetalleRow key={c.id} contacto={c} expanded={expandedId === c.id}
                  checked={selected.has(c.id)} enriching={enrichingId === c.id}
                  onCheck={() => toggleSelect(c.id)}
                  onToggle={() => setExpandedId(expandedId === c.id ? null : c.id)}
                  onEnrich={() => setEnrichModalId(c.id)}
                  onDelete={() => setDeleteId(c.id)} />
              ))}
              {!paginados.length && <tr><td colSpan={8} className="empty-row">No hay contactos</td></tr>}
            </tbody>
          </table>
        </div>
        {totalPages > 1 && (
          <div className="pagination">
            <Button size="sm" variant="ghost" disabled={page <= 1} onClick={() => setPage(page - 1)}>Anterior</Button>
            <span className="text-sm">Pagina {page} de {totalPages}</span>
            <Button size="sm" variant="ghost" disabled={page >= totalPages} onClick={() => setPage(page + 1)}>Siguiente</Button>
          </div>
        )}
      </div>
      {deleteId && <ConfirmModal message="Este contacto sera eliminado permanentemente." onConfirm={eliminar} onCancel={() => setDeleteId(null)} />}
      {enrichModalId && (
        <Modal title="Enriquecer contacto" onClose={() => setEnrichModalId(null)}>
          <p className="text-sm text-secondary" style={{ marginBottom: '1rem' }}>Seleccioná el método para buscar datos adicionales del contacto.</p>
          <div className="form-group">
            <label htmlFor="enrich-metodo">Método de enriquecimiento</label>
            <select id="enrich-metodo" value={enrichMetodo} onChange={(e) => setEnrichMetodo(e.target.value)}>
              <option value="claude">Claude (IA)</option>
              <option value="perplexity">Perplexity</option>
              <option value="apollo">Apollo</option>
            </select>
          </div>
          <div className="flex gap-sm" style={{ marginTop: '1rem' }}>
            <Button onClick={enriquecer}>Enriquecer</Button>
            <Button variant="ghost" onClick={() => setEnrichModalId(null)}>Cancelar</Button>
          </div>
        </Modal>
      )}
      {showBloque && (
        <Modal title="Armar bloque" onClose={() => setShowBloque(false)}>
          <div className="form-group">
            <label htmlFor="hist-bloque-nombre">Nombre del bloque</label>
            <input id="hist-bloque-nombre" value={nombreBloque} onChange={(e) => setNombreBloque(e.target.value)} placeholder="Ej: Hospitales Córdoba" />
          </div>
          <Button onClick={armarBloque}>Crear bloque con {selected.size} contactos</Button>
        </Modal>
      )}
    </div>
  )
}
