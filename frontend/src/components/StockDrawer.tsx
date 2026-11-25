import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { api } from '../api'
import { dateTime, money, bcvPrice, productPrice } from '../format'
import { Icon } from '../icons'
import type { DashboardRow, Movement, StockUnit } from '../types'

export type StockMode = 'entry' | 'exit' | 'set' | 'history'

const TABS: { id: StockMode; label: string }[] = [
  { id: 'entry', label: 'Entrada' },
  { id: 'exit', label: 'Salida' },
  { id: 'set', label: 'Fijar stock' },
  { id: 'history', label: 'Historial' },
]

const HINTS: Record<Exclude<StockMode, 'history'>, string> = {
  entry: 'Suma unidades al stock actual.',
  exit: 'Resta unidades del stock actual.',
  set: 'Define el stock final. Puedes dejarlo en 0.',
}

export function StockDrawer({
  row,
  mode,
  onClose,
  onDone,
}: {
  row: DashboardRow
  mode: StockMode
  onClose: () => void
  onDone: (message: string) => void
}) {
  const [tab, setTab] = useState<StockMode>(mode)
  const [quantity, setQuantity] = useState(
    mode === 'set' ? String(row.quantity) : '1',
  )
  const [note, setNote] = useState('')
  const [imeisText, setImeisText] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [movements, setMovements] = useState<Movement[] | null>(null)
  const [availableUnits, setAvailableUnits] = useState<StockUnit[] | null>(
    null,
  )

  useEffect(() => {
    let active = true
    api
      .stockUnits(row.id, 'available')
      .then((units) => {
        if (active) setAvailableUnits(units)
      })
      .catch(() => {
        if (active) setAvailableUnits([])
      })
    return () => {
      active = false
    }
  }, [row.id])

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !busy) onClose()
    }
    window.addEventListener('keydown', onKey)
    const previous = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      window.removeEventListener('keydown', onKey)
      document.body.style.overflow = previous
    }
  }, [busy, onClose])

  useEffect(() => {
    if (tab !== 'history' || movements !== null) return
    let active = true
    api
      .movements(row.id)
      .then((data) => {
        if (active) setMovements(data)
      })
      .catch((err: Error) => {
        if (active) setError(err.message)
      })
    return () => {
      active = false
    }
  }, [tab, movements, row.id])

  const parsed = Number(quantity)
  const validNumber = Number.isInteger(parsed) && parsed >= 0
  const resulting =
    tab === 'set'
      ? parsed
      : tab === 'entry'
        ? row.quantity + parsed
        : row.quantity - parsed
  const excessiveExit = tab === 'exit' && validNumber && resulting < 0
  const parsedImeis = imeisText
    .split(/[\n,;]+/)
    .map((value) => value.trim())
    .filter(Boolean)

  const canSubmit = useMemo(() => {
    if (!validNumber) return false
    if (tab === 'entry' || tab === 'exit') return parsed > 0 && !excessiveExit
    if (tab === 'set') return true
    return false
  }, [validNumber, parsed, tab, excessiveExit])

  const switchTab = (next: StockMode) => {
    setTab(next)
    setError(null)
    if (next === 'set') setQuantity(String(row.quantity))
    else if (next !== 'history') setQuantity('1')
  }

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (!canSubmit || tab === 'history') return
    setBusy(true)
    setError(null)
    try {
      if (tab === 'entry')
        await api.addEntry(row.id, parsed, note, parsedImeis)
      else if (tab === 'exit') await api.addExit(row.id, parsed, note)
      else await api.adjust(row.id, parsed, note)
      onDone(
        tab === 'set'
          ? `Stock fijado en ${parsed} unidades.`
          : tab === 'entry'
            ? `Entrada de ${parsed} unidades registrada.`
            : `Salida de ${parsed} unidades registrada.`,
      )
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div
      className="drawer-backdrop"
      onMouseDown={() => {
        if (!busy) onClose()
      }}
    >
      <aside
        className="drawer"
        role="dialog"
        aria-modal="true"
        aria-label={`Stock de ${row.product_name}`}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="drawer-head">
          <div>
            <span className="eyebrow">Inventario</span>
            <h2>{row.product_name}</h2>
              <p className="muted small mono">
                {row.sku} · {money(productPrice(row))} · {money(bcvPrice(row))}
              </p>
          </div>
          <button
            className="icon-btn"
            onClick={onClose}
            aria-label="Cerrar"
            disabled={busy}
          >
            <Icon name="close" />
          </button>
        </header>

        <div className="drawer-tabs">
          {TABS.map((entry) => (
            <button
              key={entry.id}
              className={tab === entry.id ? 'active' : ''}
              onClick={() => switchTab(entry.id)}
            >
              {entry.label}
            </button>
          ))}
        </div>

        {tab === 'history' ? (
          <>
            <div className="drawer-body">
              {error && <div className="alert alert-error">{error}</div>}
              {movements === null && !error && (
                <div className="loading-state">Cargando movimientos…</div>
              )}
              {movements && movements.length === 0 && (
                <div className="empty-state">
                  <strong>Sin movimientos</strong>
                  <p>Este producto todavía no tiene historial.</p>
                </div>
              )}
              {movements && movements.length > 0 && (
                <ul className="movement-list">
                  {movements.map((movement) => (
                    <li key={movement.id}>
                      <span
                        className={`movement-delta ${
                          movement.delta > 0 ? 'positive' : 'negative'
                        }`}
                      >
                        {movement.delta > 0 ? `+${movement.delta}` : movement.delta}
                      </span>
                      <div className="movement-main">
                        <strong>{movement.movement_type}</strong>
                        <span className="muted small">
                          {dateTime(movement.created_at)}
                        </span>
                        {movement.note && (
                          <span className="small">{movement.note}</span>
                        )}
                      </div>
                      <span className="movement-stock mono">
                        {movement.quantity_before} → {movement.quantity_after}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <footer className="drawer-foot">
              <button className="btn btn-ghost" onClick={onClose}>
                Cerrar
              </button>
            </footer>
          </>
        ) : (
          <form className="drawer-form" onSubmit={submit}>
            <div className="drawer-body">
              <div className="stock-hero">
                <div>
                  <span className="muted small">Stock actual</span>
                  <strong>{row.stock_synced ? row.quantity : '—'}</strong>
                </div>
                <span className="stock-hero-arrow">→</span>
                <div>
                  <span className="muted small">Quedará en</span>
                  <strong className={resulting === 0 ? 'text-danger' : ''}>
                    {validNumber ? resulting : '—'}
                  </strong>
                </div>
              </div>
              <p className="muted small drawer-hint">{HINTS[tab]}</p>

              <label className="field">
                <span>
                  {tab === 'set' ? 'Stock final' : 'Cantidad'}
                </span>
                <input
                  type="number"
                  min={tab === 'set' ? 0 : 1}
                  step={1}
                  value={quantity}
                  onChange={(event) => setQuantity(event.target.value)}
                  autoFocus
                />
              </label>
              {tab === 'entry' && (
                <>
                  <label className="field">
                    <span>IMEIs (opcional · uno por línea)</span>
                    <textarea
                      rows={3}
                      value={imeisText}
                      onChange={(event) => setImeisText(event.target.value)}
                      placeholder={'356789012345678\n356789012345679'}
                    />
                  </label>
                  {parsedImeis.length > 0 && parsedImeis.length !== parsed && (
                    <p className="muted small">
                      Has escrito {parsedImeis.length} IMEI(s) para{' '}
                      {parsed || 0} unidad(es).
                    </p>
                  )}
                  <div className="imei-stock">
                    <span className="muted small">
                      IMEIs disponibles en stock
                      {availableUnits ? ` (${availableUnits.length})` : ''}
                    </span>
                    {availableUnits && availableUnits.length > 0 ? (
                      <div className="chip-row">
                        {availableUnits.map((unit) => (
                          <span key={unit.id} className="chip mono">
                            {unit.imei}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <p className="muted small">Sin IMEIs registrados.</p>
                    )}
                  </div>
                </>
              )}

              <div className="quick-row">
                {tab === 'set' && (
                  <>
                    <button
                      type="button"
                      className="chip"
                      onClick={() => setQuantity('0')}
                    >
                      Vaciar (0)
                    </button>
                    <button
                      type="button"
                      className="chip"
                      onClick={() => setQuantity(String(row.quantity))}
                    >
                      Actual ({row.quantity})
                    </button>
                  </>
                )}
                {tab === 'entry' && (
                  <>
                    <button
                      type="button"
                      className="chip"
                      onClick={() => setQuantity('1')}
                    >
                      +1
                    </button>
                    <button
                      type="button"
                      className="chip"
                      onClick={() => setQuantity('5')}
                    >
                      +5
                    </button>
                    <button
                      type="button"
                      className="chip"
                      onClick={() => setQuantity('10')}
                    >
                      +10
                    </button>
                  </>
                )}
                {tab === 'exit' && (
                  <>
                    <button
                      type="button"
                      className="chip"
                      onClick={() => setQuantity('1')}
                    >
                      1
                    </button>
                    {row.quantity > 0 && (
                      <button
                        type="button"
                        className="chip chip-danger"
                        onClick={() => setQuantity(String(row.quantity))}
                      >
                        Vaciar todo
                      </button>
                    )}
                  </>
                )}
              </div>

              <label className="field">
                <span>Nota (opcional)</span>
                <input
                  type="text"
                  maxLength={500}
                  value={note}
                  onChange={(event) => setNote(event.target.value)}
                  placeholder={
                    tab === 'entry'
                      ? 'Recepción de proveedor'
                      : tab === 'exit'
                        ? 'Venta en tienda'
                        : 'Corrección de inventario'
                  }
                />
              </label>

              {excessiveExit && (
                <div className="alert alert-error">
                  <Icon name="alert" />
                  <span>No puedes sacar más unidades de las disponibles.</span>
                </div>
              )}
              {error && (
                <div className="alert alert-error">
                  <Icon name="alert" />
                  <span>{error}</span>
                </div>
              )}
            </div>

            <footer className="drawer-foot">
              <button
                type="button"
                className="btn btn-ghost"
                onClick={onClose}
                disabled={busy}
              >
                Cancelar
              </button>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={!canSubmit || busy}
              >
                {busy ? 'Guardando…' : 'Confirmar'}
              </button>
            </footer>
          </form>
        )}
      </aside>
    </div>
  )
}
