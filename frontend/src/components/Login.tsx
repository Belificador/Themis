import { useState, useRef, useEffect, useCallback } from 'react'
import { api } from '../api'
import { Icon } from '../icons'
import logoMark from '../assets/logo-mark.png'

export function Login({ onLogin }: { onLogin: () => void }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [theme, setTheme] = useState<'light' | 'dark'>(
    () => (localStorage.getItem('themis-theme') === 'dark' ? 'dark' : 'light')
  )
  const [intro, setIntro] = useState<'idle' | 'playing' | 'skipped' | 'done'>(
    'idle'
  )
  const cardRef = useRef<HTMLDivElement>(null)
  const videoRef = useRef<HTMLVideoElement>(null)
  const introOverlayRef = useRef<HTMLDivElement>(null)

  // Aplicar tema al montar y al cambiar
  useEffect(() => {
    document.documentElement.dataset.theme = theme
    localStorage.setItem('themis-theme', theme)
  }, [theme])

  // Animación de entrada de la tarjeta
  useEffect(() => {
    cardRef.current?.classList.add('login-entered')
  }, [])

  // Iniciar intro automáticamente al montar
  useEffect(() => {
    setIntro('playing')
  }, [])

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'light' ? 'dark' : 'light'))
  }

  const skipIntro = () => {
    setIntro('skipped')
    if (videoRef.current) {
      videoRef.current.pause()
      videoRef.current.src = ''
      videoRef.current.load()
    }
  }

  const handleIntroEnd = () => {
    setIntro('done')
  }

  const shakeCard = useCallback(() => {
    if (!cardRef.current) return
    cardRef.current.classList.remove('login-shake')
    void cardRef.current.offsetWidth
    cardRef.current.classList.add('login-shake')
  }, [])

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

  // Video URL según el tema actual
  const introVideoUrl =
    theme === 'dark' ? '/intro-fondo-oscuro.mp4' : '/intro-fondo-blanco.mp4'

  // Si la intro está saltada o terminada, no renderizar overlay
  if (intro === 'skipped' || intro === 'done') {
    return renderLoginForm()
  }

  return (
    <>
      {/* Overlay de intro a pantalla completa */}
      <div
        ref={introOverlayRef}
        className="intro-overlay"
        onClick={skipIntro}
      >
        <video
          ref={videoRef}
          className="intro-video"
          autoPlay
          muted
          playsInline
          preload="auto"
          onEnded={handleIntroEnd}
          onError={handleIntroEnd}
        >
          <source src={introVideoUrl} type="video/mp4" />
          Tu navegador no soporta video.
        </video>
        <div className="intro-hint">Haz clic para saltar</div>
        <div className="intro-spinner" />
      </div>

      {/* Login form oculto durante la intro, se muestra cuando termina */}
      {intro === 'playing' && (
        <div className="login-hidden" />
      )}
    </>
  )

  function renderLoginForm() {
    return (
      <div className="login-page">
        {/* Animación de fondo: orugas flotantes + gradiente animado */}
        <div className="login-bg" />
        <div className="login-orb login-orb-1" />
        <div className="login-orb login-orb-2" />
        <div className="login-orb login-orb-3" />

        <div className="login-center">
          <div className="login-card" ref={cardRef}>
            <div className="login-header">
              {/* Selector de tema */}
              <div className="theme-toggle-row">
                <button
                  type="button"
                  className="theme-btn"
                  onClick={toggleTheme}
                  aria-label={
                    theme === 'light'
                      ? 'Cambiar a tema oscuro'
                      : 'Cambiar a tema claro'
                  }
                >
                  <Icon
                    name={theme === 'light' ? 'moon' : 'sun'}
                    size={18}
                  />
                  <span className="theme-label">
                    {theme === 'light' ? 'Oscuro' : 'Claro'}
                  </span>
                </button>
              </div>

              <div className="login-logo">
                <img src={logoMark} alt="Themis" />
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
                    aria-label={
                      showPassword
                        ? 'Ocultar contraseña'
                        : 'Mostrar contraseña'
                    }
                  >
                    <Icon
                      name={showPassword ? 'eye-off' : 'eye'}
                      size={16}
                    />
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
}
