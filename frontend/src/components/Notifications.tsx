import { useEffect, useState } from 'react'
import { api } from '../api'
import type {
  NotificationLog,
  NotificationStats,
  TestResult,
} from '../types'

function formatDate(value: string | null): string {
  if (!value) return '—'
  return new Date(value).toLocaleString('es-ES')
}

function statusClass(status: string): string {
  if (status === 'sent') return 'badge badge-ok'
  if (status === 'dry_run') return 'badge badge-sync'
  if (status === 'failed') return 'badge badge-danger'
  return 'badge badge-muted'
}

export function Notifications() {
  const [logs, setLogs] = useState<NotificationLog[]>([])
  const [stats, setStats] = useState<NotificationStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [test, setTest] = useState<TestResult | null>(null)
  const [testing, setTesting] = useState(false)

  const load = () => {
    setLoading(true)
    Promise.all([api.notifications(), api.notificationStats()])
      .then(([logData, statsData]) => {
        setLogs(logData)
        setStats(statsData)
        setError(null)
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [])

  const sendTest = async () => {
    setTesting(true)
    setError(null)
    try {
      setTest(await api.testAlert())
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setTesting(false)
    }
  }

  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <h2>Notificaciones</h2>
          <p className="muted">
            Eventos <span className="mono">stock.*</span> consumidos con
            idempotencia, deduplicación y reintentos.
          </p>
        </div>
        <div className="kpis">
          <div className="kpi">
            <span className="kpi-value">{stats?.processed_events ?? '—'}</span>
            <span className="kpi-label">Eventos procesados</span>
          </div>
          <div className="kpi kpi-warn">
            <span className="kpi-value">
              {stats?.dedupe_window_seconds ?? '—'}s
            </span>
            <span className="kpi-label">Ventana anti-spam</span>
          </div>
        </div>
      </div>

      <div className="toolbar">
        <button className="btn btn-ghost" onClick={load} disabled={loading}>
          {loading ? 'Actualizando…' : 'Actualizar'}
        </button>
        <button className="btn" onClick={sendTest} disabled={testing}>
          {testing ? 'Enviando…' : 'Enviar alerta de prueba'}
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {test && (
        <div className="alert alert-info">
          <strong>Resultado de la prueba</strong>
          <ul className="result-list">
            {test.results.map((result) => (
              <li key={result.channel}>
                <span className="mono">{result.channel}</span>:{' '}
                <span className={statusClass(result.status)}>
                  {result.status}
                </span>
                {result.detail ? ` · ${result.detail}` : ''}
                {result.error ? ` · ${result.error}` : ''}
              </li>
            ))}
          </ul>
        </div>
      )}

      {stats && stats.by_channel_status.length > 0 && (
        <div className="stats-row">
          {stats.by_channel_status.map((entry) => (
            <div
              className="stat-chip"
              key={`${entry.channel}-${entry.status}`}
            >
              <span className="mono">{entry.channel}</span>
              <span className={statusClass(entry.status)}>{entry.status}</span>
              <strong>{entry.count}</strong>
            </div>
          ))}
        </div>
      )}

      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>Fecha</th>
              <th>Producto</th>
              <th>Canal</th>
              <th>Destino</th>
              <th>Estado</th>
              <th>Intentos</th>
              <th>Detalle</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((log) => (
              <tr key={log.id}>
                <td className="small">{formatDate(log.created_at)}</td>
                <td>
                  <div className="product-name">{log.product_name}</div>
                  <div className="muted small mono">{log.event_type}</div>
                </td>
                <td className="mono">{log.channel}</td>
                <td className="small">{log.destination ?? '—'}</td>
                <td>
                  <span className={statusClass(log.status)}>{log.status}</span>
                </td>
                <td className="mono">{log.attempts}</td>
                <td className="small">
                  {log.error ?? log.detail ?? '—'}
                  {log.correlation_id && (
                    <div className="muted small mono">
                      cid: {log.correlation_id}
                    </div>
                  )}
                </td>
              </tr>
            ))}
            {logs.length === 0 && !loading && (
              <tr>
                <td colSpan={7} className="empty">
                  Todavía no hay alertas. vende hasta cruzar el umbral o usa
                  «Enviar alerta de prueba».
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  )
}
