/**
 * Badge de confianza con guard para valores legacy (enteros >1) y float 0-1.
 * Verde >80%, amarillo 60-80%, rojo <60%.
 */
export default function ConfidenceBadge({ value }) {
  if (value == null) return <span style={{ color: 'var(--gray)' }}>-</span>
  const pct = value > 1 ? Math.round(value) : Math.round(value * 100)
  const color = pct >= 80 ? '#22C55E' : pct >= 60 ? '#EAB308' : '#EF4444'
  const bg = pct >= 80 ? '#F0FDF4' : pct >= 60 ? '#FEFCE8' : '#FEF2F2'
  return (
    <span style={{ background: bg, color, padding: '2px 10px', borderRadius: 12, fontSize: '0.8rem', fontWeight: 600 }}>
      {pct}%
    </span>
  )
}
