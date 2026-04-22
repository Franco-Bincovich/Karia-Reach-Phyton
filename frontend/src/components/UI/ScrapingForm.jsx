import { useState } from 'react'
import { useToast } from '../../context/ToastContext'
import Button from './Button'

export default function ScrapingForm({ onBuscar, loading }) {
  const toast = useToast()
  const [entradas, setEntradas] = useState('')

  const handleBuscar = () => {
    const lista = entradas.split('\n').map((l) => l.trim()).filter(Boolean)
    if (!lista.length) { toast.error('Ingresa al menos un sitio a scrapear'); return }
    onBuscar(lista)
  }

  return (
    <div>
      <div className="form-group">
        <label htmlFor="scraping-entradas">Sitios a scrapear</label>
        <textarea
          id="scraping-entradas"
          rows={5}
          value={entradas}
          onChange={(e) => setEntradas(e.target.value)}
          placeholder={'https://municipio.gob.ar\nMunicipio de Río Cuarto Córdoba\nhttps://hotelxyz.com'}
          style={{ width: '100%', resize: 'vertical', fontFamily: 'inherit', padding: '0.5rem', borderRadius: 6, border: '1px solid var(--border)' }}
        />
        <p className="text-sm text-secondary" style={{ marginTop: '0.35rem' }}>
          Podés pegar URLs directas o escribir el nombre del lugar — lo buscamos automáticamente
        </p>
      </div>
      <Button onClick={handleBuscar} disabled={loading}>Buscar</Button>
    </div>
  )
}
