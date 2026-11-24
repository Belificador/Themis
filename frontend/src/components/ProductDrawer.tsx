import { useEffect, useState, type FormEvent } from 'react'
import { api } from '../api'
import { Icon } from '../icons'
import { productImageUrl } from '../media'
import type { Category, Product, ProductInput } from '../types'

const CATEGORIES: { id: Category; label: string }[] = [
  { id: 'phone', label: 'Teléfono' },
  { id: 'tablet', label: 'Tablet' },
  { id: 'accessory', label: 'Accesorio' },
]

interface FormState {
  sku: string
  brand: string
  model: string
  ram_gb: string
  storage_gb: string
  color: string
  category: Category
  price_usd: string
  price_bcv_usd: string
  price_cashea_usd: string
  camera: string
  threshold: string
}

function stateFromProduct(product: Product | null): FormState {
  return {
    sku: product?.sku ?? '',
    brand: product?.brand ?? '',
    model: product?.model ?? '',
    ram_gb: String(product?.ram_gb ?? 0),
    storage_gb: String(product?.storage_gb ?? 0),
    color: product?.color ?? 'Estándar',
    category: product?.category ?? 'phone',
    price_usd: String(product?.price_usd ?? 0),
    price_bcv_usd: String(product?.price_bcv_usd ?? 0),
    price_cashea_usd: String(product?.price_cashea_usd ?? 0),
    camera: product?.camera ?? '',
    threshold: String(product?.threshold ?? 0),
  }
}

