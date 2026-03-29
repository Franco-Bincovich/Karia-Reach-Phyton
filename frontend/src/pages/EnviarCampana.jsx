import { useState, useEffect } from 'react'
import api from '../hooks/useApi'
import { useToast } from '../context/ToastContext'
import { API_COMPOSE_TEMPLATES, API_CONTACTS, API_SEND_CAMPAIGN } from '../constants/api'
import Button from '../components/UI/Button'
import LoadingSpinner from '../components/UI/LoadingSpinner'
import ContactSelector from '../components/ContactSelector'
import ConfirmModal from '../components/UI/ConfirmModal'

export default function EnviarCampana() {
  const toast = useToast()
  const [templates, setTemplates] = useState([])
  const [contactos, setContactos] = useState([])
  const [form, setForm] = useState({ nombre: '', template_id: '' })
  const [loading, setLoading] = useState(false)
  const [resultado, setResultado] = useState(null)
  const [showConfirm, setShowConfirm] = useState(false)

  useEffect(() => {
    api.get(API_COMPOSE_TEMPLATES)
      .then(({ data }) => setTemplates(data.data || []))
      .catch((err) => toast.error(err.message))
    api.get(API_CONTACTS)
      .then(({ data }) => setContactos((data.data || []).map((c) => ({ ...c, _selected: false }))))
      .catch((err) => toast.error(err.message))
  }, [])

  const validar = () => {
    if (!form.nombre.trim()) { toast.error('Ingresa un nombre para la campana'); return false }
    if (!form.template_id) { toast.error('Selecciona una plantilla'); return false }
    if (!contactos.some((c) => c._selected)) { toast.error('Selecciona al menos un contacto'); return false }
    return true
  }

  const enviar = async () => {
    setShowConfirm(false)
    setLoading(true)
    try {
      const sel = contactos.filter((c) => c._selected)
      const payload = {
        nombre: form.nombre, template_id: form.template_id,
        contact_ids: sel.map((c) => c.id), scheduled_at: null,
      }
      const { data } = await api.post(API_SEND_CAMPAIGN, payload)
      setResultado(data.data)
      toast.success(`Campana enviada: ${data.data?.sent_count ?? 0} emails`)
    } catch (err) { toast.error(err.message) }
    finally { setLoading(false) }
  }

  if (loading) return <LoadingSpinner text="Enviando campana..." />

  return (
    <div>
      <div className="card mb-md">
        <div className="form-group">
          <label htmlFor="camp-nombre">Nombre de la campana</label>
          <input id="camp-nombre" value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} placeholder="Ej: Campana Q1 2026" />
        </div>
        <div className="form-group">
          <label htmlFor="camp-template">Plantilla</label>
          <select id="camp-template" value={form.template_id} onChange={(e) => setForm({ ...form, template_id: e.target.value })}>
            <option value="">Seleccionar plantilla...</option>
            {templates.map((t) => <option key={t.id} value={t.id}>{t.nombre} — {t.asunto}</option>)}
          </select>
        </div>
        <div className="form-group">
          <label>Contactos</label>
          <ContactSelector contactos={contactos} onChange={setContactos} />
        </div>
        <div className="form-group">
          <label htmlFor="camp-schedule">Programar envio</label>
          <input id="camp-schedule" type="datetime-local" disabled style={{ opacity: 0.5 }} />
          <span className="text-sm text-secondary" style={{ marginTop: 4, display: 'block' }}>
            Proximamente — el envio programado estara disponible en la proxima version.
          </span>
        </div>
        <Button onClick={() => validar() && setShowConfirm(true)} loading={loading}>Enviar campana</Button>
      </div>

      {resultado && (
        <div className="card">
          <h3 className="mb-md">Resultado</h3>
          <div className="form-row">
            <div><strong>Estado:</strong> {resultado.status}</div>
            <div><strong>Enviados:</strong> {resultado.sent_count}</div>
            <div><strong>Fallidos:</strong> {resultado.failed_count}</div>
          </div>
        </div>
      )}

      {showConfirm && (
        <ConfirmModal title="Confirmar envio"
          message={`Enviar campana "${form.nombre}" a ${contactos.filter((c) => c._selected).length} contactos?`}
          confirmLabel="Enviar" confirmVariant="primary"
          onConfirm={enviar} onCancel={() => setShowConfirm(false)} />
      )}
    </div>
  )
}
