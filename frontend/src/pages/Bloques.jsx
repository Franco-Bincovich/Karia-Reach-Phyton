import { useState, useEffect } from 'react'
import api from '../hooks/useApi'
import { useToast } from '../context/ToastContext'
import { API_BLOQUES, API_BLOQUE_DELETE, API_BLOQUE_CONTACTOS, API_BLOQUE_REMOVE_CONTACT, API_CONTACTS } from '../constants/api'
import Button from '../components/UI/Button'
import LoadingSpinner from '../components/UI/LoadingSpinner'
import ConfirmModal from '../components/UI/ConfirmModal'
import Modal from '../components/UI/Modal'

export default function Bloques() {
  const toast = useToast()
  const [bloques, setBloques] = useState([])
  const [expandedId, setExpandedId] = useState(null)
  const [contactos, setContactos] = useState([])
  const [deleteId, setDeleteId] = useState(null)
  const [editId, setEditId] = useState(null)
  const [editNombre, setEditNombre] = useState('')
  const [showAgregar, setShowAgregar] = useState(null)
  const [todosContactos, setTodosContactos] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => { cargarBloques() }, [])

  const cargarBloques = async () => {
    try {
      const { data } = await api.get(API_BLOQUES)
      setBloques(data.data || [])
    } catch (err) { toast.error(err.message) }
    finally { setLoading(false) }
  }

  const expandir = async (id) => {
    if (expandedId === id) { setExpandedId(null); return }
    setExpandedId(id)
    try {
      const { data } = await api.get(API_BLOQUE_CONTACTOS(id))
      setContactos(data.data || [])
    } catch (err) { toast.error(err.message) }
  }

  const eliminarBloque = async () => {
    const id = deleteId; setDeleteId(null)
    try {
      await api.delete(API_BLOQUE_DELETE(id))
      toast.success('Bloque eliminado')
      setBloques((prev) => prev.filter((b) => b.id !== id))
      if (expandedId === id) setExpandedId(null)
    } catch (err) { toast.error(err.message) }
  }

  const guardarEdicion = async (id) => {
    if (!editNombre.trim()) return toast.error('El nombre no puede estar vacío')
    try {
      await api.put(API_BLOQUE_DELETE(id), { nombre: editNombre.trim() })
      setBloques((prev) => prev.map((b) => b.id === id ? { ...b, nombre: editNombre.trim() } : b))
      setEditId(null); toast.success('Nombre actualizado')
    } catch (err) { toast.error(err.message) }
  }

  const quitarContacto = async (bloqueId, contactoId) => {
    try {
      await api.delete(API_BLOQUE_REMOVE_CONTACT(bloqueId, contactoId))
      setContactos((prev) => prev.filter((c) => c.id !== contactoId))
      setBloques((prev) => prev.map((b) => b.id === bloqueId ? { ...b, cantidad_contactos: (b.cantidad_contactos || 1) - 1 } : b))
      toast.success('Contacto quitado del bloque')
    } catch (err) { toast.error(err.message) }
  }

  const abrirAgregar = async (bloqueId) => {
    setShowAgregar(bloqueId)
    try {
      const { data } = await api.get(API_CONTACTS)
      setTodosContactos((data.data || []).map((c) => ({ ...c, _selected: false })))
    } catch (err) { toast.error(err.message) }
  }

  const agregarSeleccion = async () => {
    const ids = todosContactos.filter((c) => c._selected).map((c) => c.id)
    if (!ids.length) return toast.error('Selecciona al menos un contacto')
    try {
      await api.post(API_BLOQUE_CONTACTOS(showAgregar), { contacto_ids: ids })
      toast.success(`${ids.length} contactos agregados`)
      setShowAgregar(null)
      await expandir(showAgregar)
      cargarBloques()
    } catch (err) { toast.error(err.message) }
  }

  if (loading) return <LoadingSpinner />

  return (
    <div>
      {!bloques.length && <div className="card"><p className="text-sm text-secondary">No hay bloques creados.</p></div>}
      {bloques.map((b) => (
        <div key={b.id} className="card mb-md">
          <div className="flex-between mb-md">
            {editId === b.id ? (
              <div className="flex gap-sm" style={{ flex: 1 }}>
                <input value={editNombre} onChange={(e) => setEditNombre(e.target.value)} style={{ flex: 1 }} />
                <Button size="sm" onClick={() => guardarEdicion(b.id)}>Guardar</Button>
                <Button size="sm" variant="ghost" onClick={() => setEditId(null)}>Cancelar</Button>
              </div>
            ) : (
              <>
                <strong style={{ cursor: 'pointer' }} onClick={() => expandir(b.id)}>
                  {expandedId === b.id ? '\u25BC' : '\u25B6'} {b.nombre} ({b.cantidad_contactos} contactos)
                </strong>
                <div className="flex gap-sm">
                  <Button size="sm" variant="ghost" onClick={() => { setEditId(b.id); setEditNombre(b.nombre) }}>Editar</Button>
                  <Button size="sm" variant="ghost" onClick={() => setDeleteId(b.id)}>Eliminar</Button>
                </div>
              </>
            )}
          </div>
          {expandedId === b.id && (
            <>
              <table className="historial-table" style={{ width: '100%' }}>
                <thead>
                  <tr><th>Nombre</th><th>Empresa</th><th>Cargo</th><th>Email Corp.</th><th style={{ width: 80 }}></th></tr>
                </thead>
                <tbody>
                  {contactos.map((c) => (
                    <tr key={c.id}>
                      <td>{c.nombre || '-'}</td><td>{c.empresa || '-'}</td><td>{c.cargo || '-'}</td>
                      <td>{c.email_empresarial || '-'}</td>
                      <td><Button size="sm" variant="ghost" onClick={() => quitarContacto(b.id, c.id)}>Quitar</Button></td>
                    </tr>
                  ))}
                  {!contactos.length && <tr><td colSpan={5} style={{ textAlign: 'center', padding: '1rem' }}>Sin contactos</td></tr>}
                </tbody>
              </table>
              <div style={{ marginTop: '0.5rem' }}>
                <Button size="sm" variant="ghost" onClick={() => abrirAgregar(b.id)}>+ Agregar contactos</Button>
              </div>
            </>
          )}
        </div>
      ))}

      {deleteId && <ConfirmModal message="Este bloque sera eliminado permanentemente." onConfirm={eliminarBloque} onCancel={() => setDeleteId(null)} />}

      {showAgregar && (
        <Modal title="Agregar contactos al bloque" onClose={() => setShowAgregar(null)}>
          <div style={{ maxHeight: 300, overflow: 'auto' }}>
            <table style={{ width: '100%', fontSize: '0.85rem' }}>
              <thead><tr><th></th><th>Nombre</th><th>Empresa</th><th>Email</th></tr></thead>
              <tbody>
                {todosContactos.map((c, i) => (
                  <tr key={c.id} style={{ cursor: 'pointer' }} onClick={() => setTodosContactos((prev) => prev.map((x, j) => j === i ? { ...x, _selected: !x._selected } : x))}>
                    <td><input type="checkbox" checked={c._selected} readOnly /></td>
                    <td>{c.nombre || '-'}</td><td>{c.empresa || '-'}</td><td>{c.email_empresarial || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div style={{ marginTop: '0.5rem' }}>
            <Button onClick={agregarSeleccion}>Agregar {todosContactos.filter((c) => c._selected).length} contactos</Button>
          </div>
        </Modal>
      )}
    </div>
  )
}
