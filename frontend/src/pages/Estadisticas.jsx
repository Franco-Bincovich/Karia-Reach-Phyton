import { useState, useEffect } from 'react'
import api from '../hooks/useApi'
import { useToast } from '../context/ToastContext'
import { API_SEND_STATS, API_SEND_CAMPAIGNS, API_SEND_CAMPAIGN_STATS } from '../constants/api'
import Badge from '../components/UI/Badge'
import Table from '../components/UI/Table'
import LoadingSpinner from '../components/UI/LoadingSpinner'
import './Estadisticas.css'

const STATUS_VARIANTS = {
  completed: 'success', failed: 'error', sending: 'info',
  partial: 'media', draft: 'manual', scheduled: 'manual',
}

export default function Estadisticas() {
  const toast = useToast()
  const [stats, setStats] = useState(null)
  const [campanas, setCampanas] = useState([])
  const [detalle, setDetalle] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([api.get(API_SEND_STATS), api.get(API_SEND_CAMPAIGNS)])
      .then(([s, c]) => { setStats(s.data.data); setCampanas(c.data.data || []) })
      .catch((err) => toast.error(err.message))
      .finally(() => setLoading(false))
  }, [])

  const verDetalle = async (row) => {
    try {
      const { data } = await api.get(API_SEND_CAMPAIGN_STATS(row.id))
      setDetalle(data.data)
    } catch (err) { toast.error(err.message) }
  }

  if (loading) return <LoadingSpinner />

  const CAMP_COLS = [
    { key: 'nombre', label: 'Campana' },
    { key: 'sent_count', label: 'Enviados' },
    { key: 'failed_count', label: 'Fallidos' },
    { key: 'status', label: 'Estado', render: (v) => (
      <Badge variant={STATUS_VARIANTS[v] || 'info'}>{v}</Badge>
    )},
    { key: 'created_at', label: 'Fecha', render: (v) => v ? new Date(v).toLocaleDateString('es-AR') : '-' },
  ]

  const DET_COLS = [
    { key: 'email_destinatario', label: 'Destinatario' },
    { key: 'asunto', label: 'Asunto' },
    { key: 'exitoso', label: 'Envio', render: (v) => <Badge variant={v ? 'success' : 'error'}>{v ? 'OK' : 'Fallo'}</Badge> },
    { key: 'opened_at', label: 'Abierto', render: (v) => v ? new Date(v).toLocaleString('es-AR') : 'No' },
    { key: 'respondido', label: 'Respondido', render: (v) => v ? <Badge variant="success">Si</Badge> : 'No' },
    { key: 'error', label: 'Error' },
  ]

  return (
    <div>
      {stats && (
        <div className="stats-cards mb-md">
          <div className="stat-card"><div className="stat-value">{stats.total_campanas}</div><div className="stat-label">Campanas</div></div>
          <div className="stat-card"><div className="stat-value">{stats.total_emails_enviados}</div><div className="stat-label">Enviados</div></div>
          <div className="stat-card"><div className="stat-value">{stats.tasa_apertura_global}%</div><div className="stat-label">Tasa apertura</div></div>
          <div className="stat-card"><div className="stat-value">{stats.total_respondidos || 0}</div><div className="stat-label">Respondidos</div></div>
        </div>
      )}

      <div className="card mb-md">
        <h3 className="mb-md">Campanas</h3>
        <Table columns={CAMP_COLS} data={campanas} onRowClick={verDetalle} emptyMessage="No hay campanas" />
      </div>

      {detalle && (
        <div className="card">
          <h3 className="mb-md">Detalle: {detalle.campana?.nombre}</h3>
          <div className="stats-detail mb-md">
            <span>Enviados: <strong>{detalle.total_enviados}</strong></span>
            <span>Fallidos: <strong>{detalle.total_fallidos}</strong></span>
            <span>Abiertos: <strong>{detalle.total_abiertos}</strong></span>
            <span>Sin abrir: <strong>{detalle.total_sin_abrir}</strong></span>
            <span>Respondidos: <strong>{detalle.total_respondidos}</strong></span>
            <span>Tasa apertura: <strong>{detalle.tasa_apertura}%</strong></span>
          </div>
          <Table columns={DET_COLS} data={detalle.resultados || []} />
        </div>
      )}
    </div>
  )
}
