import ExcelJS from 'exceljs'

export async function exportarContactosExcel(contactos) {
  const workbook = new ExcelJS.Workbook()
  const sheet = workbook.addWorksheet('Contactos')

  sheet.columns = [
    { header: 'Nombre', key: 'nombre', width: 25 },
    { header: 'Empresa', key: 'empresa', width: 25 },
    { header: 'Cargo', key: 'cargo', width: 25 },
    { header: 'Email Empresarial', key: 'email_empresarial', width: 30 },
    { header: 'Email Personal', key: 'email_personal', width: 30 },
    { header: 'Telefono Empresa', key: 'telefono_empresa', width: 20 },
    { header: 'Telefono Personal', key: 'telefono_personal', width: 20 },
    { header: 'Confianza (%)', key: 'confianza', width: 15 },
    { header: 'Origen', key: 'origen', width: 15 },
    { header: 'Fecha', key: 'fecha', width: 15 },
  ]

  for (const c of contactos) {
    sheet.addRow({
      nombre: c.nombre || '',
      empresa: c.empresa || '',
      cargo: c.cargo || '',
      email_empresarial: c.email_empresarial || '',
      email_personal: c.email_personal || '',
      telefono_empresa: c.telefono_empresa || '',
      telefono_personal: c.telefono_personal || '',
      confianza: c.confianza != null
        ? (c.confianza > 1 ? Math.round(c.confianza) : Math.round(c.confianza * 100))
        : '',
      origen: c.origen || '',
      fecha: c.created_at ? new Date(c.created_at).toLocaleDateString('es-AR') : '',
    })
  }

  const buffer = await workbook.xlsx.writeBuffer()
  const blob = new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  const fecha = new Date().toISOString().slice(0, 10)
  a.href = url
  a.download = `contactos-karia-${fecha}.xlsx`
  a.click()
  URL.revokeObjectURL(url)
}
