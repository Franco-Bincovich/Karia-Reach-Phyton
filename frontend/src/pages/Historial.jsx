import { useState, useEffect } from 'react'
import api from '../hooks/useApi'
import { useToast } from '../context/ToastContext'
import { API_CONTACTS, API_CONTACT_DELETE, API_BLOQUES, API_BLOQUE_CONTACTOS, API_APIFY_ENRICH } from '../constants/api'
import Button from '../components/UI/Button'
import LoadingSpinner from '../components/UI/LoadingSpinner'
import ConfidenceBadge from '../components/UI/ConfidenceBadge'
import ConfirmModal from '../components/UI/ConfirmModal'
import Modal from '../components/UI/Modal'
import { exportarContactosExcel } from '../utils/exportExcel'
import './Historial.css'

const PAGE_SIZE = 20

const OrigenBadge = ({ value }) => {
  const isAI = value === 'ai' || value === 'apollo'
  const bg = isAI ? 'var(--row-selected)' : '#F3F4F6'
  const color = isAI ? 'var(--primary)' : 'var(--text-secondary)'
  const label = value === 'ai' ? 'IA' : value === 'apollo' ? 'Apollo' : value === 'apify' ? 'Apify' : value === 'perplexity' ? 'Perplexity' : 'Manual'
  return <span className="origen-badge" style={{ background: bg, color }}>{label}</span>
}

export default function Historial() {
  const toast = useToast()
  const [contactos, setContactos] = useState([])
  const [selected, setSelected] = useState(new Set())
  const [filtro, setFiltro] = useState('')
  const [filtroOrigen, setFiltroOrigen] = useState('todos')
  const [filtroRubro, setFiltroRubro] = useState('')
  const [page, setPage] = useState(1)
  const [expandedId, setExpandedId] = useState(null)
  const [deleteId, setDeleteId] = useState(null)
  const [loading, setLoading] = useState(true)
  const [enrichingId, setEnrichingId] = useState(null)
  const [showBloque, setShowBloque] = useState(false)
  const [nombreBloque, setNombreBloque] = useState('')

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
      setSelected((prev) => { const s = new Set(prev); s.delete(id); return s })
      if (expandedId === id) setExpandedId(null)
    } catch (err) { toast.error(err.message) }
  }

  const toggleSelect = (id) => {
    setSelected((prev) => {
      const s = new Set(prev)
      s.has(id) ? s.delete(id) : s.add(id)
      return s
    })
  }

  const enriquecer = async (id) => {
    setEnrichingId(id)
    try {
      await api.post(API_APIFY_ENRICH, { contacto_id: id })
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
          <div className="flex gap-sm">
            {selected.size > 0 && <Button size="sm" variant="ghost" onClick={() => setShowBloque(true)}>Armar bloque ({selected.size})</Button>}
            <Button size="sm" variant="ghost" disabled={!contactos.length} onClick={() => exportarContactosExcel(contactos)}>Exportar Excel</Button>
          </div>
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
              <option value="perplexity">Perplexity</option>
              <option value="apify">Apify</option>
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
                <th style={{ width: 36 }}></th>
                <th style={{ width: 36 }} aria-label="Seleccionar"></th>
                <th>Nombre</th>
                <th>Empresa</th>
                <th>Email Personal</th>
                <th style={{ width: 90 }}>Confianza</th>
                <th style={{ width: 80 }}>Origen</th>
                <th style={{ width: 72 }} aria-label="Acciones"></th>
              </tr>
            </thead>
            <tbody>
              {paginados.map((c) => (
                <HistorialRow key={c.id} contacto={c} expanded={expandedId === c.id}
                  checked={selected.has(c.id)} enriching={enrichingId === c.id}
                  onCheck={() => toggleSelect(c.id)}
                  onToggle={() => setExpandedId(expandedId === c.id ? null : c.id)}
                  onEnrich={() => enriquecer(c.id)}
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

      {deleteId && (
        <ConfirmModal message="Este contacto sera eliminado permanentemente." onConfirm={eliminar} onCancel={() => setDeleteId(null)} />
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

function HistorialRow({ contacto: c, expanded, checked, enriching, onCheck, onToggle, onEnrich, onDelete }) {
  const canEnrich = c.origen === 'apify'
  return (
    <>
      <tr className={expanded ? 'row-expanded' : ''}>
        <td><span className="expand-icon" onClick={onToggle}>{expanded ? '\u25BC' : '\u25B6'}</span></td>
        <td><input type="checkbox" checked={checked} onChange={onCheck} /></td>
        <td>{c.nombre || '-'}</td>
        <td>{c.empresa || '-'}</td>
        <td className="email-cell">{c.email_personal || '-'}</td>
        <td><ConfidenceBadge value={c.confianza} /></td>
        <td><OrigenBadge value={c.origen} /></td>
        <td className="flex gap-sm" style={{ justifyContent: 'flex-end' }}>
          {canEnrich && (
            <button className="delete-btn" title="Enriquecer con Apify" disabled={enriching} onClick={onEnrich}
              style={{ opacity: enriching ? 0.5 : 1 }}>{enriching ? '...' : '⚡'}</button>
          )}
          <button className="delete-btn" title="Eliminar" onClick={onDelete}>&#128465;</button>
        </td>
      </tr>
      {expanded && (
        <tr className="detail-row">
          <td colSpan={8}>
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
                {c.instagram_username && (
                  <div><span className="detail-label">Instagram</span><a href={`https://instagram.com/${c.instagram_username}`} target="_blank" rel="noopener noreferrer">@{c.instagram_username}</a></div>
                )}
                {c.facebook_url && (
                  <div><span className="detail-label">Facebook</span><a href={c.facebook_url} target="_blank" rel="noopener noreferrer">Ver página</a></div>
                )}
                {c.whatsapp && (
                  <div><span className="detail-label">WhatsApp</span><a href={`https://wa.me/${c.whatsapp.replace(/\D/g, '')}`} target="_blank" rel="noopener noreferrer">{c.whatsapp}</a></div>
                )}
                {c.twitter_url && (
                  <div><span className="detail-label">Twitter</span><a href={c.twitter_url} target="_blank" rel="noopener noreferrer">Ver perfil</a></div>
                )}
                {c.tiktok_username && (
                  <div><span className="detail-label">TikTok</span><a href={`https://tiktok.com/@${c.tiktok_username}`} target="_blank" rel="noopener noreferrer">@{c.tiktok_username}</a></div>
                )}
                {c.website && (
                  <div><span className="detail-label">Website</span><a href={c.website} target="_blank" rel="noopener noreferrer">{(() => { try { return new URL(c.website).hostname.replace(/^www\./, '') } catch { return c.website } })()}</a></div>
                )}
                {c.direccion && (
                  <div><span className="detail-label">Dirección</span>{c.direccion}</div>
                )}
                {(c.ciudad || c.pais) && (
                  <div><span className="detail-label">Ubicación</span>{[c.ciudad, c.pais].filter(Boolean).join(', ')}</div>
                )}
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  )
}
