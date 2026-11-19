import type { Sale } from './types'

export function productImageUrl(
  product: { id: string; image_updated_at: string | null },
): string | null {
  if (!product.image_updated_at) return null
  const version = encodeURIComponent(product.image_updated_at)
  return `/api/catalog/products/${product.id}/image?v=${version}`
}

export function invoiceUrl(
  sale: Pick<Sale, 'id' | 'invoice_uploaded_at'>,
  download = false,
): string | null {
  if (!sale.invoice_uploaded_at) return null
  const version = encodeURIComponent(sale.invoice_uploaded_at)
  return `/api/sales/${sale.id}/invoice?${download ? 'download=1&' : ''}v=${version}`
}
