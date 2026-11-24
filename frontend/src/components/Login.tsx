import { useState } from 'react'
import { api } from '../api'
import { Icon } from '../icons'

export function Login({ onLogin }: { onLogin: () => void }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    setError(null)
    setBusy(true)
    try {
      const data = await api.login({ username, password })
      localStorage.setItem('themis-token', data.access_token)
      onLogin()
    } catch (err) {
      setError('Usuario o contraseña incorrectos.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-lockup">
          <span className="brand-emblem-wrap">
            <img src="/assets/logo-mark.png" alt="" className="brand-emblem" />
          </span>
          <span className="brand-copy">
            <strong>Themis</strong>
            <span>Inventario & ventas</span>
          </span>
        </div>
        <div className="sidebar-card">
          <Icon name="alert" />
          <div>
            <strong>Acceso restringido</strong>
            <p>Inicia sesión para continuar.</p>
          </div>
        </div>
      </aside>

      <div className="main-area">
        <div className="login-card">
          <div className="login-header">
            <Icon name="receipt" size={40} />
            <h2>Iniciar sesión</h2>
            <p>Acceso al sistema de inventario y ventas.</p>
          </div>
          <form className="login-form" onSubmit={submit}>
            {error && (
              <div className="alert alert-error">
                <Icon name="alert" />
                <span>{error}</span>
              </div>
            )}
            <label className="field">
              <span>Usuario</span>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Playcell"
                autoFocus
              />
            </label>
            <label className="field">
              <span>Contraseña</span>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
              />
            </label>
            <button type="submit" className="btn btn-primary" disabled={busy}>
              {busy ? 'Ingresando…' : 'Ingresar'}
            </button>
          </form>
          <p className="login-hint">
            Usuario: <strong>Playcell</strong> · Contraseña: <strong>playcellalex</strong>
          </p>
        </div>
      </div>
    </div>
  )
}
