import './Badge.css'

const VARIANTS = {
  ai: { bg: '#E0F2FE', color: '#0369A1', label: 'IA' },
  manual: { bg: '#F0FDF4', color: '#166534', label: 'Manual' },
  apollo: { bg: '#FEF3C7', color: '#92400E', label: 'Apollo' },
  alta: { bg: '#D1FAE5', color: '#065F46' },
  media: { bg: '#FEF3C7', color: '#92400E' },
  baja: { bg: '#FEE2E2', color: '#991B1B' },
  success: { bg: '#D1FAE5', color: '#065F46' },
  error: { bg: '#FEE2E2', color: '#991B1B' },
  info: { bg: '#DBEAFE', color: '#1E40AF' },
}

export default function Badge({ variant = 'info', children }) {
  const style = VARIANTS[variant] || VARIANTS.info
  // children tiene prioridad sobre el label predefinido del variant
  return (
    <span className="badge" style={{ background: style.bg, color: style.color }}>
      {children || style.label || variant}
    </span>
  )
}
