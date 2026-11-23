import type { Sale } from './types'
import { apiUrl } from './config'

export function productImageUrl(
  product: { id: string; image_updated_at: string | null },
): string | null {
  if (!product.image_updated_at) return null
  const version = encodeURIComponent(product.image_updated_at)
  return apiUrl(`/api/catalog/products/${product.id}/image?v=${version}`)
}
