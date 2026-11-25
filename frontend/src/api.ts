import type {
  BcvRates,
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
  Token,
  UserLogin,
} from './types'
import { apiUrl } from './config'

async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  const token = localStorage.getItem('themis-token')
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }
  if (options.body && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }
  const response = await fetch(apiUrl(url), { ...options, headers })
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
  login: (payload: UserLogin) =>
    request<Token>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  bcvRates: () => request<BcvRates>('/api/rates/bcv'),
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
  salesSummary: () => request<SalesSummary>('/api/sales/summary'),
  createSale: (payload: SaleInput) =>
    request<Sale>('/api/sales', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  deleteSale: (saleId: string) =>
    request<void>(`/api/sales/${saleId}`, {
      method: 'DELETE',
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
  invoiceUrl: async (saleId: string) => {
    const token = localStorage.getItem('themis-token')
    const response = await fetch(apiUrl(`/api/sales/${saleId}/invoice-url`), {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!response.ok) {
      throw new Error(`${response.status} ${response.statusText}`)
    }
    const blob = await response.blob()
    return { url: URL.createObjectURL(blob) }
  },
  exportSales: () => {
    const token = localStorage.getItem('themis-token')
    return fetch(apiUrl('/api/reports/export-sales'), {
      headers: { Authorization: `Bearer ${token}` },
    })
  },
  exportStock: () => {
    const token = localStorage.getItem('themis-token')
    return fetch(apiUrl('/api/reports/export-stock'), {
      headers: { Authorization: `Bearer ${token}` },
    })
  },
}
