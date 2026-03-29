import axios from 'axios'

// Instancia de axios con baseURL vacia — Vite proxy redirige /api al backend
const api = axios.create({ baseURL: '' })

// Interceptor: agrega JWT desde sessionStorage en header Authorization
api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem('karia_token')
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`
  }
  return config
})

// Interceptor de respuesta: extrae mensaje de error del backend
api.interceptors.response.use(
  (res) => res,
  (err) => {
    // Si el token expiro, limpiar sesion para forzar re-login
    if (err.response?.status === 401) {
      sessionStorage.removeItem('karia_token')
      sessionStorage.removeItem('karia_user')
    }
    const msg = err.response?.data?.message || err.message || 'Error de conexion'
    return Promise.reject(new Error(msg))
  }
)

export default api
