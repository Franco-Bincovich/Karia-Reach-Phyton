import { useState } from 'react'
import api from '../../hooks/useApi'
import { useToast } from '../../context/ToastContext'
import { useGmailStatus } from '../../hooks/useGmailStatus'
import { API_GMAIL_AUTHORIZE, API_GMAIL_DISCONNECT } from '../../constants/api'
import Button from './Button'
import Badge from './Badge'
import ConfirmModal from './ConfirmModal'

export default function GmailConfig() {
  const toast = useToast()
  const { estado, cargando, error, refrescar } = useGmailStatus()
  const [loadingConectar, setLoadingConectar] = useState(false)
  const [loadingDesconectar, setLoadingDesconectar] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)

  const conectar = async () => {
    setLoadingConectar(true)
    try {
      const { data } = await api.get(API_GMAIL_AUTHORIZE)
      window.location.href = data.data.url
    } catch (err) {
      toast.error(err.message)
      setLoadingConectar(false)
    }
  }

  const desconectar = async () => {
    setShowConfirm(false)
    setLoadingDesconectar(true)
    try {
      await api.post(API_GMAIL_DISCONNECT)
      toast.success('Gmail desconectado')
      refrescar()
    } catch (err) {
      toast.error(err.message)
    } finally {
      setLoadingDesconectar(false)
    }
  }

  if (cargando) {
    return (
      <div className="card mb-md" style={{ maxWidth: 600 }}>
        <div className="flex-between mb-md">
          <h3>Gmail</h3>
          <Badge variant="info">...</Badge>
        </div>
        <p className="text-sm text-secondary">Cargando estado de Gmail...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="card mb-md" style={{ maxWidth: 600 }}>
        <div className="flex-between mb-md">
          <h3>Gmail</h3>
          <Badge variant="error">Error</Badge>
        </div>
        <p className="text-sm text-secondary mb-md">{error}</p>
        <Button variant="ghost" onClick={refrescar}>Reintentar</Button>
      </div>
    )
  }

  const conectado = estado?.conectado

  return (
    <>
      <div className="card mb-md" style={{ maxWidth: 600 }}>
        <div className="flex-between mb-md">
          <h3>Gmail</h3>
          <Badge variant={conectado ? 'success' : 'error'}>
            {conectado ? 'Conectado' : 'No conectado'}
          </Badge>
        </div>
        <p className="text-sm text-secondary mb-md">
          Conectá tu cuenta de Gmail para enviar campañas de email directamente
          desde tu cuenta personal o corporativa.
        </p>
        {conectado ? (
          <>
            <div className="text-sm mb-md">
              <div><strong>Cuenta:</strong> {estado.email}</div>
              {estado.ultimo_uso && (
                <div className="text-secondary" style={{ marginTop: 'var(--space-xs)' }}>
                  Último uso: {new Date(estado.ultimo_uso).toLocaleString('es-AR')}
                </div>
              )}
            </div>
            <Button variant="danger" loading={loadingDesconectar} onClick={() => setShowConfirm(true)}>
              Desconectar
            </Button>
          </>
        ) : (
          <Button loading={loadingConectar} onClick={conectar}>
            Conectar Gmail
          </Button>
        )}
      </div>
      {showConfirm && (
        <ConfirmModal
          message="Se desconectará tu cuenta de Gmail. Deberás reconectarla para poder enviar campañas."
          onConfirm={desconectar}
          onCancel={() => setShowConfirm(false)}
        />
      )}
    </>
  )
}
