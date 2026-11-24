export type Category = 'phone' | 'tablet' | 'accessory'
export type Currency = 'USD'
export type PaymentMethod = 'cash' | 'card' | 'transfer' | 'other' | 'cashea'

export interface BcvRates {
  oficial: number
  paralelo: number
  factor: number
}

export interface Product {
  id: string
  sku: string
  brand: string
  model: string
  ram_gb: number
  ram_virtual_gb: number
  storage_gb: number
  color: string
  category: Category
  price_usd: number
  price_bcv_usd: number
  price_cashea_usd: number
  camera: string | null
  threshold: number
  image_content_type: string | null
  image_size: number | null
  image_updated_at: string | null
  product_name: string
  created_at: string
  updated_at: string
}

export interface ProductInput {
  sku: string
  brand: string
  model: string
  ram_gb: number
  ram_virtual_gb: number
  storage_gb: number
  color: string
  category: Category
  price_usd: number
  price_bcv_usd: number
  price_cashea_usd: number
  camera: string | null
  threshold: number
}

export interface DashboardRow extends Product {
  quantity: number
  low_stock: boolean
  alert_state: string
  active: boolean
  stock_synced: boolean
  price_bcv_effective_usd: number
}

export interface DashboardTotals {
  currency: string
  units: number
  retail_value: number
  bcv_retail_value: number
  phone_units: number
  phone_retail_value: number
  phone_bcv_retail_value: number
}

export interface DashboardResponse {
  count: number
  low_stock_count: number
  total_units: number
  bcv_factor: number
  bcv_rates: BcvRates
  totals: DashboardTotals[]
  products: DashboardRow[]
}

export interface Movement {
  id: string
  product_id: string
  movement_type: string
  delta: number
  quantity_before: number
  quantity_after: number
  note: string | null
  correlation_id: string | null
  created_at: string
}

export interface NotificationLog {
  id: string
  event_id: string
  event_type: string
  product_id: string
  product_name: string
  channel: string
  destination: string | null
  status: string
  attempts: number
  detail: string | null
  error: string | null
  correlation_id: string | null
  created_at: string
  sent_at: string | null
}

export interface NotificationStats {
  service: string
  dedupe_window_seconds: number
  processed_events: number
  by_channel_status: { channel: string; status: string; count: number }[]
}

export interface TestResult {
  event_id: string
  results: {
    channel: string
    status: string
    attempts?: number
    detail?: string | null
    error?: string | null
  }[]
}

export interface SaleItem {
  id: string
  product_id: string
  sku: string
  product_name: string
  category: Category
    quantity: number
    unit_price: number
    line_total: number
    imei?: string
}

export interface Sale {
  id: string
  sale_number: string
  status: string
  customer_name: string | null
  vendedor: string | null
  payment_method: PaymentMethod
  note: string | null
  currency: string
  total: number
  invoice_filename: string | null
  invoice_content_type: string | null
  invoice_size: number | null
  invoice_uploaded_at: string | null
  created_at: string
  items: SaleItem[]
}

export interface SaleInputItem {
  product_id: string
  quantity: number
  unit_price?: number
}

export interface SaleInput {
  items: SaleInputItem[]
  payment_method: PaymentMethod
  currency: Currency
  customer_name?: string | null
  vendedor?: string | null
  note?: string | null
  idempotency_key?: string
}

export interface PeriodStats {
  sales: number
  units: number
  revenue: number
  average_ticket: number
}

export interface SalesSummary {
  currency: Currency
  all_time: PeriodStats
  today: PeriodStats
  month: PeriodStats
  top_products: {
    product_id: string
    product_name: string
    category: Category
    units: number
    revenue: number
  }[]
  daily: { date: string; sales: number; revenue: number }[]
}

export interface Token {
  access_token: string
  token_type: string
}

export interface UserLogin {
  username: string
  password: string
}
