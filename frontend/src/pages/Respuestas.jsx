import { useState, useEffect, useRef } from 'react'
import api from '../hooks/useApi'
import { useToast } from '../context/ToastContext'
import { API_SEND_CAMPAIGNS, API_REPLIES, API_REPLIES_SYNC, API_REPLIES_RESPOND, API_REPLIES_READ } from '../constants/api'
import Button from '../components/UI/Button'
import Badge from '../components/UI/Badge'
import LoadingSpinner from '../components/UI/LoadingSpinner'
import './Respuestas.css'

export default function Respuestas() {
  const toast = useToast()
  const toastRef = useRef(toast)
  toastRef.current = toast
  const [campanas, setCampanas] = useState([])
  const [campanaId, setCampanaId] = useState('')
  const [respuestas, setRespuestas] = useState([])
  const [selected, setSelected] = useState(null)
  const [replyText, setReplyText] = useState('')
  const [loading, setLoading] = useState(false)
  const [syncing, setSyncing] = useState(false)

  useEffect(() => {
    api.get(API_SEND_CAMPAIGNS)
      .then(({ data }) => setCampanas(data.data || []))
      .catch((err) => toastRef.current.error(err.message))
  }, [])

  const cargar = async (id) => {
    setCampanaId(id)
    if (!id) return
    setLoading(true)
    try {
      const { data } = await api.get(`${API_REPLIES}/${id}`)
      setRespuestas(data.data || [])
    } catch (err) { toast.error(err.message) }
    finally { setLoading(false) }
  }

  const sincronizar = async () => {
    setSyncing(true)
    try {
      const { data } = await api.post(API_REPLIES_SYNC(campanaId))
      toast.success(`${data.nuevas} respuestas nuevas`)
      cargar(campanaId)
    } catch (err) { toast.error(err.message) }
    finally { setSyncing(false) }
  }

  const marcarLeida = async (id) => {
    try {
      await api.patch(API_REPLIES_READ(id))
      setRespuestas((prev) => prev.map((r) => r.id === id ? { ...r, leido: true } : r))
    } catch (err) { toast.error(err.message) }
  }

  const responder = async () => {
    if (!replyText.trim()) return
    try {
      await api.post(API_REPLIES_RESPOND(selected.id), { cuerpo: replyText })
      toast.success('Respuesta enviada')
      setReplyText('')
      setSelected({ ...selected, respondido: true })
      setRespuestas((prev) => prev.map((r) => r.id === selected.id ? { ...r, respondido: true } : r))
    } catch (err) { toast.error(err.message) }
  }

  return (
    <div className="respuestas-layout">
      <div className="respuestas-main">
        <div className="card mb-md">
          <label htmlFor="resp-campana" className="text-sm text-secondary mb-md" style={{ display: 'block' }}>Campana</label>
          <div className="flex gap-sm">
            <select id="resp-campana" value={campanaId} onChange={(e) => cargar(e.target.value)} style={{ flex: 1 }}>
              <option value="">Seleccionar campana...</option>
              {campanas.map((c) => <option key={c.id} value={c.id}>{c.nombre}</option>)}
            </select>
            <Button variant="teal" loading={syncing} onClick={sincronizar} disabled={!campanaId}>Sincronizar</Button>
          </div>
        </div>

        {loading ? <LoadingSpinner /> : (
          <div className="card">
            {respuestas.map((r) => (
              <div key={r.id} className={`reply-item ${!r.leido ? 'unread' : ''} ${selected?.id === r.id ? 'active' : ''}`}
                onClick={() => { setSelected(r); if (!r.leido) marcarLeida(r.id) }}>
                <div className="flex-between">
                  <strong>{r.de}</strong>
                  <span className="text-sm text-secondary">{r.fecha ? new Date(r.fecha).toLocaleDateString('es-AR') : ''}</span>
                </div>
                <div className="text-sm">{r.asunto}</div>
                <div className="flex gap-sm mt-md">
                  {!r.leido && <Badge variant="info">Nuevo</Badge>}
                  {r.respondido && <Badge variant="success">Respondido</Badge>}
                </div>
              </div>
            ))}
            {!respuestas.length && <div className="empty-replies">Sin respuestas</div>}
          </div>
        )}
      </div>

      {selected && (
        <div className="respuestas-panel card">
          <h3>{selected.asunto}</h3>
          <p className="text-sm text-secondary mb-md">De: {selected.de}</p>
          <div className="reply-body">{selected.cuerpo}</div>
          <div className="mt-lg">
            <label htmlFor="resp-reply">Responder</label>
            <textarea id="resp-reply" rows={4} value={replyText} onChange={(e) => setReplyText(e.target.value)} placeholder="Escribi tu respuesta..." />
            <Button className="mt-md" onClick={responder}>Enviar respuesta</Button>
          </div>
        </div>
      )}
    </div>
  )
}
