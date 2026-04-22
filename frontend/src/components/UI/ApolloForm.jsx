import { useState } from 'react'
import Button from './Button'

const TAMANO_OPCIONES = [
  { value: '', label: 'Cualquier tamaño' },
  { value: 'micro', label: 'Micro (1-10)' },
  { value: 'pequena', label: 'Pequeña (11-50)' },
  { value: 'mediana', label: 'Mediana (51-500)' },
  { value: 'grande', label: 'Grande (501-5000)' },
  { value: 'enterprise', label: 'Enterprise (5000+)' },
]

export default function ApolloForm({ onBuscar, loading }) {
  const [cargo, setCargo] = useState('')
  const [tamano, setTamano] = useState('')
  const [soloVerificado, setSoloVerificado] = useState(false)

  const handleBuscar = () => {
    const params = {}
    if (cargo.trim()) params.cargo = cargo.trim()
    if (tamano) params.tamano_empresa = tamano
    if (soloVerificado) params.solo_email_verificado = true
    onBuscar(params)
  }

  return (
    <>
      <div className="form-row">
        <div className="form-group">
          <label htmlFor="apollo-cargo">Cargo específico</label>
          <input id="apollo-cargo" value={cargo} onChange={(e) => setCargo(e.target.value)} placeholder="Ej: CEO, Director Comercial" />
        </div>
        <div className="form-group">
          <label htmlFor="apollo-tamano">Tamaño de empresa</label>
          <select id="apollo-tamano" value={tamano} onChange={(e) => setTamano(e.target.value)}>
            {TAMANO_OPCIONES.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>
        <div className="form-group" style={{ justifyContent: 'flex-end', paddingTop: '1.6rem' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
            <input type="checkbox" checked={soloVerificado} onChange={(e) => setSoloVerificado(e.target.checked)} />
            Solo email verificado
          </label>
        </div>
      </div>
      <div className="flex gap-sm" style={{ marginTop: '0.5rem' }}>
        <Button onClick={handleBuscar} disabled={loading}>Buscar</Button>
      </div>
    </>
  )
}
