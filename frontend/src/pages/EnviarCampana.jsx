import { useState, useEffect } from 'react'
import api from '../hooks/useApi'
import { useToast } from '../context/ToastContext'
import { API_COMPOSE_TEMPLATES, API_CONTACTS, API_SEND_CAMPAIGN, API_BLOQUES, API_BLOQUE_CONTACTOS, API_CAMPANAS_PROGRAMADAS } from '../constants/api'
import Button from '../components/UI/Button'
import LoadingSpinner from '../components/UI/LoadingSpinner'
import ContactSelector from '../components/ContactSelector'
import ConfirmModal from '../components/UI/ConfirmModal'

const DIAS = ['Lun', 'Mar', 'Mie', 'Jue', 'Vie', 'Sab', 'Dom']

export default function EnviarCampana() {
  const toast = useToast()
  const [templates, setTemplates] = useState([])
  const [contactos, setContactos] = useState([])
  const [bloques, setBloques] = useState([])
  const [bloqueId, setBloqueId] = useState('')
  const [form, setForm] = useState({ nombre: '', template_id: '' })
  const [loading, setLoading] = useState(false)
  const [resultado, setResultado] = useState(null)
  const [showConfirm, setShowConfirm] = useState(false)
  // Scheduling
  const [modoEnvio, setModoEnvio] = useState('ahora')      // 'ahora' | 'programar'
  const [tipoSchedule, setTipoSchedule] = useState('unica') // 'unica' | 'recurrente'
  const [fechaEnvio, setFechaEnvio] = useState('')          // datetime-local
  const [horaEnvio, setHoraEnvio] = useState('09:00')
  const [diasSemana, setDiasSemana] = useState([])

  useEffect(() => {
    api.get(API_COMPOSE_TEMPLATES).then(({ data }) => setTemplates(data.data || [])).catch((err) => toast.error(err.message))
    api.get(API_CONTACTS).then(({ data }) => setContactos((data.data || []).map((c) => ({ ...c, _selected: false })))).catch((err) => toast.error(err.message))
    api.get(API_BLOQUES).then(({ data }) => setBloques(data.data || [])).catch((err) => toast.error(err.message))
  }, [])

  const cargarBloque = async (id) => {
    setBloqueId(id)
    if (!id) { setContactos((prev) => prev.map((c) => ({ ...c, _selected: false }))); return }
    try {
      const { data } = await api.get(API_BLOQUE_CONTACTOS(id))
      const bloqueIds = new Set((data.data || []).map((c) => c.id))
      setContactos((prev) => prev.map((c) => ({ ...c, _selected: bloqueIds.has(c.id) })))
      toast.success(`${bloqueIds.size} contactos del bloque cargados`)
    } catch (err) { toast.error(err.message) }
  }

  const toggleDia = (i) => setDiasSemana((prev) => prev.includes(i) ? prev.filter((x) => x !== i) : [...prev, i])

  const validar = () => {
    if (!form.nombre.trim()) { toast.error('Ingresa un nombre para la campana'); return false }
    if (!form.template_id) { toast.error('Selecciona una plantilla'); return false }
    if (!contactos.some((c) => c._selected)) { toast.error('Selecciona al menos un contacto'); return false }
    if (modoEnvio === 'programar') {
      if (tipoSchedule === 'unica' && !fechaEnvio) { toast.error('Selecciona fecha y hora'); return false }
      if (tipoSchedule === 'recurrente' && !diasSemana.length) { toast.error('Selecciona al menos un dia'); return false }
    }
    return true
  }

  const enviar = async () => {
    setShowConfirm(false)
    setLoading(true)
    try {
      const sel = contactos.filter((c) => c._selected)
      if (modoEnvio === 'ahora') {
        const { data } = await api.post(API_SEND_CAMPAIGN, { nombre: form.nombre, template_id: form.template_id, contact_ids: sel.map((c) => c.id), scheduled_at: null })
        setResultado(data.data)
        toast.success(`Campana enviada: ${data.data?.sent_count ?? 0} emails`)
      } else {
        const horaFinal = tipoSchedule === 'unica' ? (fechaEnvio.split('T')[1]?.substring(0, 5) || horaEnvio) : horaEnvio
        const payload = {
          nombre: form.nombre, template_id: form.template_id,
          contact_ids: sel.map((c) => c.id), bloque_id: bloqueId || undefined,
          tipo: tipoSchedule, hora_envio: horaFinal,
          ...(tipoSchedule === 'unica' ? { fecha_envio: new Date(fechaEnvio).toISOString() } : { dias_semana: diasSemana }),
        }
        await api.post(API_CAMPANAS_PROGRAMADAS, payload)
        setResultado(null)
        toast.success('Campana programada exitosamente')
      }
    } catch (err) { toast.error(err.message) }
    finally { setLoading(false) }
  }

  if (loading) return <LoadingSpinner text={modoEnvio === 'ahora' ? 'Enviando campana...' : 'Programando campana...'} />

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
          <label htmlFor="camp-bloque">Usar bloque (opcional)</label>
          <select id="camp-bloque" value={bloqueId} onChange={(e) => cargarBloque(e.target.value)}>
            <option value="">Seleccionar manualmente...</option>
            {bloques.map((b) => <option key={b.id} value={b.id}>{b.nombre} ({b.cantidad_contactos} contactos)</option>)}
          </select>
        </div>
        <div className="form-group">
          <label>Contactos</label>
          <ContactSelector contactos={contactos} onChange={setContactos} />
        </div>

        <div className="form-group">
          <label>Modo de envio</label>
          <div className="flex gap-md">
            {[['ahora', 'Enviar ahora'], ['programar', 'Programar envio']].map(([val, label]) => (
              <label key={val} style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
                <input type="radio" name="modo-envio" checked={modoEnvio === val} onChange={() => setModoEnvio(val)} />
                {label}
              </label>
            ))}
          </div>
        </div>

        {modoEnvio === 'programar' && (
          <>
            <div className="form-group">
              <label htmlFor="tipo-schedule">Tipo de programacion</label>
              <select id="tipo-schedule" value={tipoSchedule} onChange={(e) => setTipoSchedule(e.target.value)}>
                <option value="unica">Una vez</option>
                <option value="recurrente">Recurrente</option>
              </select>
            </div>
            {tipoSchedule === 'unica' ? (
              <div className="form-group">
                <label htmlFor="fecha-envio">Fecha y hora de envio</label>
                <input id="fecha-envio" type="datetime-local" value={fechaEnvio} onChange={(e) => setFechaEnvio(e.target.value)} />
              </div>
            ) : (
              <>
                <div className="form-group">
                  <label>Dias de la semana</label>
                  <div className="flex gap-sm" style={{ flexWrap: 'wrap' }}>
                    {DIAS.map((d, i) => (
                      <label key={i} style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}>
                        <input type="checkbox" checked={diasSemana.includes(i)} onChange={() => toggleDia(i)} />
                        {d}
                      </label>
                    ))}
                  </div>
                </div>
                <div className="form-group">
                  <label htmlFor="hora-envio">Hora de envio</label>
                  <input id="hora-envio" type="time" value={horaEnvio} onChange={(e) => setHoraEnvio(e.target.value)} />
                </div>
              </>
            )}
          </>
        )}

        <Button onClick={() => validar() && setShowConfirm(true)} loading={loading}>
          {modoEnvio === 'ahora' ? 'Enviar campana' : 'Programar campana'}
        </Button>
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
        <ConfirmModal title={modoEnvio === 'ahora' ? 'Confirmar envio' : 'Confirmar programacion'}
          message={`${modoEnvio === 'ahora' ? 'Enviar' : 'Programar'} campana "${form.nombre}" a ${contactos.filter((c) => c._selected).length} contactos?`}
          confirmLabel={modoEnvio === 'ahora' ? 'Enviar' : 'Programar'} confirmVariant="primary"
          onConfirm={enviar} onCancel={() => setShowConfirm(false)} />
      )}
    </div>
  )
}
