import { useEffect, useState } from 'react'
import { api } from '../api'
import { dateTime, money, paymentLabel, statusLabel } from '../format'
import { Icon } from '../icons'
import type { Sale } from '../types'

function fileSize(bytes: number | null): string {
  if (!bytes) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function SaleDetailDrawer({
  sale,
  onClose,
  onChanged,
}: {
  sale: Sale
  onClose: () => void
  onChanged: () => void
}) {
  const [current, setCurrent] = useState(sale)
  const [file, setFile] = useState<File | null>(null)
  const [inputKey, setInputKey] = useState(0)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [invoicePreviewUrl, setInvoicePreviewUrl] = useState<string | null>(null)

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
    let active = true
    let objectUrl: string | null = null
    if (!current.invoice_uploaded_at) {
      setInvoicePreviewUrl(null)
      return
    }
    api
      .invoiceUrl(current.id)
      .then((data) => {
        if (active) {
          objectUrl = data.url
          setInvoicePreviewUrl(data.url)
        } else {
          URL.revokeObjectURL(data.url)
        }
      })
      .catch(() => {
        if (active) setInvoicePreviewUrl(null)
      })
    return () => {
      active = false
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [current.id, current.invoice_uploaded_at])

  const preview = invoicePreviewUrl
  const isImage = current.invoice_content_type?.startsWith('image/')

  const upload = async () => {
    if (!file) {
      setError('Selecciona una imagen o PDF.')
      return
    }
    setBusy(true)
    setError(null)
    try {
      const updated = await api.uploadInvoice(current.id, file)
      setCurrent(updated)
      setFile(null)
      setInputKey((value) => value + 1)
      onChanged()
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const remove = async () => {
    if (!window.confirm('¿Eliminar la factura de esta venta?')) return
    setBusy(true)
    setError(null)
    try {
      await api.deleteInvoice(current.id)
      setCurrent({
        ...current,
        invoice_filename: null,
        invoice_content_type: null,
        invoice_size: null,
        invoice_uploaded_at: null,
      })
      setFile(null)
      setInputKey((value) => value + 1)
      onChanged()
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
        className="drawer drawer-wide"
        role="dialog"
        aria-modal="true"
        aria-label={`Venta ${current.sale_number}`}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="drawer-head">
          <div>
            <span className="eyebrow">Detalle de venta</span>
            <h2>{current.sale_number}</h2>
            <p className="muted small">
              {dateTime(current.created_at)} ·{' '}
              {money(current.total)} ·{' '}
              {statusLabel(current.status)}
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

        <div className="drawer-body">
          <ul className="receipt-items">
            {current.items.map((item) => (
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
              <dd>{paymentLabel(current.payment_method)}</dd>
            </div>
            {current.customer_name && (
              <div>
                <dt>Cliente</dt>
                <dd>{current.customer_name}</dd>
              </div>
            )}
            {current.vendedor && (
              <div>
                <dt>Vendedor</dt>
                <dd>{current.vendedor}</dd>
              </div>
            )}
            {current.note && (
              <div>
                <dt>Nota</dt>
                <dd>{current.note}</dd>
              </div>
            )}
            <div className="receipt-total-row">
              <dt>Total</dt>
              <dd>{money(current.total, current.currency)}</dd>
            </div>
          </dl>

          <div className="form-section">
            <h3>Factura fiscal</h3>
            {current.invoice_uploaded_at && preview ? (
              <>
                <div className="invoice-meta">
                  <span>
                    <Icon name="receipt" size={16} />
                    {current.invoice_filename ?? 'Factura adjunta'}
                  </span>
                  <span className="muted small">
                    {fileSize(current.invoice_size)}
                  </span>
                </div>
                {isImage ? (
                  <img
                    className="invoice-preview"
                    src={preview}
                    alt="Factura fiscal"
                  />
                ) : (
                  <iframe
                    className="invoice-preview invoice-pdf"
                    src={preview}
                    title="Factura fiscal"
                  />
                )}
                <div className="row-actions">
                  <a
                    className="btn btn-ghost btn-sm"
                    href={preview ?? undefined}
                  >
                    Descargar
                  </a>
                  <button
                    className="btn btn-ghost btn-sm"
                    type="button"
                    onClick={remove}
                    disabled={busy}
                  >
                    Eliminar
                  </button>
                </div>
              </>
            ) : (
              <p className="muted small">
                Esta venta todavía no tiene factura adjunta.
              </p>
            )}

            <label className="field">
              <span>
                {current.invoice_uploaded_at
                  ? 'Reemplazar factura'
                  : 'Adjuntar factura'}{' '}
                (JPG, PNG, WebP o PDF · máx. 10 MB)
              </span>
              <input
                key={inputKey}
                type="file"
                accept="image/jpeg,image/png,image/webp,application/pdf"
                onChange={(event) =>
                  setFile(event.target.files?.[0] ?? null)
                }
                disabled={busy}
              />
            </label>
            <button
              className="btn btn-primary btn-sm"
              type="button"
              onClick={upload}
              disabled={busy || !file}
            >
              {busy
                ? 'Guardando…'
                : current.invoice_uploaded_at
                  ? 'Reemplazar factura'
                  : 'Adjuntar factura'}
            </button>
          </div>

          {error && (
            <div className="alert alert-error">
              <Icon name="alert" />
              <span>{error}</span>
            </div>
          )}
        </div>

        <footer className="drawer-foot">
          <button
            className="btn btn-ghost"
            onClick={onClose}
            disabled={busy}
          >
            Cerrar
          </button>
        </footer>
      </aside>
    </div>
  )
}
