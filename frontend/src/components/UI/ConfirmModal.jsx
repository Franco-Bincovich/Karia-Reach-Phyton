import Modal from './Modal'
import Button from './Button'

/**
 * Modal de confirmacion reutilizable. Reemplaza confirm() nativo.
 * Props: title, message, onConfirm, onCancel, confirmLabel, confirmVariant.
 */
export default function ConfirmModal({
  title = 'Confirmar eliminacion',
  message = 'Esta accion no se puede deshacer.',
  onConfirm,
  onCancel,
  confirmLabel = 'Eliminar',
  confirmVariant = 'danger',
}) {
  return (
    <Modal title={title} onClose={onCancel}>
      <p className="text-sm text-secondary mb-md">{message}</p>
      <div className="flex gap-sm" style={{ justifyContent: 'flex-end' }}>
        <Button variant="ghost" onClick={onCancel}>Cancelar</Button>
        <Button variant={confirmVariant} onClick={onConfirm}>{confirmLabel}</Button>
      </div>
    </Modal>
  )
}
