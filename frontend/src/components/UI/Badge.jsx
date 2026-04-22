import './Badge.css'

const VARIANTS = {
  ai: { bg: '#DBEAFE', color: '#1D4ED8', label: 'IA' },
  manual: { bg: '#DCFCE7', color: '#15803D', label: 'Manual' },
  apollo: { bg: '#FEF9C3', color: '#A16207', label: 'Apollo' },
  alta: { bg: '#DCFCE7', color: '#15803D' },
  media: { bg: '#FEF9C3', color: '#A16207' },
  baja: { bg: '#FEE2E2', color: '#B91C1C' },
  success: { bg: '#DCFCE7', color: '#15803D' },
  error: { bg: '#FEE2E2', color: '#B91C1C' },
  info: { bg: '#DBEAFE', color: '#1D4ED8' },
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
