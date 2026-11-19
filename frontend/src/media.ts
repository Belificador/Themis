import type { Sale } from './types'

export function productImageUrl(
  product: { id: string; image_updated_at: string | null },
): string | null {
  if (!product.image_updated_at) return null
  const version = encodeURIComponent(product.image_updated_at)
  return `/api/catalog/products/${product.id}/image?v=${version}`
}