export function ProductDrawer({
  product,
  onClose,
  onDone,
}: {
  product: Product | null
  onClose: () => void
  onDone: (message: string) => void
}) {
  const [form, setForm] = useState<FormState>(() => stateFromProduct(product))
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [imageFile, setImageFile] = useState<File | null>(null)
  const [imagePreview, setImagePreview] = useState<string | null>(null)
  const [removeImage, setRemoveImage] = useState(false)
  const isEdit = product !== null
  const existingImage = product ? productImageUrl(product) : null
  const displayedImage =
    imagePreview ?? (removeImage ? null : existingImage)

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
    return () => {
      if (imagePreview) URL.revokeObjectURL(imagePreview)
    }
  }, [imagePreview])

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setForm((current) => ({ ...current, [key]: value }))
  }

  const chooseImage = (file: File | null) => {
    setImageFile(file)
    setRemoveImage(false)
    setImagePreview(file ? URL.createObjectURL(file) : null)
  }

  const clearImage = () => {
    setImageFile(null)
    setImagePreview(null)
    setRemoveImage(true)
  }

  const previewName = [
    form.brand.trim(),
    form.model.trim(),
    Number(form.ram_gb) > 0 ? `${form.ram_gb}GB` : '',
    Number(form.storage_gb) > 0 ? `${form.storage_gb}GB` : '',
    form.color.trim(),
  ]
    .filter(Boolean)
    .join(' ')

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (
      !form.sku.trim() ||
      !form.brand.trim() ||
      !form.model.trim() ||
      !form.color.trim()
    ) {
      setError('Completa SKU, marca, modelo y color.')
      return
    }
    if (
      [
        form.price_usd,
        form.price_bcv_usd,
        form.price_cashea_usd,
        form.threshold,
        form.ram_gb,
        form.storage_gb,
      ]
        .map(Number)
        .some((value) => !Number.isFinite(value) || value < 0)
    ) {
      setError('Los importes, el umbral y la memoria no pueden ser negativos.')
      return
    }

    const payload: ProductInput = {
      sku: form.sku.trim().toUpperCase(),
      brand: form.brand.trim(),
      model: form.model.trim(),
      ram_gb: Number(form.ram_gb) || 0,
      storage_gb: Number(form.storage_gb) || 0,
      color: form.color.trim(),
      category: form.category,
      price_usd: Number(form.price_usd) || 0,
      price_bcv_usd: Number(form.price_bcv_usd) || 0,
      price_cashea_usd: Number(form.price_cashea_usd) || 0,
      ram_virtual_gb: 0,
      camera: form.camera.trim() || null,
      threshold: Number(form.threshold) || 0,
    }

    setBusy(true)
    setError(null)
    try {
      const saved = product
        ? await api.updateProduct(product.id, payload)
        : await api.createProduct(payload)
      let imageNote = ''
      try {
        if (imageFile) {
          await api.uploadProductImage(saved.id, imageFile)
        } else if (isEdit && removeImage) {
          await api.deleteProductImage(saved.id)
        }
      } catch (err) {
        imageNote = ` La imagen no se pudo actualizar: ${(err as Error).message}`
      }
      onDone(
        (product
          ? 'Producto actualizado.'
          : 'Producto creado y stock inicializado.') + imageNote,
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
        className="drawer drawer-wide"
        role="dialog"
        aria-modal="true"
        aria-label={isEdit ? 'Editar producto' : 'Nuevo producto'}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="drawer-head">
          <div>
            <span className="eyebrow">Catálogo</span>
            <h2>{isEdit ? 'Editar producto' : 'Nuevo producto'}</h2>
            <p className="muted small">
              {isEdit
                ? 'Los cambios de precio se aplican al instante.'
                : 'Se creará también su registro de stock.'}
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

        <form className="drawer-form" onSubmit={submit}>
          <div className="drawer-body">
            <div className="form-section">
              <h3>Identificación</h3>
              <div className="form-grid">
                <label className="field">
                  <span>SKU</span>
                  <input
                    value={form.sku}
                    onChange={(event) => set('sku', event.target.value)}
                    placeholder="SAM-A57-8-256"
                    autoFocus
                  />
                </label>
                <label className="field">
                  <span>Categoría</span>
                  <div className="segmented">
                    {CATEGORIES.map((entry) => (
                      <button
                        type="button"
                        key={entry.id}
                        className={form.category === entry.id ? 'active' : ''}
                        onClick={() => set('category', entry.id)}
                      >
                        {entry.label}
                      </button>
                    ))}
                  </div>
                </label>
                <label className="field">
                  <span>Marca</span>
                  <input
                    value={form.brand}
                    onChange={(event) => set('brand', event.target.value)}
                    placeholder="Samsung"
                  />
                </label>
                <label className="field">
                  <span>Modelo</span>
                  <input
                    value={form.model}
                    onChange={(event) => set('model', event.target.value)}
                    placeholder="Galaxy A57"
                  />
                </label>
                <label className="field">
                  <span>RAM (GB)</span>
                  <input
                    type="number"
                    min={0}
                    step={1}
                    value={form.ram_gb}
                    onChange={(event) => set('ram_gb', event.target.value)}
                  />
                </label>
                <label className="field">
                  <span>Almacenamiento (GB)</span>
                  <input
                    type="number"
                    min={0}
                    step={1}
                    value={form.storage_gb}
                    onChange={(event) =>
                      set('storage_gb', event.target.value)
                    }
                  />
                </label>
                <label className="field">
                  <span>Color</span>
                  <input
                    value={form.color}
                    onChange={(event) => set('color', event.target.value)}
                    placeholder="Estándar"
                  />
                </label>
              </div>
              {previewName && (
                <p className="preview-name">
                  <span className="muted small">Se mostrará como</span>
                  <strong>{previewName}</strong>
                </p>
              )}
            </div>

            <div className="form-section">
              <h3>Imagen</h3>
              <div className="product-image-edit">
                {displayedImage ? (
                  <img
                    className="product-image-large"
                    src={displayedImage}
                    alt="Vista previa del producto"
                  />
                ) : (
                  <span className="product-image-large product-thumb-empty">
                    <Icon name="box" size={34} />
                  </span>
                )}
                <div className="stack-sm">
                  <label className="field">
                    <span>Foto del producto (JPG, PNG o WebP · máx. 5 MB)</span>
                    <input
                      type="file"
                      accept="image/jpeg,image/png,image/webp"
                      onChange={(event) =>
                        chooseImage(event.target.files?.[0] ?? null)
                      }
                      disabled={busy}
                    />
                  </label>
                  {(displayedImage || imageFile) && (
                    <button
                      type="button"
                      className="btn btn-ghost btn-sm"
                      onClick={clearImage}
                      disabled={busy}
                    >
                      Quitar imagen
                    </button>
                  )}
                </div>
              </div>
            </div>

            <div className="form-section">
              <h3>Precios y stock</h3>
              <div className="form-grid">
                <label className="field">
                  <span>PVP USD</span>
                  <input
                    type="number"
                    min={0}
                    step="0.01"
                    value={form.price_usd}
                    onChange={(event) => set('price_usd', event.target.value)}
                  />
                </label>
                <label className="field">
                  <span>Ref. BCV</span>
                  <input
                    type="number"
                    min={0}
                    step="0.01"
                    value={form.price_bcv_usd}
                    onChange={(event) =>
                      set('price_bcv_usd', event.target.value)
                    }
                  />
                </label>
                <label className="field">
                  <span>Cashea</span>
                  <input
                    type="number"
                    min={0}
                    step="0.01"
                    value={form.price_cashea_usd}
                    onChange={(event) =>
                      set('price_cashea_usd', event.target.value)
                    }
                  />
                </label>
                <label className="field">
                  <span>Cámara</span>
                  <input
                    value={form.camera}
                    onChange={(event) => set('camera', event.target.value)}
                    placeholder="Ej. 50 MP"
                  />
                </label>
                <label className="field">
                  <span>Umbral de alerta</span>
                  <input
                    type="number"
                    min={0}
                    step={1}
                    value={form.threshold}
                    onChange={(event) =>
                      set('threshold', event.target.value)
                    }
                  />
                </label>
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
            <button
              type="button"
              className="btn btn-ghost"
              onClick={onClose}
              disabled={busy}
            >
              Cancelar
            </button>
            <button type="submit" className="btn btn-primary" disabled={busy}>
              {busy
                ? 'Guardando…'
                : isEdit
                  ? 'Guardar cambios'
                  : 'Crear producto'}
            </button>
          </footer>
        </form>
      </aside>
    </div>
  )
}
