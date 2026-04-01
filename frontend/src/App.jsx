import { useState } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import Sidebar from './components/Layout/Sidebar'
import Header from './components/Layout/Header'
import Login from './pages/Login'
import BuscarContactos from './pages/BuscarContactos'
import ComponerEmails from './pages/ComponerEmails'
import EnviarCampana from './pages/EnviarCampana'
import Historial from './pages/Historial'
import Bloques from './pages/Bloques'
import Estadisticas from './pages/Estadisticas'
import Respuestas from './pages/Respuestas'
import Configuracion from './pages/Configuracion'
import CampanasProgramadas from './pages/CampanasProgramadas'
import Admin from './pages/Admin'

const BASE_ROUTES = [
  { path: '/buscar', label: 'Buscar Contactos', element: <BuscarContactos /> },
  { path: '/componer', label: 'Componer Emails', element: <ComponerEmails /> },
  { path: '/enviar', label: 'Enviar Campana', element: <EnviarCampana /> },
  { path: '/programadas', label: 'Campanas Programadas', element: <CampanasProgramadas /> },
  { path: '/historial', label: 'Historial', element: <Historial /> },
  { path: '/bloques', label: 'Bloques', element: <Bloques /> },
  { path: '/estadisticas', label: 'Estadisticas', element: <Estadisticas /> },
  { path: '/respuestas', label: 'Respuestas', element: <Respuestas /> },
  { path: '/configuracion', label: 'Configuracion', element: <Configuracion /> },
]

const ADMIN_ROUTE = { path: '/admin', label: 'Admin', element: <Admin /> }

export default function App() {
  const { isAuthenticated, user } = useAuth()
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

  if (!isAuthenticated) return <Login />

  const ROUTES = user?.rol === 'superadmin' ? [...BASE_ROUTES, ADMIN_ROUTE] : BASE_ROUTES

  return (
    <div className={`app-layout ${sidebarCollapsed ? 'sidebar-is-collapsed' : ''}`}>
      <Sidebar routes={ROUTES} collapsed={sidebarCollapsed} onToggle={() => setSidebarCollapsed(!sidebarCollapsed)} />
      <div className="app-content">
        <Header routes={ROUTES} />
        <main className="page">
          <Routes>
            {ROUTES.map((r) => <Route key={r.path} path={r.path} element={r.element} />)}
            <Route path="*" element={<Navigate to="/buscar" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}
