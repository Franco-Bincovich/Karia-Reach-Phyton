import { useState, useEffect } from 'react'
import api from '../hooks/useApi'
import { useToast } from '../context/ToastContext'
import { API_ADMIN_USUARIOS, API_ADMIN_USUARIO, API_ADMIN_USUARIO_METODOS } from '../constants/api'
import Button from '../components/UI/Button'
import Modal from '../components/UI/Modal'
import ConfirmModal from '../components/UI/ConfirmModal'
import LoadingSpinner from '../components/UI/LoadingSpinner'
import EditarUsuarioModal from '../components/UI/EditarUsuarioModal'

export default function Admin() {
  const toast = useToast()
  const [usuarios, setUsuarios] = useState([])
  const [loading, setLoading] = useState(true)
  const [detalle, setDetalle] = useState(null)
  const [editando, setEditando] = useState(null)
  const [editForm, setEditForm] = useState({ nombre: '', email: '', rol: '', metodos_habilitados: [] })
  const [deleteId, setDeleteId] = useState(null)
  const [nuevo, setNuevo] = useState(null)
  const crearUsuario = async () => {
    const payload = { ...nuevo }
    setNuevo(null)
    try {
      await api.post(API_ADMIN_USUARIOS, payload)
      toast.success('Usuario creado')
      cargar()
    } catch (e) {
      setNuevo(payload)
      e.response?.status===409 ? toast.error('El email ya está registrado') : toast.error(e.message)
    }
  }

  const cargar = () => api.get(API_ADMIN_USUARIOS)
    .then(({ data }) => setUsuarios(data.data || []))
    .catch((err) => toast.error(err.message))
    .finally(() => setLoading(false))
  useEffect(() => { cargar() }, [])

  const verDetalle = async (id) => {
    try {
      const { data } = await api.get(API_ADMIN_USUARIO(id))
      setDetalle(data.data)
    } catch (err) { toast.error(err.message) }
  }

  const abrirEditar = async (u) => {
    setEditando(u.id); setEditForm({ nombre: u.nombre || '', email: u.email || '', rol: u.rol || 'user', metodos_habilitados: [] })
    try { const { data } = await api.get(API_ADMIN_USUARIO_METODOS(u.id)); setEditForm(f => ({ ...f, metodos_habilitados: data.data?.metodos_habilitados || [] })) } catch (_) { /* usa defaults */ }
  }
  const guardarEdicion = async () => {
    try { await api.patch(API_ADMIN_USUARIO(editando), editForm); toast.success('Usuario actualizado'); setEditando(null); cargar() }
    catch (err) { toast.error(err.message) }
  }
  const eliminar = async () => {
    const id = deleteId; setDeleteId(null)
    try { await api.delete(API_ADMIN_USUARIO(id)); toast.success('Usuario eliminado'); cargar() }
    catch (err) { toast.error(err.message) }
  }

  if (loading) return <LoadingSpinner />

  return (
    <div>
      <div className="card">
        <div className="flex-between mb-md"><h3>Usuarios ({usuarios.length})</h3><Button size="sm" onClick={()=>setNuevo({nombre:'',email:'',password:'',rol:'user'})}>Nuevo usuario</Button></div>
        <div style={{ overflowX: 'auto' }}>
          <table className="historial-table">
            <thead>
              <tr>
                <th>Nombre</th><th>Email</th><th>Rol</th>
                <th>Contactos</th><th>Campanas</th><th>Emails</th><th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {usuarios.map((u) => (
                <tr key={u.id}>
                  <td>{u.nombre || '-'}</td>
                  <td>{u.email}</td>
                  <td><span className={`origen-badge`} style={{
                    background: u.rol === 'superadmin' ? 'var(--row-selected)' : '#F3F4F6',
                    color: u.rol === 'superadmin' ? 'var(--primary)' : 'var(--text-secondary)'
                  }}>{u.rol}</span></td>
                  <td>{u.total_contactos}</td>
                  <td>{u.total_campanas}</td>
                  <td>{u.total_emails_enviados}</td>
                  <td className="flex gap-sm">
                    <Button size="sm" variant="ghost" onClick={() => verDetalle(u.id)}>Ver</Button>
                    <Button size="sm" variant="ghost" onClick={() => abrirEditar(u)}>Editar</Button>
                    <Button size="sm" variant="danger" onClick={() => setDeleteId(u.id)}>Eliminar</Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {detalle && (
        <Modal title={`Detalle: ${detalle.nombre || detalle.email}`} onClose={() => setDetalle(null)}>
          <div className="detail-grid" style={{ marginBottom: '1rem' }}>
            <div><span className="detail-label">Email</span>{detalle.email}</div>
            <div><span className="detail-label">Rol</span>{detalle.rol}</div>
            <div><span className="detail-label">Creado</span>{detalle.created_at ? new Date(detalle.created_at).toLocaleDateString('es-AR') : '-'}</div>
            <div><span className="detail-label">Contactos</span>{detalle.total_contactos ?? '-'}</div>
            <div><span className="detail-label">Campanas</span>{detalle.total_campanas ?? '-'}</div>
            <div><span className="detail-label">Emails enviados</span>{detalle.total_emails_enviados ?? '-'}</div>
          </div>
          <h4>Integraciones</h4>
          <p className="text-sm mb-md">{(detalle.integraciones || []).length ? detalle.integraciones.join(', ') : 'Ninguna'}</p>
          <h4>Últimos contactos ({detalle.contactos?.length || 0})</h4>
          <div style={{ maxHeight: 180, overflow: 'auto', marginBottom: '1rem' }}>
            <table className="historial-table" style={{ fontSize: 'var(--font-sm)' }}>
              <thead><tr><th>Nombre</th><th>Empresa</th><th>Email</th><th>Origen</th></tr></thead>
              <tbody>
                {(detalle.contactos || []).slice(0, 10).map((c) => (
                  <tr key={c.id}><td>{c.nombre || '-'}</td><td>{c.empresa || '-'}</td><td>{c.email_empresarial || '-'}</td><td>{c.origen}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
          <h4>Últimas campanas ({detalle.campanas?.length || 0})</h4>
          <div style={{ maxHeight: 150, overflow: 'auto' }}>
            <table className="historial-table" style={{ fontSize: 'var(--font-sm)' }}>
              <thead><tr><th>Nombre</th><th>Estado</th><th>Enviados</th><th>Fecha</th></tr></thead>
              <tbody>
                {(detalle.campanas || []).slice(0, 5).map((c) => (
                  <tr key={c.id}><td>{c.nombre || '-'}</td><td>{c.status}</td><td>{c.sent_count ?? 0}</td>
                    <td>{c.created_at ? new Date(c.created_at).toLocaleDateString('es-AR') : '-'}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        </Modal>
      )}

      {editando && <EditarUsuarioModal form={editForm} onChange={setEditForm} onClose={() => setEditando(null)} onGuardar={guardarEdicion} />}

      {deleteId && (
        <ConfirmModal message="Se eliminará el usuario y TODOS sus datos (contactos, campañas, emails). Esta acción es irreversible."
          onConfirm={eliminar} onCancel={() => setDeleteId(null)} />
      )}
      {nuevo && <Modal title="Nuevo usuario" onClose={()=>setNuevo(null)}>
        {[['nombre','Nombre'],['email','Email'],['password','Contraseña']].map(([f,l])=><div className="form-group" key={f}><label>{l}</label><input type={f==='password'?'password':'text'} value={nuevo[f]} onChange={e=>setNuevo({...nuevo,[f]:e.target.value})}/></div>)}
        <div className="form-group"><label>Rol</label><select value={nuevo.rol} onChange={e=>setNuevo({...nuevo,rol:e.target.value})}><option value="user">Usuario</option><option value="superadmin">Superadmin</option></select></div><Button onClick={crearUsuario}>Crear</Button></Modal>}
    </div>
  )
}
