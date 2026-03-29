import './LoadingSpinner.css'

export default function LoadingSpinner({ text = 'Cargando...' }) {
  return (
    <div className="loading-spinner" role="status" aria-label="Cargando...">
      <div className="spinner" />
      <span>{text}</span>
    </div>
  )
}
