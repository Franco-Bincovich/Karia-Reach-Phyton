import { useLocation } from 'react-router-dom'
import './Header.css'

export default function Header({ routes }) {
  const { pathname } = useLocation()
  const current = routes.find((r) => pathname.startsWith(r.path))

  return (
    <header className="header">
      <h1 className="header-title">{current?.label || 'KarIA Reach'}</h1>
    </header>
  )
}
