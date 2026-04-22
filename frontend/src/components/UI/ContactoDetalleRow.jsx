import ConfidenceBadge from './ConfidenceBadge'

const ORIGEN_LABEL = { ai: 'IA', apollo: 'Apollo', apify: 'Apify', perplexity: 'Perplexity', claude: 'Claude', manual: 'Manual' }
const ORIGEN_COLOR = { ai: 'var(--primary)', apollo: 'var(--primary)', claude: 'var(--primary)' }

const OrigenBadge = ({ value }) => {
  const isAI = value === 'ai' || value === 'apollo' || value === 'claude'
  const bg = isAI ? 'var(--row-selected)' : '#F3F4F6'
  const color = ORIGEN_COLOR[value] || 'var(--text-secondary)'
  return <span className="origen-badge" style={{ background: bg, color }}>{ORIGEN_LABEL[value] || value || 'Manual'}</span>
}

const EnrichmentSourcesBadges = ({ sources }) => {
  if (!sources || !sources.length) return null
  return (
    <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 4 }}>
      {sources.map((s) => (
        <span key={s} style={{ fontSize: '0.65rem', fontWeight: 600, padding: '1px 5px', borderRadius: 8, background: '#EDE9FE', color: '#5B21B6' }}>
          ⚡{ORIGEN_LABEL[s] || s}
        </span>
      ))}
    </div>
  )
}

export default function ContactoDetalleRow({ contacto: c, expanded, checked, enriching, onCheck, onToggle, onEnrich, onDelete }) {
  return (
    <>
      <tr className={expanded ? 'row-expanded' : ''}>
        <td><span className="expand-icon" onClick={onToggle}>{expanded ? '▼' : '▶'}</span></td>
        <td><input type="checkbox" checked={checked} onChange={onCheck} /></td>
        <td>
          {c.nombre || '-'}
          <EnrichmentSourcesBadges sources={c.enrichment_sources} />
        </td>
        <td>{c.empresa || '-'}</td>
        <td className="email-cell">{c.email_personal || '-'}</td>
        <td><ConfidenceBadge value={c.confianza} /></td>
        <td><OrigenBadge value={c.origen} /></td>
        <td className="flex gap-sm" style={{ justifyContent: 'flex-end' }}>
          <button className="delete-btn" title="Enriquecer contacto" disabled={enriching} onClick={onEnrich}
            style={{ opacity: enriching ? 0.5 : 1 }}>{enriching ? '...' : '⚡'}</button>
          <button className="delete-btn" title="Eliminar" onClick={onDelete}>🗑</button>
        </td>
      </tr>
      {expanded && (
        <tr className="detail-row">
          <td colSpan={8}>
            <div className="detail-panel">
              <div className="detail-grid">
                <div><span className="detail-label">Email Empresarial</span>{c.email_empresarial || '-'}</div>
                <div><span className="detail-label">Cargo</span>{c.cargo || '-'}</div>
                <div><span className="detail-label">Rubro</span>{c.rubro || '-'}</div>
                <div><span className="detail-label">Tel. Empresa</span>{c.telefono_empresa || '-'}</div>
                <div><span className="detail-label">Tel. Personal</span>{c.telefono_personal || '-'}</div>
                <div><span className="detail-label">Fecha creacion</span>{c.created_at ? new Date(c.created_at).toLocaleDateString('es-AR') : '-'}</div>
                {c.linkedin_url && <div><span className="detail-label">LinkedIn</span><a href={c.linkedin_url} target="_blank" rel="noopener noreferrer">Ver perfil</a></div>}
                {c.instagram_username && <div><span className="detail-label">Instagram</span><a href={`https://instagram.com/${c.instagram_username}`} target="_blank" rel="noopener noreferrer">@{c.instagram_username}</a></div>}
                {c.facebook_url && <div><span className="detail-label">Facebook</span><a href={c.facebook_url} target="_blank" rel="noopener noreferrer">Ver página</a></div>}
                {c.whatsapp && <div><span className="detail-label">WhatsApp</span><a href={`https://wa.me/${c.whatsapp.replace(/\D/g, '')}`} target="_blank" rel="noopener noreferrer">{c.whatsapp}</a></div>}
                {c.twitter_url && <div><span className="detail-label">Twitter</span><a href={c.twitter_url} target="_blank" rel="noopener noreferrer">Ver perfil</a></div>}
                {c.tiktok_username && <div><span className="detail-label">TikTok</span><a href={`https://tiktok.com/@${c.tiktok_username}`} target="_blank" rel="noopener noreferrer">@{c.tiktok_username}</a></div>}
                {c.website && <div><span className="detail-label">Website</span><a href={c.website} target="_blank" rel="noopener noreferrer">{(() => { try { return new URL(c.website).hostname.replace(/^www\./, '') } catch { return c.website } })()}</a></div>}
                {c.direccion && <div><span className="detail-label">Dirección</span>{c.direccion}</div>}
                {(c.ciudad || c.pais) && <div><span className="detail-label">Ubicación</span>{[c.ciudad, c.pais].filter(Boolean).join(', ')}</div>}
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  )
}
