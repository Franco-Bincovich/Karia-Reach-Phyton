import { useState, useEffect, useCallback } from 'react'
import api from '../hooks/useApi'
import { useToast } from '../context/ToastContext'
import { API_CAMPANAS_PROGRAMADAS, API_CAMPANA_PROGRAMADA_CANCEL } from '../constants/api'
import Button from '../components/UI/Button'
import LoadingSpinner from '../components/UI/LoadingSpinner'
import ConfirmModal from '../components/UI/ConfirmModal'

const DIAS = ['Lun', 'Mar', 'Mie', 'Jue', 'Vie', 'Sab', 'Dom']

const ESTADO_STYLE = {
  programada: { background: '#EFF6FF', color: '#2563EB' },
  ejecutada:  { background: '#F0FDF4', color: '#16A34A' },
  cancelada:  { background: '#F3F4F6', color: '#6B7280' },
  fallida:    { background: '#FEF2F2', color: '#DC2626' },
}

function EstadoBadge({ estado }) {
  const style = ESTADO_STYLE[estado] || ESTADO_STYLE.cancelada
  return (
    <span style={{ ...style, padding: '2px 8px', borderRadius: 4, fontSize: 12, fontWeight: 600 }}>
      {estado}
    </span>
  )
}

function ResumenSchedule({ campana }) {
  if (campana.tipo === 'unica') {
    const fecha = campana.fecha_envio ? new Date(campana.fecha_envio).toLocaleString('es-AR') : '—'
    return <span>Una vez · {fecha}</span>
  }
  const dias = (campana.dias_semana || []).map((d) => DIAS[d]).join(', ')
  return <span>Recurrente · {dias || '—'} · {campana.hora_envio}</span>
}

export default function CampanasProgramadas() {
  const toast = useToast()
  const [campanas, setCampanas] = useState([])
  const [loading, setLoading] = useState(true)
  const [cancelId, setCancelId] = useState(null)

  const cargar = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await api.get(API_CAMPANAS_PROGRAMADAS)
      setCampanas(data.data || [])
    } catch (err) {
      toast.error(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { cargar() }, [cargar])

  const cancelar = async () => {
    const id = cancelId
    setCancelId(null)
    try {
      await api.delete(API_CAMPANA_PROGRAMADA_CANCEL(id))
      toast.success('Campana cancelada')
      setCampanas((prev) => prev.map((c) => c.id === id ? { ...c, estado: 'cancelada' } : c))
    } catch (err) {
      toast.error(err.message)
    }
  }

  if (loading) return <LoadingSpinner />

  return (
    <div>
      <div className="card">
        <div className="flex-between mb-md">
          <span className="text-sm text-secondary">{campanas.length} campana(s) programada(s)</span>
          <Button size="sm" variant="ghost" onClick={cargar}>Actualizar</Button>
        </div>

        {campanas.length === 0 ? (
          <p className="text-secondary text-sm">No hay campanas programadas. Usa "Enviar Campana" para crear una.</p>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                <th style={{ textAlign: 'left', padding: '8px 12px', fontSize: 13 }}>Nombre</th>
                <th style={{ textAlign: 'left', padding: '8px 12px', fontSize: 13 }}>Programacion</th>
                <th style={{ textAlign: 'left', padding: '8px 12px', fontSize: 13 }}>Estado</th>
                <th style={{ textAlign: 'left', padding: '8px 12px', fontSize: 13 }}>Ult. ejecucion</th>
                <th style={{ width: 80 }}></th>
              </tr>
            </thead>
            <tbody>
              {campanas.map((c) => (
                <tr key={c.id} style={{ borderBottom: '1px solid var(--border)' }}>
                  <td style={{ padding: '10px 12px', fontWeight: 500 }}>{c.nombre}</td>
                  <td style={{ padding: '10px 12px', fontSize: 13, color: 'var(--text-secondary)' }}>
                    <ResumenSchedule campana={c} />
                  </td>
                  <td style={{ padding: '10px 12px' }}><EstadoBadge estado={c.estado} /></td>
                  <td style={{ padding: '10px 12px', fontSize: 13, color: 'var(--text-secondary)' }}>
                    {c.ultima_ejecucion ? new Date(c.ultima_ejecucion).toLocaleString('es-AR') : '—'}
                  </td>
                  <td style={{ padding: '10px 12px' }}>
                    {c.estado === 'programada' && (
                      <Button size="sm" variant="ghost" onClick={() => setCancelId(c.id)}>Cancelar</Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {cancelId && (
        <ConfirmModal
          title="Cancelar campana"
          message={`Cancelar la campana "${campanas.find((c) => c.id === cancelId)?.nombre}"?`}
          confirmLabel="Cancelar campana"
          confirmVariant="danger"
          onConfirm={cancelar}
          onCancel={() => setCancelId(null)}
        />
      )}
    </div>
  )
}
