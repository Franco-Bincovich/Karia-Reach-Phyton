import { useState, useEffect } from 'react'
import api from '../hooks/useApi'
import { useToast } from '../context/ToastContext'
import { API_CONTACTS, API_CONTACT_DELETE } from '../constants/api'
import Button from '../components/UI/Button'
import LoadingSpinner from '../components/UI/LoadingSpinner'
import ConfidenceBadge from '../components/UI/ConfidenceBadge'
import ConfirmModal from '../components/UI/ConfirmModal'
import { exportarContactosExcel } from '../utils/exportExcel'
import './Historial.css'

const PAGE_SIZE = 20

const OrigenBadge = ({ value }) => {
  const isAI = value === 'ai' || value === 'apollo'
  const bg = isAI ? 'var(--row-selected)' : '#F3F4F6'
  const color = isAI ? 'var(--primary)' : 'var(--text-secondary)'
  const label = value === 'ai' ? 'IA' : value === 'apollo' ? 'Apollo' : 'Manual'
  return <span className="origen-badge" style={{ background: bg, color }}>{label}</span>
}

export default function Historial() {
  const toast = useToast()
  const [contactos, setContactos] = useState([])
  const [filtro, setFiltro] = useState('')
  const [filtroOrigen, setFiltroOrigen] = useState('todos')
  const [filtroRubro, setFiltroRubro] = useState('')
  const [page, setPage] = useState(1)
  const [expandedId, setExpandedId] = useState(null)
  const [deleteId, setDeleteId] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get(API_CONTACTS)
      .then(({ data }) => setContactos(data.data || []))
      .catch((err) => toast.error(err.message))
      .finally(() => setLoading(false))
  }, [])

  const eliminar = async () => {
    const id = deleteId
    setDeleteId(null)
    try {
      await api.delete(API_CONTACT_DELETE(id))
      toast.success('Contacto eliminado')
      setContactos((prev) => prev.filter((c) => c.id !== id))
      if (expandedId === id) setExpandedId(null)
    } catch (err) { toast.error(err.message) }
  }

  const filtrados = contactos.filter((c) => {
    if (filtro) {
      const q = filtro.toLowerCase()
      const matchTexto = [c.nombre, c.empresa, c.cargo, c.email_empresarial, c.email_personal]
        .some((v) => v?.toLowerCase().includes(q))
      if (!matchTexto) return false
    }
    if (filtroOrigen !== 'todos' && c.origen !== filtroOrigen) return false
    if (filtroRubro) {
      const qr = filtroRubro.toLowerCase()
      if (!c.cargo?.toLowerCase().includes(qr)) return false
    }
    return true
  })

  const totalPages = Math.ceil(filtrados.length / PAGE_SIZE) || 1
  const paginados = filtrados.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)
  useEffect(() => { setPage(1) }, [filtro, filtroOrigen, filtroRubro])

  if (loading) return <LoadingSpinner />

  return (
    <div>
      <div className="card mb-md">
        <div className="flex-between mb-md">
          <label htmlFor="hist-filtro" className="text-sm text-secondary">Filtros</label>
          <Button size="sm" variant="ghost" disabled={!contactos.length} onClick={() => exportarContactosExcel(contactos)}>
            Exportar Excel
          </Button>
        </div>
        <div className="form-row">
          <div className="form-group" style={{ flex: 2 }}>
            <input id="hist-filtro" placeholder="Buscar por nombre, empresa, cargo o email..." value={filtro} onChange={(e) => setFiltro(e.target.value)} />
          </div>
          <div className="form-group" style={{ flex: 1 }}>
            <select id="hist-origen" value={filtroOrigen} onChange={(e) => setFiltroOrigen(e.target.value)}>
              <option value="todos">Todos los origenes</option>
              <option value="ai">IA</option>
              <option value="apollo">Apollo</option>
              <option value="manual">Manual</option>
            </select>
          </div>
          <div className="form-group" style={{ flex: 1 }}>
            <input id="hist-rubro" placeholder="Filtrar por rubro/cargo..." value={filtroRubro} onChange={(e) => setFiltroRubro(e.target.value)} />
          </div>
        </div>
      </div>
      <div className="card historial-card">
        <div className="flex-between mb-md">
          <span className="text-sm text-secondary">{filtrados.length} contactos</span>
        </div>
        <div className="historial-table-wrap">
          <table className="historial-table">
            <thead>
              <tr>
                <th style={{ width: 36 }} aria-label="Expandir"></th>
                <th>Nombre</th>
                <th>Empresa</th>
                <th>Email Personal</th>
                <th style={{ width: 90 }}>Confianza</th>
                <th style={{ width: 80 }}>Origen</th>
                <th style={{ width: 48 }} aria-label="Acciones"></th>
              </tr>
            </thead>
            <tbody>
              {paginados.map((c) => (
                <HistorialRow key={c.id} contacto={c} expanded={expandedId === c.id}
                  onToggle={() => setExpandedId(expandedId === c.id ? null : c.id)}
                  onDelete={() => setDeleteId(c.id)} />
              ))}
              {!paginados.length && <tr><td colSpan={7} className="empty-row">No hay contactos</td></tr>}
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

      {deleteId && (
        <ConfirmModal
          message="Este contacto sera eliminado permanentemente."
          onConfirm={eliminar}
          onCancel={() => setDeleteId(null)}
        />
      )}
    </div>
  )
}

function HistorialRow({ contacto: c, expanded, onToggle, onDelete }) {
  return (
    <>
      <tr className={expanded ? 'row-expanded' : ''}>
        <td><span className="expand-icon" onClick={onToggle}>{expanded ? '\u25BC' : '\u25B6'}</span></td>
        <td>{c.nombre || '-'}</td>
        <td>{c.empresa || '-'}</td>
        <td className="email-cell">{c.email_personal || '-'}</td>
        <td><ConfidenceBadge value={c.confianza} /></td>
        <td><OrigenBadge value={c.origen} /></td>
        <td><button className="delete-btn" title="Eliminar" onClick={onDelete}>&#128465;</button></td>
      </tr>
      {expanded && (
        <tr className="detail-row">
          <td colSpan={7}>
            <div className="detail-panel">
              <div className="detail-grid">
                <div><span className="detail-label">Email Empresarial</span>{c.email_empresarial || '-'}</div>
                <div><span className="detail-label">Cargo</span>{c.cargo || '-'}</div>
                <div><span className="detail-label">Rubro</span>{c.rubro || '-'}</div>
                <div><span className="detail-label">Tel. Empresa</span>{c.telefono_empresa || '-'}</div>
                <div><span className="detail-label">Tel. Personal</span>{c.telefono_personal || '-'}</div>
                <div><span className="detail-label">Fecha creacion</span>{c.created_at ? new Date(c.created_at).toLocaleDateString('es-AR') : '-'}</div>
                {c.linkedin_url && (
                  <div><span className="detail-label">LinkedIn</span><a href={c.linkedin_url} target="_blank" rel="noopener noreferrer">Ver perfil</a></div>
                )}
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  )
}
