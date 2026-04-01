import { NavLink, useLocation } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import './Sidebar.css'

const ICONS = {
  '/buscar': '\uD83D\uDD0D',
  '/componer': '\u270F\uFE0F',
  '/enviar': '\uD83D\uDCE8',
  '/historial': '\uD83D\uDCCB',
  '/programadas': '\uD83D\uDCC5',
  '/bloques': '\uD83D\uDDC2\uFE0F',
  '/estadisticas': '\uD83D\uDCCA',
  '/respuestas': '\uD83D\uDCE9',
  '/configuracion': '\u2699\uFE0F',
  '/admin': '\uD83D\uDEE1\uFE0F',
}

export default function Sidebar({ routes, collapsed, onToggle }) {
  const { logout } = useAuth()
  const { pathname } = useLocation()

  return (
    <aside className={`sidebar ${collapsed ? 'sidebar-collapsed' : ''}`}>
      <div className="sidebar-brand">
        <div className="sidebar-logo">K</div>
        {!collapsed && (
          <div>
            <div className="sidebar-title">KarIA</div>
            <div className="sidebar-subtitle">Reach</div>
          </div>
        )}
      </div>

      <button className="sidebar-toggle" onClick={onToggle}
        aria-label={collapsed ? 'Expandir sidebar' : 'Colapsar sidebar'}>
        {collapsed ? '\u25B6' : '\u25C0'}
      </button>

      <nav className="sidebar-nav">
        {routes.map((r) => (
          <NavLink
            key={r.path}
            to={r.path}
            className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
            aria-current={pathname.startsWith(r.path) ? 'page' : undefined}
            title={collapsed ? r.label : undefined}
          >
            <span className="sidebar-icon">{ICONS[r.path]}</span>
            {!collapsed && <span className="sidebar-label">{r.label}</span>}
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <button className="sidebar-logout" onClick={logout}>
          {collapsed ? '\uD83D\uDEAA' : 'Cerrar sesion'}
        </button>
      </div>
    </aside>
  )
}
