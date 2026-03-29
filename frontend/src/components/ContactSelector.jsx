import ConfidenceBadge from './UI/ConfidenceBadge'
import './ContactSelector.css'

/**
 * Tabla ejecutiva para seleccionar contactos con checkboxes.
 * Reutilizada en EnviarCampana y ComponerEmails.
 */
export default function ContactSelector({ contactos, onChange }) {
  const toggle = (i) => {
    onChange(contactos.map((x, j) => j === i ? { ...x, _selected: !x._selected } : x))
  }

  const selCount = contactos.filter((c) => c._selected).length

  return (
    <div>
      <div className="cs-wrap">
        <table className="cs-table">
          <thead>
            <tr>
              <th style={{ width: 40 }}></th>
              <th>Nombre</th>
              <th>Empresa</th>
              <th style={{ width: 90 }}>Confianza</th>
            </tr>
          </thead>
          <tbody>
            {contactos.map((c, i) => (
              <tr key={c.id || i} className={c._selected ? 'selected' : ''} onClick={() => toggle(i)}>
                <td><input type="checkbox" checked={c._selected || false} readOnly /></td>
                <td>{c.nombre || '-'}</td>
                <td>{c.empresa || '-'}</td>
                <td><ConfidenceBadge value={c.confianza} /></td>
              </tr>
            ))}
            {!contactos.length && <tr><td colSpan={4} className="cs-empty">No hay contactos</td></tr>}
          </tbody>
        </table>
      </div>
      <div className="cs-footer">{selCount} seleccionado{selCount !== 1 ? 's' : ''}</div>
    </div>
  )
}
