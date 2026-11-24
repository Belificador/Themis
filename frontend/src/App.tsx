import { useEffect, useRef, useState } from 'react'
import logoMark from './assets/logo-mark.png'
import { Inventory } from './components/Inventory'
import { Notifications } from './components/Notifications'
import { Overview } from './components/Overview'
import { ProductDrawer } from './components/ProductDrawer'
import { SaleDrawer } from './components/SaleDrawer'
import { Sales } from './components/Sales'
import { InstallButton } from './components/InstallButton'
import { Icon, type IconName } from './icons'
import type { DashboardRow, Product } from './types'

type Tab = 'overview' | 'inventory' | 'sales' | 'notifications'
type Theme = 'light' | 'dark'

const TITLES: Record<Tab, { title: string; subtitle: string }> = {
  overview: {
    title: 'Resumen',
    subtitle: 'La salud de tu inventario y tus ventas de un vistazo.',
  },
  inventory: {
    title: 'Inventario',
    subtitle: 'Precios, stock y disponibilidad de cada producto.',
  },
  sales: {
    title: 'Ventas',
    subtitle: 'Registra cada venta y descuenta el stock automáticamente.',
  },
  notifications: {
    title: 'Alertas',
    subtitle: 'Avisos de stock enviados a Telegram y WhatsApp.',
  },
}

const NAV: { id: Tab; label: string; icon: IconName }[] = [
  { id: 'overview', label: 'Resumen', icon: 'overview' },
  { id: 'inventory', label: 'Inventario', icon: 'inventory' },
  { id: 'sales', label: 'Ventas', icon: 'sales' },
  { id: 'notifications', label: 'Alertas', icon: 'bell' },
]

function initialTheme(): Theme {
  const stored = localStorage.getItem('themis-theme')
  return stored === 'dark' ? 'dark' : 'light'
}

function newIdempotencyKey(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID()
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`
}

export default function App() {
  const [tab, setTab] = useState<Tab>('overview')
  const [theme, setTheme] = useState<Theme>(initialTheme)
  const [refreshKey, setRefreshKey] = useState(0)
  const [saleOpen, setSaleOpen] = useState(false)
  const [saleInitial, setSaleInitial] = useState<DashboardRow | null>(null)
  const [saleSession, setSaleSession] = useState(0)
  const [productOpen, setProductOpen] = useState(false)
  const [editingProduct, setEditingProduct] = useState<Product | null>(null)
  const [toast, setToast] = useState<string | null>(null)
  const toastTimer = useRef<number | null>(null)

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    localStorage.setItem('themis-theme', theme)
  }, [theme])

  useEffect(() => {
    return () => {
      if (toastTimer.current) window.clearTimeout(toastTimer.current)
    }
  }, [])

  const bump = () => setRefreshKey((value) => value + 1)

  const notify = (message: string) => {
    setToast(message)
    if (toastTimer.current) window.clearTimeout(toastTimer.current)
    toastTimer.current = window.setTimeout(() => setToast(null), 3200)
  }

  const openSale = (row: DashboardRow | null = null) => {
    setSaleInitial(row)
    setSaleSession((value) => value + 1)
    setSaleOpen(true)
  }

  const openProduct = (product: Product | null = null) => {
    setEditingProduct(product)
    setProductOpen(true)
  }

  const page = TITLES[tab]

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-lockup">
          <span className="brand-emblem-wrap">
            <img src={logoMark} alt="" className="brand-emblem" />
          </span>
          <span className="brand-copy">
            <strong>Themis</strong>
            <span>Inventario & ventas</span>
          </span>
        </div>

        <nav className="side-nav" aria-label="Navegación principal">
          {NAV.map((item) => (
            <button
              key={item.id}
              className={tab === item.id ? 'nav-item active' : 'nav-item'}
              onClick={() => setTab(item.id)}
            >
              <Icon name={item.icon} />
              <span>{item.label}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-card">
          <Icon name="alert" />
          <div>
            <strong>Stock bajo</strong>
            <p>Las alertas se envían solas al cruzar el umbral.</p>
          </div>
        </div>

        <div className="sidebar-footer">
          <span className="status-dot" />
          <span>catalog · inventory · sales</span>
        </div>
      </aside>

      <div className="main-area">
        <header className="topbar">
          <div className="topbar-title">
            <span className="eyebrow">Themis</span>
            <h1>{page.title}</h1>
            <p>{page.subtitle}</p>
          </div>
          <div className="topbar-actions">
            <button
              className="icon-btn theme-toggle"
              onClick={() =>
                setTheme((value) => (value === 'light' ? 'dark' : 'light'))
              }
              aria-label={
                theme === 'light' ? 'Activar tema oscuro' : 'Activar tema claro'
              }
              title={
                theme === 'light' ? 'Activar tema oscuro' : 'Activar tema claro'
              }
            >
              <Icon name={theme === 'light' ? 'moon' : 'sun'} />
            </button>
            <button
              className="btn btn-ghost"
              onClick={() => openProduct(null)}
            >
              <Icon name="plus" />
              <span className="btn-label">Producto</span>
            </button>
            <button className="btn btn-primary" onClick={() => openSale()}>
              <Icon name="receipt" />
              <span className="btn-label">Nueva venta</span>
            </button>
            <InstallButton />
          </div>
        </header>

        <main className="page">
          {tab === 'overview' && (
            <Overview
              refreshKey={refreshKey}
              onNavigate={setTab}
              onSell={(row) => openSale(row)}
              onNewSale={() => openSale()}
              onNewProduct={() => openProduct(null)}
            />
          )}
          {tab === 'inventory' && (
            <Inventory
              refreshKey={refreshKey}
              onChanged={bump}
              onSell={(row) => openSale(row)}
              onEdit={(product) => openProduct(product)}
              onNewProduct={() => openProduct(null)}
              onToast={notify}
            />
          )}
          {tab === 'sales' && (
            <Sales
              refreshKey={refreshKey}
              onChanged={bump}
              onNewSale={() => openSale()}
            />
          )}
          {tab === 'notifications' && <Notifications />}
        </main>
      </div>

      <nav className="mobile-nav" aria-label="Navegación móvil">
        {NAV.map((item) => (
          <button
            key={item.id}
            className={tab === item.id ? 'active' : ''}
            onClick={() => setTab(item.id)}
          >
            <Icon name={item.icon} size={20} />
            <span>{item.label}</span>
          </button>
        ))}
      </nav>

      {saleOpen && (
        <SaleDrawer
          key={saleSession}
          initialRow={saleInitial}
          idempotencyKey={newIdempotencyKey()}
          onClose={() => setSaleOpen(false)}
          onDone={() => {
            bump()
            notify('Venta registrada y stock actualizado.')
          }}
        />
      )}

      {productOpen && (
        <ProductDrawer
          product={editingProduct}
          onClose={() => setProductOpen(false)}
          onDone={(message) => {
            bump()
            setProductOpen(false)
            notify(message)
          }}
        />
      )}

      {toast && (
        <div className="toast" role="status">
          <Icon name="check" />
          <span>{toast}</span>
        </div>
      )}
    </div>
  )
}
