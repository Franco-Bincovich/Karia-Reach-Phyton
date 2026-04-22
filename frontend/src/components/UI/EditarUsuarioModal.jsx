import Button from './Button'
import Modal from './Modal'

const METODOS = [
  { value: 'claude_ai', label: 'IA (Claude)' },
  { value: 'apollo', label: 'Apollo.io' },
  { value: 'perplexity', label: 'Perplexity' },
  { value: 'apify', label: 'Apify' },
  { value: 'scraping_web', label: 'Scraping Web' },
  { value: 'carga_manual', label: 'Carga Manual' },
]

export default function EditarUsuarioModal({ form, onChange, onClose, onGuardar }) {
  const metodos = form.metodos_habilitados || []
  const toggleMetodo = (val) => onChange({
    ...form,
    metodos_habilitados: metodos.includes(val) ? metodos.filter(m => m !== val) : [...metodos, val],
  })

  return (
    <Modal title="Editar usuario" onClose={onClose}>
      {['nombre', 'email'].map((f) => (
        <div className="form-group" key={f}>
          <label>{f}</label>
          <input value={form[f]} onChange={(e) => onChange({ ...form, [f]: e.target.value })} />
        </div>
      ))}
      <div className="form-group">
        <label>Rol</label>
        <select value={form.rol} onChange={(e) => onChange({ ...form, rol: e.target.value })}>
          <option value="user">user</option>
          <option value="superadmin">superadmin</option>
        </select>
      </div>
      <div className="form-group">
        <label>Métodos de búsqueda habilitados</label>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.4rem', marginTop: '0.3rem' }}>
          {METODOS.map(({ value, label }) => (
            <label key={value} style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer', fontSize: 'var(--font-sm)' }}>
              <input type="checkbox" checked={metodos.includes(value)} onChange={() => toggleMetodo(value)} />
              {label}
            </label>
          ))}
        </div>
      </div>
      <Button onClick={onGuardar}>Guardar</Button>
    </Modal>
  )
}
