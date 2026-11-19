import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { api } from '../api'
import {
  categoryLabel,
  money,
  paymentLabel,
  productCost,
  productPrice,
  statusLabel,
} from '../format'
import { Icon } from '../icons'
import casheaLogo from '../assets/cashea-logo.png'
import { invoiceUrl } from '../media'
import type {
  Currency,
  DashboardRow,
  PaymentMethod,
  Sale,
} from '../types'

interface Line {
  row: DashboardRow
  quantity: number
  unitPrice: number
}

const PAYMENTS: { id: PaymentMethod; label: string }[] = [
  { id: 'cash', label: 'Efectivo 💵' },
  { id: 'card', label: 'Tarjeta 💳' },
  { id: 'transfer', label: 'Transferencia 🏦' },
  { id: 'other', label: 'Otro 🔖' },
  { id: 'cashea', label: 'Cashea' },
]

function makeKey(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID()
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function round2(value: number): number {
  return Math.round((value + Number.EPSILON) * 100) / 100
}

export function SaleDrawer({
  initialRow,
  defaultCurrency,
  idempotencyKey,
  onClose,
  onDone,
}: {
  initialRow: DashboardRow | null
  defaultCurrency: Currency
  idempotencyKey: string
  onClose: () => void
  onDone: () => void
}) {
  const [products, setProducts] = useState<DashboardRow[]>([])
  const [currency, setCurrency] = useState<Currency>(defaultCurrency)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [lines, setLines] = useState<Line[]>(() =>
    initialRow
      ? [
          {
            row: initialRow,
            quantity: 1,
            unitPrice: productPrice(initialRow, defaultCurrency),
          },
        ]
      : [],
  )
  const [payment, setPayment] = useState<PaymentMethod>('cash')
  const [paymentOpen, setPaymentOpen] = useState(false)
  const [customer, setCustomer] = useState('')
  const [note, setNote] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [receipt, setReceipt] = useState<Sale | null>(null)
  const [key, setKey] = useState(idempotencyKey)
  const [invoiceFile, setInvoiceFile] = useState<File | null>(null)
  const [invoiceInputKey, setInvoiceInputKey] = useState(0)
  const [invoiceBusy, setInvoiceBusy] = useState(false)
  const [invoiceError, setInvoiceError] = useState<string | null>(null)

  const refreshProducts = () => {
    setLoading(true)
    return api
      .dashboard()
      .then((data) => {
        setProducts(data.products)
        setLoadError(null)
      })
      .catch((err: Error) => setLoadError(err.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    let active = true
    api
      .dashboard()
      .then((data) => {
        if (active) setProducts(data.products)
      })
      .catch((err: Error) => {
        if (active) setLoadError(err.message)
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [])

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
    const onClick = (event: MouseEvent) => {
      if (
        paymentOpen &&
        !(event.target as HTMLElement)?.closest('.custom-select')
      ) {
        setPaymentOpen(false)
      }
    }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [paymentOpen])

  const totals = useMemo(() => {
    const subtotal = round2(
      lines.reduce(
        (sum, line) => sum + line.unitPrice * line.quantity,
        0,
      ),
    )
    const cost = round2(
      lines.reduce(
        (sum, line) => sum + productCost(line.row, currency) * line.quantity,
        0,
      ),
    )
    return { subtotal, cost, margin: round2(subtotal - cost) }
  }, [lines, currency])

  const available = useMemo(() => {
    const query = search.trim().toLowerCase()
    return products
      .filter((row) => {
        if (!query) return row.quantity > 0
        return [row.product_name, row.sku, row.brand, row.model]
          .join(' ')
          .toLowerCase()
          .includes(query)
      })
      .slice(0, query ? 8 : 6)
  }, [products, search])

  const addProduct = (row: DashboardRow) => {
    if (row.quantity === 0) return
    setError(null)
    setLines((current) => {
      const existing = current.find((line) => line.row.id === row.id)
      if (!existing) {
        return [
          ...current,
          { row, quantity: 1, unitPrice: productPrice(row, currency) },
        ]
      }
      if (existing.quantity >= row.quantity) return current
      return current.map((line) =>
        line.row.id === row.id
          ? { ...line, quantity: line.quantity + 1 }
          : line,
      )
    })
    setSearch('')
  }

  const updateQuantity = (productId: string, value: number) => {
    setLines((current) =>
      current.map((line) =>
        line.row.id === productId
          ? {
              ...line,
              quantity: Math.max(0, Math.min(line.row.quantity, Math.floor(value))),
            }
          : line,
      ),
    )
  }

  const updatePrice = (productId: string, value: number) => {
    setLines((current) =>
      current.map((line) =>
        line.row.id === productId
          ? { ...line, unitPrice: Math.max(0, value) }
          : line,
      ),
    )
  }

  const removeLine = (productId: string) => {
    setLines((current) => current.filter((line) => line.row.id !== productId))
  }

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (lines.length === 0) {
      setError('Añade al menos un producto a la venta.')
      return
    }
    for (const line of lines) {
      if (!Number.isInteger(line.quantity) || line.quantity <= 0) {
        setError('Cada línea debe tener una cantidad entera mayor que 0.')
        return
      }
      if (line.quantity > line.row.quantity) {
        setError(`No hay stock suficiente de ${line.row.product_name}.`)
        return
      }
      if (!Number.isFinite(line.unitPrice) || line.unitPrice < 0) {
        setError('Los precios no pueden ser negativos.')
        return
      }
    }

    setBusy(true)
    setError(null)
    try {
      const sale = await api.createSale({
        items: lines.map((line) => ({
          product_id: line.row.id,
          quantity: line.quantity,
          unit_price: round2(line.unitPrice),
        })),
        payment_method: payment,
        currency,
        customer_name: customer.trim() || null,
        note: note.trim() || null,
        idempotency_key: key,
      })
      setReceipt(sale)
      void refreshProducts()
      onDone()
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const startNewSale = () => {
    setReceipt(null)
    setLines([])
    setSearch('')
    setPayment('cash')
    setCurrency(defaultCurrency)
    setCustomer('')
    setNote('')
    setError(null)
    setInvoiceFile(null)
    setInvoiceError(null)
    setInvoiceInputKey((value) => value + 1)
    setKey(makeKey())
    void refreshProducts()
  }

  const uploadReceiptInvoice = async () => {
    if (!receipt || !invoiceFile) return
    setInvoiceBusy(true)
    setInvoiceError(null)
    try {
      const updated = await api.uploadInvoice(receipt.id, invoiceFile)
      setReceipt(updated)
      setInvoiceFile(null)
      setInvoiceInputKey((value) => value + 1)
      onDone()
    } catch (err) {
      setInvoiceError((err as Error).message)
    } finally {
      setInvoiceBusy(false)
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
        className="drawer drawer-wide"
        role="dialog"
        aria-modal="true"
        aria-label="Nueva venta"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="drawer-head">
          <div>
            <span className="eyebrow">
              {receipt ? 'Venta completada' : 'Punto de venta'}
            </span>
            <h2>{receipt ? receipt.sale_number : 'Nueva venta'}</h2>
            <p className="muted small">
              {receipt
                ? `${money(receipt.total, receipt.currency)} · ${statusLabel(receipt.status)}`
                : 'Carrito multi-producto con descuento de stock automático.'}
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

        {receipt ? (
          <>
            <div className="drawer-body">
              <div className="receipt-success">
                <span className="receipt-check">
                  <Icon name="check" size={26} />
                </span>
                <div>
                  <strong>Venta registrada</strong>
                  <p className="muted small">
                    El stock se ha descontado correctamente.
                  </p>
                </div>
              </div>

              <ul className="receipt-items">
                {receipt.items.map((item) => (
                  <li key={item.id}>
                    <div>
                      <strong>{item.product_name}</strong>
                      <span className="muted small">
                        {item.quantity} × {money(item.unit_price, receipt.currency)}
                      </span>
                    </div>
                    <strong>{money(item.line_total, receipt.currency)}</strong>
                  </li>
                ))}
              </ul>

              <dl className="receipt-totals">
                <div>
                  <dt>Método de pago</dt>
                  <dd>{paymentLabel(receipt.payment_method)}</dd>
                </div>
                {receipt.customer_name && (
                  <div>
                    <dt>Cliente</dt>
                    <dd>{receipt.customer_name}</dd>
                  </div>
                )}
                <div>
                  <dt>Coste</dt>
                  <dd>{money(receipt.cost_total, receipt.currency)}</dd>
                </div>
                <div>
                  <dt>Margen</dt>
                  <dd>{money(receipt.margin, receipt.currency)}</dd>
                </div>
                <div className="receipt-total-row">
                  <dt>Total</dt>
                  <dd>{money(receipt.total, receipt.currency)}</dd>
                </div>
              </dl>

              <div className="form-section">
                <h3>Factura fiscal (opcional)</h3>
                {receipt.invoice_uploaded_at && invoiceUrl(receipt) ? (
                  <div className="invoice-meta">
                    <span>
                      <Icon name="receipt" size={16} />
                      {receipt.invoice_filename ?? 'Factura adjunta'}
                    </span>
                    <a
                      className="link-btn"
                      href={invoiceUrl(receipt) ?? undefined}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Ver factura
                    </a>
                  </div>
                ) : (
                  <p className="muted small">
                    Puedes adjuntarla ahora o más tarde desde el historial.
                  </p>
                )}
                <label className="field">
                  <span>
                    {receipt.invoice_uploaded_at
                      ? 'Reemplazar factura'
                      : 'Adjuntar factura'}{' '}
                    (JPG, PNG, WebP o PDF · máx. 10 MB)
                  </span>
                  <input
                    key={invoiceInputKey}
                    type="file"
                    accept="image/jpeg,image/png,image/webp,application/pdf"
                    onChange={(event) =>
                      setInvoiceFile(event.target.files?.[0] ?? null)
                    }
                    disabled={invoiceBusy}
                  />
                </label>
                <button
                  className="btn btn-ghost btn-sm"
                  type="button"
                  onClick={uploadReceiptInvoice}
                  disabled={invoiceBusy || !invoiceFile}
                >
                  {invoiceBusy
                    ? 'Guardando…'
                    : receipt.invoice_uploaded_at
                      ? 'Reemplazar factura'
                      : 'Adjuntar factura'}
                </button>
                {invoiceError && (
                  <div className="alert alert-error">
                    <Icon name="alert" />
                    <span>{invoiceError}</span>
                  </div>
                )}
              </div>
            </div>
            <footer className="drawer-foot">
              <button className="btn btn-ghost" onClick={onClose}>
                Cerrar
              </button>
              <button className="btn btn-primary" onClick={startNewSale}>
                <Icon name="plus" />
                Nueva venta
              </button>
            </footer>
          </>
        ) : (
          <form className="drawer-form" onSubmit={submit}>
            <div className="drawer-body">
              <div className="form-section compact">
                <h3>Moneda de la venta</h3>
                <div className="segmented">
                  {(['EUR', 'USD'] as Currency[]).map((code) => (
                    <button
                      type="button"
                      key={code}
                      className={currency === code ? 'active' : ''}
                      onClick={() => setCurrency(code)}
                      disabled={lines.length > 0}
                    >
                      {code}
                    </button>
                  ))}
                </div>
                {lines.length > 0 && (
                  <p className="muted small">
                    Vacía el carrito para cambiar de moneda y conservar los
                    precios manuales.
                  </p>
                )}
              </div>

              <div className="sale-picker">
                <label className="search-box">
                  <Icon name="search" size={16} />
                  <input
                    placeholder="Buscar producto por nombre, marca o SKU…"
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                  />
                </label>
                {loading ? (
                  <div className="loading-state">Cargando productos…</div>
                ) : loadError ? (
                  <div className="alert alert-error">{loadError}</div>
                ) : (
                  available.length > 0 && (
                    <ul className="picker-results">
                      {available.map((row) => (
                        <li key={row.id}>
                          <button
                            type="button"
                            onClick={() => addProduct(row)}
                            disabled={row.quantity === 0}
                          >
                            <span>
                              <strong>{row.product_name}</strong>
                              <span className="muted small">
                                {categoryLabel(row.category)} · {row.sku}
                              </span>
                            </span>
                            <span className="picker-side">
                              <span className="muted small">
                                {row.quantity} uds
                              </span>
                              <strong>{money(productPrice(row, currency), currency)}</strong>
                              <Icon name="plus" size={16} />
                            </span>
                          </button>
                        </li>
                      ))}
                    </ul>
                  )
                )}
              </div>

              {lines.length === 0 ? (
                <div className="empty-state sale-empty">
                  <strong>El carrito está vacío</strong>
                  <p>Busca un producto arriba y pulsa para añadirlo.</p>
                </div>
              ) : (
                <ul className="sale-lines">
                  {lines.map((line) => (
                    <li key={line.row.id}>
                      <div className="sale-line-head">
                        <div>
                          <strong>{line.row.product_name}</strong>
                          <span className="muted small">
                            {line.row.sku} · {line.row.quantity} disponibles
                          </span>
                        </div>
                        <button
                          type="button"
                          className="icon-btn small"
                          onClick={() => removeLine(line.row.id)}
                          aria-label="Quitar"
                        >
                          <Icon name="close" size={15} />
                        </button>
                      </div>
                      <div className="sale-line-grid">
                        <label className="field">
                          <span>Cantidad</span>
                          <input
                            type="number"
                            min={1}
                            max={line.row.quantity}
                            step={1}
                            value={line.quantity}
                            onChange={(event) =>
                              updateQuantity(
                                line.row.id,
                                Number(event.target.value) || 0,
                              )
                            }
                          />
                        </label>
                        <label className="field">
                          <span>Precio unitario</span>
                          <input
                            type="number"
                            min={0}
                            step="0.01"
                            value={line.unitPrice}
                            onChange={(event) =>
                              updatePrice(
                                line.row.id,
                                Number(event.target.value) || 0,
                              )
                            }
                          />
                        </label>
                        <div className="sale-line-total">
                          <span className="muted small">Total</span>
                          <strong>
                            {money(
                              line.unitPrice * line.quantity,
                              currency,
                            )}
                          </strong>
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              )}

              <div className="form-section">
                <h3>Detalles</h3>
                <div className="form-grid">
                  <label className="field">
                    <span>Método de pago</span>
                    <div
                      className={`custom-select ${paymentOpen ? 'open' : ''}`}
                      onClick={(event) => {
                        event.stopPropagation()
                        setPaymentOpen((value) => !value)
                      }}
                    >
                      <button
                        type="button"
                        className="custom-select-trigger"
                        aria-label="Seleccionar método de pago"
                      >
                        {payment === 'cashea' ? (
                          <>
                            <img src={casheaLogo} className="custom-select-icon" alt="Cashea" />
                            <span>Cashea</span>
                          </>
                        ) : (
                          <span>{paymentLabel(payment)}</span>
                        )}
                        <Icon name="chevronDown" size={14} />
                      </button>
                      <ul className="custom-select-list" role="listbox">
                        {PAYMENTS.map((entry) => (
                          <li
                            key={entry.id}
                            role="option"
                            aria-selected={payment === entry.id}
                            className={payment === entry.id ? 'active' : ''}
                            onClick={() => {
                              setPayment(entry.id)
                              setPaymentOpen(false)
                            }}
                          >
                            {entry.id === 'cashea' ? (
                              <>
                                <img src={casheaLogo} className="custom-select-icon" alt="Cashea" />
                                <span>{entry.label}</span>
                              </>
                            ) : (
                              <span>{entry.label}</span>
                            )}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </label>
                  <label className="field">
                    <span>Cliente (opcional)</span>
                    <input
                      value={customer}
                      onChange={(event) => setCustomer(event.target.value)}
                      placeholder="Nombre o teléfono"
                      maxLength={120}
                    />
                  </label>
                </div>
                <label className="field">
                  <span>Nota (opcional)</span>
                  <input
                    value={note}
                    onChange={(event) => setNote(event.target.value)}
                    placeholder="Observaciones de la venta"
                    maxLength={500}
                  />
                </label>
              </div>

              <div className="sale-totals">
                <div>
                  <span className="muted small">Subtotal</span>
                  <strong>{money(totals.subtotal, currency)}</strong>
                </div>
                <div>
                  <span className="muted small">Coste</span>
                  <span>{money(totals.cost, currency)}</span>
                </div>
                <div>
                  <span className="muted small">Margen</span>
                  <span className="text-ok">
                    {money(totals.margin, currency)}
                  </span>
                </div>
              </div>

              {error && (
                <div className="alert alert-error">
                  <Icon name="alert" />
                  <span>{error}</span>
                </div>
              )}
            </div>

            <footer className="drawer-foot">
              <div className="drawer-total">
                <span className="muted small">Total</span>
                <strong>{money(totals.subtotal, currency)}</strong>
              </div>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={busy || lines.length === 0}
              >
                {busy ? 'Procesando…' : 'Confirmar venta'}
              </button>
            </footer>
          </form>
        )}
      </aside>
    </div>
  )
}
