import * as XLSX from 'xlsx'

/**
 * Exporta un array de contactos a un archivo Excel (.xlsx).
 * Columnas: Nombre, Empresa, Cargo, Email Empresarial, Email Personal,
 * Telefono Empresa, Telefono Personal, Confianza (%), Origen, Fecha.
 */
export function exportarContactosExcel(contactos) {
  const rows = contactos.map((c) => ({
    Nombre: c.nombre || '',
    Empresa: c.empresa || '',
    Cargo: c.cargo || '',
    'Email Empresarial': c.email_empresarial || '',
    'Email Personal': c.email_personal || '',
    'Telefono Empresa': c.telefono_empresa || '',
    'Telefono Personal': c.telefono_personal || '',
    'Confianza (%)': c.confianza != null
      ? (c.confianza > 1 ? Math.round(c.confianza) : Math.round(c.confianza * 100))
      : '',
    Origen: c.origen || '',
    Fecha: c.created_at ? new Date(c.created_at).toLocaleDateString('es-AR') : '',
  }))

  const ws = XLSX.utils.json_to_sheet(rows)
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, 'Contactos')

  const fecha = new Date().toISOString().slice(0, 10)
  XLSX.writeFile(wb, `contactos-karia-${fecha}.xlsx`)
}
