import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { api } from '../api'
import {
  casheaPrice,
  categoryLabel,
  money,
  paymentLabel,
  productPrice,
  statusLabel,
} from '../format'
import { Icon } from '../icons'
import casheaLogo from '../assets/cashea-logo.png'
import type { DashboardRow, PaymentMethod, Sale, StockUnit } from '../types'
import { InvoiceLightbox } from './InvoiceLightbox'

interface Line {
  row: DashboardRow
  quantity: number
  unitPrice: number
  imeis: string[]
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
  idempotencyKey,
  onClose,
  onDone,
}: {
  initialRow: DashboardRow | null
  idempotencyKey: string
  onClose: () => void
  onDone: () => void
}) {
  const [products, setProducts] = useState<DashboardRow[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [lines, setLines] = useState<Line[]>(() =>
    initialRow
      ? [
          {
            row: initialRow,
            quantity: 1,
            unitPrice: productPrice(initialRow),
            imeis: [],
          },
        ]
      : [],
  )
  const [payment, setPayment] = useState<PaymentMethod>('cash')
  const [paymentOpen, setPaymentOpen] = useState(false)
  const [customer, setCustomer] = useState('')
  const [vendedor, setVendedor] = useState('')
  const [note, setNote] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [receipt, setReceipt] = useState<Sale | null>(null)
  const [key, setKey] = useState(idempotencyKey)
  const [invoiceFile, setInvoiceFile] = useState<File | null>(null)
  const [invoiceInputKey, setInvoiceInputKey] = useState(0)
  const [invoiceBusy, setInvoiceBusy] = useState(false)
  const [invoiceError, setInvoiceError] = useState<string | null>(null)
  const [receiptInvoiceUrl, setReceiptInvoiceUrl] = useState<string | null>(null)
  const [receiptLightboxOpen, setReceiptLightboxOpen] = useState(false)
  const [unitOptions, setUnitOptions] = useState<Record<string, StockUnit[]>>(
    {},
  )
  const [unitLoading, setUnitLoading] = useState<string | null>(null)
  const [openPicker, setOpenPicker] = useState<string | null>(null)
  const [manualImei, setManualImei] = useState('')

  const defaultUnitPrice = (row: DashboardRow) =>
    payment === 'cashea' ? casheaPrice(row) : productPrice(row)

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

  useEffect(() => {
    let active = true
    let objectUrl: string | null = null
    if (!receipt?.invoice_uploaded_at) {
      setReceiptInvoiceUrl(null)
      return
    }
    api
      .invoiceUrl(receipt.id)
      .then((data) => {
        if (active) {
          objectUrl = data.revoke ? data.url : null
          setReceiptInvoiceUrl(data.url)
        } else if (data.revoke) {
          URL.revokeObjectURL(data.url)
        }
      })
      .catch(() => {
        if (active) setReceiptInvoiceUrl(null)
      })
    return () => {
      active = false
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [receipt?.id, receipt?.invoice_uploaded_at])

  const totals = useMemo(() => {
    const subtotal = round2(
      lines.reduce(
        (sum, line) => sum + line.unitPrice * line.quantity,
        0,
      ),
    )
    return { subtotal }
  }, [lines])

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
          { row, quantity: 1, unitPrice: defaultUnitPrice(row), imeis: [] },
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
      current.map((line) => {
        if (line.row.id !== productId) return line
        const quantity = Math.max(
          0,
          Math.min(line.row.quantity, Math.floor(value)),
        )
        return {
          ...line,
          quantity,
          imeis: line.imeis.slice(0, quantity),
        }
      }),
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

  const loadUnits = async (productId: string) => {
    setUnitLoading(productId)
    try {
      const units = await api.stockUnits(productId, 'available')
      setUnitOptions((current) => ({ ...current, [productId]: units }))
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setUnitLoading((current) => (current === productId ? null : current))
    }
  }

  const togglePicker = (productId: string) => {
    setManualImei('')
    setOpenPicker((current) => {
      const next = current === productId ? null : productId
      if (next) void loadUnits(productId)
      return next
    })
  }

  const addImei = (productId: string, raw: string) => {
    const value = raw.trim()
    if (!value) return
    setLines((current) =>
      current.map((line) => {
        if (line.row.id !== productId) return line
        if (line.imeis.includes(value) || line.imeis.length >= line.quantity) {
          return line
        }
        return { ...line, imeis: [...line.imeis, value] }
      }),
    )
  }

  const removeImei = (productId: string, value: string) => {
    setLines((current) =>
      current.map((line) =>
        line.row.id === productId
          ? { ...line, imeis: line.imeis.filter((imei) => imei !== value) }
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

    // Validar cliente y vendedor
    if (!customer.trim()) {
      setError('El cliente es obligatorio.')
      return
    }
    if (!vendedor.trim()) {
      setError('El vendedor es obligatorio.')
      return
    }

    // Validar cada línea
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
          imeis: line.imeis,
        })),
        payment_method: payment,
        currency: 'USD',
        customer_name: customer.trim(),
        vendedor: vendedor.trim(),
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
    setCustomer('')
    setVendedor('')
    setNote('')
    setError(null)
    setInvoiceFile(null)
    setInvoiceError(null)
    setReceiptLightboxOpen(false)
    setOpenPicker(null)
    setManualImei('')
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
      setReceiptLightboxOpen(false)
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
                ? `${money(receipt.total)} · ${statusLabel(receipt.status)}`
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
                        {item.quantity} × {money(item.unit_price)}
                        {item.imei ? ` · IMEI: ${item.imei}` : ''}
                      </span>
                    </div>
                    <strong>{money(item.line_total)}</strong>
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
                {receipt.vendedor && (
                  <div>
                    <dt>Vendedor</dt>
                    <dd>{receipt.vendedor}</dd>
                  </div>
                )}
                {receipt.note && (
                  <div>
                    <dt>Nota</dt>
                    <dd>{receipt.note}</dd>
                  </div>
                )}
                <div className="receipt-total-row">
                  <dt>Total</dt>
                  <dd>{money(receipt.total)}</dd>
                </div>
              </dl>

              <div className="form-section">
                <h3>Factura fiscal (opcional)</h3>
                {receipt.invoice_uploaded_at && receiptInvoiceUrl ? (
                  <>
                    <div className="invoice-meta">
                      <span>
                        <Icon name="receipt" size={16} />
                        {receipt.invoice_filename ?? 'Factura adjunta'}
                      </span>
                      <button
                        className="link-btn"
                        type="button"
                        onClick={() => setReceiptLightboxOpen(true)}
                      >
                        Ver factura
                      </button>
                    </div>
                    {receipt.invoice_content_type?.startsWith('image/') && (
                      <img
                        className="invoice-preview invoice-preview-clickable"
                        src={receiptInvoiceUrl}
                        alt="Factura fiscal"
                        role="button"
                        tabIndex={0}
                        title="Ampliar factura"
                        onClick={() => setReceiptLightboxOpen(true)}
                        onKeyDown={(event) => {
                          if (event.key === 'Enter' || event.key === ' ') {
                            event.preventDefault()
                            setReceiptLightboxOpen(true)
                          }
                        }}
                      />
                    )}
                  </>
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
                              <strong>{money(defaultUnitPrice(row))}</strong>
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
                        <div className="field imei-field">
                          <span>
                            IMEIs ({line.imeis.length}/{line.quantity})
                          </span>
                          <div className="imei-chips">
                            {line.imeis.map((imei) => (
                              <span
                                key={imei}
                                className="chip chip-removable mono"
                              >
                                {imei}
                                <button
                                  type="button"
                                  onClick={() => removeImei(line.row.id, imei)}
                                  aria-label={`Quitar IMEI ${imei}`}
                                >
                                  <Icon name="close" size={11} />
                                </button>
                              </span>
                            ))}
                            {line.imeis.length < line.quantity && (
                              <button
                                type="button"
                                className="chip chip-add"
                                onClick={() => togglePicker(line.row.id)}
                              >
                                <Icon name="plus" size={13} />
                                Añadir
                              </button>
                            )}
                          </div>
                          {line.imeis.length < line.quantity && (
                            <span className="muted small">
                              Faltan {line.quantity - line.imeis.length}{' '}
                              IMEI(s) por asignar.
                            </span>
                          )}
                          {openPicker === line.row.id && (
                            <div className="imei-picker">
                              {unitLoading === line.row.id ? (
                                <span className="muted small">
                                  Cargando IMEIs…
                                </span>
                              ) : (
                                <>
                                  {(unitOptions[line.row.id] ?? []).filter(
                                    (unit) =>
                                      !line.imeis.includes(unit.imei),
                                  ).length > 0 ? (
                                    <div className="chip-row">
                                      {(unitOptions[line.row.id] ?? [])
                                        .filter(
                                          (unit) =>
                                            !line.imeis.includes(unit.imei),
                                        )
                                        .map((unit) => (
                                          <button
                                            key={unit.id}
                                            type="button"
                                            className="chip mono"
                                            onClick={() =>
                                              addImei(line.row.id, unit.imei)
                                            }
                                          >
                                            {unit.imei}
                                          </button>
                                        ))}
                                    </div>
                                  ) : (
                                    <p className="muted small">
                                      No hay IMEIs registrados disponibles.
                                    </p>
                                  )}
                                  <div className="imei-manual">
                                    <input
                                      value={manualImei}
                                      onChange={(event) =>
                                        setManualImei(event.target.value)
                                      }
                                      placeholder="Escribir IMEI manual"
                                      maxLength={64}
                                    />
                                    <button
                                      type="button"
                                      className="btn btn-ghost btn-sm"
                                      onClick={() => {
                                        addImei(line.row.id, manualImei)
                                        setManualImei('')
                                      }}
                                    >
                                      Añadir
                                    </button>
                                  </div>
                                  <button
                                    type="button"
                                    className="link-btn"
                                    onClick={() => setOpenPicker(null)}
                                  >
                                    Cerrar lista
                                  </button>
                                </>
                              )}
                            </div>
                          )}
                        </div>
                        <div className="sale-line-total">
                          <span className="muted small">Total</span>
                          <strong>{money(line.unitPrice * line.quantity)}</strong>
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
                    <span>Cliente (obligatorio)</span>
                    <input
                      value={customer}
                      onChange={(event) => setCustomer(event.target.value)}
                      placeholder="Nombre o teléfono"
                      maxLength={120}
                    />
                  </label>
                  <label className="field">
                    <span>Vendedor (obligatorio)</span>
                    <input
                      value={vendedor}
                      onChange={(event) => setVendedor(event.target.value)}
                      placeholder="Nombre del vendedor"
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
                  <strong>{money(totals.subtotal)}</strong>
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
                <strong>{money(totals.subtotal)}</strong>
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

      <InvoiceLightbox
        open={receiptLightboxOpen}
        url={receiptInvoiceUrl}
        filename={receipt?.invoice_filename}
        isImage={Boolean(receipt?.invoice_content_type?.startsWith('image/'))}
        onClose={() => setReceiptLightboxOpen(false)}
      />
    </div>
  )
}
