import type { Category, Currency, Product } from './types'

const CATEGORY_LABELS: Record<Category, string> = {
  phone: 'Teléfono',
  tablet: 'Tablet',
  accessory: 'Accesorio',
}

const PAYMENT_LABELS: Record<string, string> = {
  cash: 'Efectivo 💵',
  card: 'Tarjeta 💳',
  transfer: 'Transferencia 🏦',
  other: 'Otro',
  cashea: 'Cashea 📱',
}

export function categoryLabel(category: Category | string): string {
  return CATEGORY_LABELS[category as Category] ?? 'Producto'
}

export function productPrice(
  product: Pick<Product, 'price_eur' | 'price_usd'>,
  currency: Currency,
): number {
  return currency === 'USD' ? product.price_usd : product.price_eur
}

export function productCost(
  product: Pick<Product, 'cost_price_eur' | 'cost_price_usd'>,
  currency: Currency,
): number {
  return currency === 'USD' ? product.cost_price_usd : product.cost_price_eur
}

export function paymentLabel(method: string): string {
  return PAYMENT_LABELS[method] ?? method
}

export function money(value: number | string | null | undefined, currency = 'EUR'): string {
  const amount = Number(value)
  try {
    return new Intl.NumberFormat('es-ES', {
      style: 'currency',
      currency: currency || 'EUR',
      minimumFractionDigits: 2,
    }).format(Number.isFinite(amount) ? amount : 0)
  } catch {
    return `${Number.isFinite(amount) ? amount.toFixed(2) : '0.00'} ${currency}`
  }
}

export function integer(value: number | string | null | undefined): string {
  return new Intl.NumberFormat('es-ES').format(Number(value) || 0)
}

export function dateTime(value: string | null | undefined): string {
  if (!value) return '—'
  return new Date(value).toLocaleString('es-ES', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function shortDate(value: string): string {
  return new Date(value).toLocaleDateString('es-ES', {
    weekday: 'short',
  })
}

export function statusLabel(status: string): string {
  if (status === 'completed') return 'Completada'
  if (status === 'pending') return 'Procesando'
  if (status === 'failed') return 'Fallida'
  return status
}

export function stockStatus(quantity: number, threshold: number, synced = true) {
  if (!synced) return { label: 'Sincronizando', tone: 'sync' }
  if (quantity === 0) return { label: 'Sin stock', tone: 'danger' }
  if (quantity <= threshold) return { label: 'Bajo stock', tone: 'warn' }
  return { label: 'Disponible', tone: 'ok' }
}
