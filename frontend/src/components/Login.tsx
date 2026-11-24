import { useState, useRef, useEffect } from 'react'
import { api } from '../api'
import { Icon } from '../icons'

export function Login({ onLogin }: { onLogin: () => void }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const cardRef = useRef<HTMLDivElement>(null)

  // Animación de entrada de la tarjeta (se dispara en el montaje)
  useEffect(() => {
    cardRef.current?.classList.add('login-entered')
  }, [])

  const shakeCard = () => {
    if (!cardRef.current) return
    cardRef.current.classList.remove('login-shake')
    // forzar reflow para reiniciar la animación
    void cardRef.current.offsetWidth
    cardRef.current.classList.add('login-shake')
  }

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    setError(null)

    if (!username.trim() || !password) {
      setError('Ingresa usuario y contraseña.')
      shakeCard()
      return
    }

    setBusy(true)
    try {
      const data = await api.login({ username: username.trim(), password })
      localStorage.setItem('themis-token', data.access_token)
      onLogin()
    } catch (err) {
      setError('Usuario o contraseña incorrectos.')
      shakeCard()
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="login-page">
      {/* Halo radial sutil detrás de la tarjeta */}
      <div className="login-halo" />

      <div className="login-center">
        <div className="login-card" ref={cardRef}>
          <div className="login-header">
            <div className="login-logo">
              <img src="/assets/logo-mark.png" alt="Themis" />
            </div>
            <h2>Iniciar sesión</h2>
            <p>Acceso al sistema de inventario y ventas.</p>
          </div>

          <form className="login-form" onSubmit={submit}>
            <div className="field">
              <span>Usuario o correo electrónico</span>
              <div className="input-wrap">
                <Icon name="user" size={16} className="input-icon" />
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="Playcell"
                  autoComplete="username"
                  autoFocus
                />
              </div>
            </div>

            <div className="field">
              <span>Contraseña</span>
              <div className="input-wrap">
                <Icon name="key" size={16} className="input-icon" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  className="toggle-password"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                >
                  <Icon name={showPassword ? 'eye-off' : 'eye'} size={16} />
                </button>
              </div>
            </div>

            {error && (
              <div className="field-error" role="alert">
                <Icon name="alert" size={14} />
                <span>{error}</span>
              </div>
            )}

            <div className="options-bar">
              <label className="remember">
                <input type="checkbox" defaultChecked />
                <span>Recordarme</span>
              </label>
              <a href="#" className="forgot-link">
                ¿Olvidaste tu contraseña?
              </a>
            </div>

            <button
              type="submit"
              className="btn btn-primary btn-login"
              disabled={busy}
            >
              {busy ? (
                <span className="btn-loader">
                  <span className="spin" />
                  Ingresando…
                </span>
              ) : (
                <span>Ingresar</span>
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
