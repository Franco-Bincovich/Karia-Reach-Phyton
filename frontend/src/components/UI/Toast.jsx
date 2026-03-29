import './Toast.css'

const ICONS = { success: '\u2713', error: '\u2717', info: '\u2139' }

export default function Toast({ message, type = 'info' }) {
  return (
    <div className={`toast toast-${type}`}>
      <span className="toast-icon">{ICONS[type]}</span>
      <span>{message}</span>
    </div>
  )
}
