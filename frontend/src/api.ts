import type {
  Currency,
  DashboardResponse,
  Movement,
  NotificationLog,
  NotificationStats,
  Product,
  ProductInput,
  Sale,
  SaleInput,
  SalesSummary,
  TestResult,
} from './types'

async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  if (options.body && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }
  const response = await fetch(url, { ...options, headers })
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`
    try {
      const body = await response.json()
      if (body && typeof body.detail === 'string') {
        detail = body.detail
      } else if (body) {
        detail = JSON.stringify(body)
      }
    } catch {
      // keep default detail
    }
    throw new Error(detail)
  }
  if (response.status === 204) {
    return undefined as T
  }
  return (await response.json()) as T
}

export const api = {
  dashboard: () => request<DashboardResponse>('/api/dashboard'),
  createProduct: (payload: ProductInput) =>
    request<Product>('/api/catalog/products', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateProduct: (productId: string, payload: Partial<ProductInput>) =>
    request<Product>(`/api/catalog/products/${productId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  uploadProductImage: (productId: string, file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request<Product>(`/api/catalog/products/${productId}/image`, {
      method: 'POST',
      body: form,
    })
  },
  deleteProductImage: (productId: string) =>
    request<void>(`/api/catalog/products/${productId}/image`, {
      method: 'DELETE',
    }),
  addEntry: (productId: string, quantity: number, note: string) =>
    request(`/api/inventory/stock/${productId}/entries`, {
      method: 'POST',
      body: JSON.stringify({ quantity, note: note || null }),
    }),
  addExit: (productId: string, quantity: number, note: string) =>
    request(`/api/inventory/stock/${productId}/exits`, {
      method: 'POST',
      body: JSON.stringify({ quantity, note: note || null }),
    }),
  adjust: (productId: string, quantity: number, note: string) =>
    request(`/api/inventory/stock/${productId}/adjustments`, {
      method: 'POST',
      body: JSON.stringify({ quantity, note: note || null }),
    }),
  movements: (productId: string) =>
    request<Movement[]>(`/api/inventory/stock/${productId}/movements`),
  notifications: (limit = 100) =>
    request<NotificationLog[]>(`/api/notifications?limit=${limit}`),
  notificationStats: () =>
    request<NotificationStats>('/api/notifications/stats'),
  testAlert: () =>
    request<TestResult>('/api/notifications/test', {
      method: 'POST',
      body: JSON.stringify({ channel: 'all' }),
    }),
  sales: (limit = 100) => request<Sale[]>(`/api/sales?limit=${limit}`),
  sale: (saleId: string) => request<Sale>(`/api/sales/${saleId}`),
  salesSummary: (currency: Currency = 'EUR') =>
    request<SalesSummary>(`/api/sales/summary?currency=${currency}`),
  createSale: (payload: SaleInput) =>
    request<Sale>('/api/sales', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  uploadInvoice: (saleId: string, file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request<Sale>(`/api/sales/${saleId}/invoice`, {
      method: 'POST',
      body: form,
    })
  },
  deleteInvoice: (saleId: string) =>
    request<void>(`/api/sales/${saleId}/invoice`, {
      method: 'DELETE',
    }),
  invoiceUrl: (saleId: string) =>
    request<{ url: string }>(`/api/sales/${saleId}/invoice-url`),
}
