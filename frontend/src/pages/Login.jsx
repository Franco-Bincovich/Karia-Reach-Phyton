import { useState } from 'react'
import { useAuth } from '../context/AuthContext'
import Button from '../components/UI/Button'
import './Login.css'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (!email.trim() || !password.trim()) {
      return setError('Completa email y contrasena')
    }
    setLoading(true)
    try {
      await login(email.trim(), password)
    } catch (err) {
      setError(err.response?.data?.message || 'Credenciales incorrectas')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-overlay">
      <form className="login-card" onSubmit={handleSubmit}>
        <div className="login-brand">
          <div className="login-logo">K</div>
          <h1>KarIA <span>Reach</span></h1>
          <p>Plataforma de outreach comercial con IA</p>
        </div>

        <div className="form-group">
          <label htmlFor="login-email">Email</label>
          <input
            id="login-email"
            type="email"
            placeholder="tu@email.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoFocus
          />
        </div>

        <div className="form-group">
          <label htmlFor="login-pass">Contrasena</label>
          <input
            id="login-pass"
            type="password"
            placeholder="Ingresa tu contrasena"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>

        {error && <p className="login-error">{error}</p>}

        <Button type="submit" variant="primary" size="lg" loading={loading}
          disabled={!email.trim() || !password.trim()}>
          Ingresar
        </Button>
      </form>
    </div>
  )
}
