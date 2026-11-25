import { useEffect } from 'react'
import { createPortal } from 'react-dom'
import { Icon } from '../icons'

export function InvoiceLightbox({
  open,
  url,
  filename,
  isImage,
  onClose,
}: {
  open: boolean
  url: string | null
  filename?: string | null
  isImage: boolean
  onClose: () => void
}) {
  useEffect(() => {
    if (!open) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.stopPropagation()
        onClose()
      }
    }
    window.addEventListener('keydown', onKey, true)
    return () => window.removeEventListener('keydown', onKey, true)
  }, [open, onClose])

  if (!open || !url) return null

  const label = filename || 'Factura fiscal'

  return createPortal(
    <div
      className="lightbox"
      role="dialog"
      aria-modal="true"
      aria-label={label}
      onMouseDown={onClose}
    >
      <figure
        className="lightbox-figure"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="lightbox-bar">
          <span className="lightbox-title">
            <Icon name="receipt" size={16} />
            {label}
          </span>
          <div className="lightbox-actions">
            <a
              className="btn btn-ghost btn-sm"
              href={url}
              download={filename || undefined}
            >
              <Icon name="download" size={15} />
              Descargar
            </a>
            <button
              className="icon-btn"
              type="button"
              onClick={onClose}
              aria-label="Cerrar"
            >
              <Icon name="close" />
            </button>
          </div>
        </div>
        {isImage ? (
          <img className="lightbox-image" src={url} alt={label} />
        ) : (
          <iframe className="lightbox-frame" src={url} title={label} />
        )}
      </figure>
    </div>,
    document.body,
  )
}
