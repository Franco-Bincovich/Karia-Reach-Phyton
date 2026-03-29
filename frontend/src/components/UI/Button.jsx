import './Button.css'

export default function Button({ children, variant = 'primary', size = 'md', loading, disabled, ...props }) {
  return (
    <button
      className={`btn btn-${variant} btn-${size}`}
      disabled={disabled || loading}
      {...props}
    >
      {loading && <span className="btn-spinner" />}
      {children}
    </button>
  )
}
