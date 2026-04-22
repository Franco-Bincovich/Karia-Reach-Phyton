export default function ContactoFiltros({ filtros, onChange }) {
  return (
    <div className="form-row">
      <div className="form-group" style={{ flex: 2 }}>
        <input id="hist-filtro" placeholder="Buscar por nombre, empresa, cargo o email..."
          value={filtros.texto} onChange={(e) => onChange({ ...filtros, texto: e.target.value })} />
      </div>
      <div className="form-group" style={{ flex: 1 }}>
        <select id="hist-origen" value={filtros.origen} onChange={(e) => onChange({ ...filtros, origen: e.target.value })}>
          <option value="todos">Todos los origenes</option>
          <option value="ai">IA</option>
          <option value="apollo">Apollo</option>
          <option value="perplexity">Perplexity</option>
          <option value="apify">Apify</option>
          <option value="manual">Manual</option>
        </select>
      </div>
      <div className="form-group" style={{ flex: 1 }}>
        <input id="hist-rubro" placeholder="Filtrar por rubro/cargo..."
          value={filtros.rubro} onChange={(e) => onChange({ ...filtros, rubro: e.target.value })} />
      </div>
    </div>
  )
}
