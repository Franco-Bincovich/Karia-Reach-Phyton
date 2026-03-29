import { useState } from 'react'
import Button from './UI/Button'
import ConfirmModal from './UI/ConfirmModal'

export default function TemplateList({ templates, onEliminar }) {
  const [deleteId, setDeleteId] = useState(null)

  if (!templates.length) return null

  const confirmarEliminar = () => {
    onEliminar(deleteId)
    setDeleteId(null)
  }

  return (
    <div className="card mt-lg">
      <h3 className="mb-md">Plantillas guardadas</h3>
      {templates.map((t) => (
        <div key={t.id} className="flex-between" style={{ padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
          <div>
            <strong>{t.nombre}</strong>
            <span className="text-sm text-secondary"> — {t.asunto}</span>
          </div>
          <Button size="sm" variant="danger" onClick={() => setDeleteId(t.id)}>Eliminar</Button>
        </div>
      ))}

      {deleteId && (
        <ConfirmModal
          message="Esta plantilla sera eliminada permanentemente."
          onConfirm={confirmarEliminar}
          onCancel={() => setDeleteId(null)}
        />
      )}
    </div>
  )
}
