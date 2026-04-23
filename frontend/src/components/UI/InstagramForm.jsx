import { useState } from 'react'
import { useToast } from '../../context/ToastContext'
import Button from './Button'

export default function InstagramForm({ onBuscar, loading }) {
  const toast = useToast()
  const [handles, setHandles] = useState('')
  const [maxPorPerfil, setMaxPorPerfil] = useState(500)

  const handleBuscar = () => {
    const lista = handles.split('\n').map((l) => l.trim().replace(/^@/, '')).filter(Boolean)
    if (!lista.length) { toast.error('Ingresá al menos un perfil de Instagram'); return }
    if (lista.length > 8) { toast.error('Máximo 8 perfiles permitidos'); return }
    onBuscar({ handles: lista, max_por_perfil: maxPorPerfil })
  }

  return (
    <div>
      <div className="form-group">
        <label htmlFor="ig-handles">Perfiles de competencia</label>
        <textarea
          id="ig-handles"
          rows={5}
          value={handles}
          onChange={(e) => setHandles(e.target.value)}
          placeholder={'restaurantebuenosaires\ncafeteriapalermo\ntiendaropa_ba'}
          style={{ width: '100%', resize: 'vertical', fontFamily: 'inherit', padding: '0.5rem', borderRadius: 6, border: '1px solid var(--border)' }}
        />
        <p className="text-sm text-secondary" style={{ marginTop: '0.35rem' }}>
          Ingresá hasta 8 perfiles de competencia, uno por línea (sin @)
        </p>
      </div>
      <div className="form-group">
        <label htmlFor="ig-max">Contactos por perfil</label>
        <input
          id="ig-max"
          type="number"
          min={10}
          max={2000}
          value={maxPorPerfil}
          onChange={(e) => setMaxPorPerfil(Math.min(2000, Math.max(10, +e.target.value || 500)))}
        />
      </div>
      <Button onClick={handleBuscar} disabled={loading}>Buscar</Button>
    </div>
  )
}
