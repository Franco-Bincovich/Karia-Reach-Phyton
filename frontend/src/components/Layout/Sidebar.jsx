import { NavLink, useLocation } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import './Sidebar.css'

const ICONS = {
  '/buscar': '\uD83D\uDD0D',
  '/componer': '\u270F\uFE0F',
  '/enviar': '\uD83D\uDCE8',
  '/historial': '\uD83D\uDCCB',
  '/bloques': '\uD83D\uDDC2\uFE0F',
  '/estadisticas': '\uD83D\uDCCA',
  '/respuestas': '\uD83D\uDCE9',
  '/configuracion': '\u2699\uFE0F',
}

export default function Sidebar({ routes }) {
  const { logout } = useAuth()
  const { pathname } = useLocation()

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="sidebar-logo">K</div>
        <div>
          <div className="sidebar-title">KarIA</div>
          <div className="sidebar-subtitle">Reach</div>
        </div>
      </div>

      <nav className="sidebar-nav">
        {routes.map((r) => (
          <NavLink
            key={r.path}
            to={r.path}
            className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
            aria-current={pathname.startsWith(r.path) ? 'page' : undefined}
          >
            <span className="sidebar-icon">{ICONS[r.path]}</span>
            {r.label}
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <button className="sidebar-logout" onClick={logout}>Cerrar sesion</button>
      </div>
    </aside>
  )
}
