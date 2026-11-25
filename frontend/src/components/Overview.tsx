import { useEffect, useState } from 'react'
import { api } from '../api'
import { categoryLabel, dateTime, money, paymentLabel, shortDate } from '../format'
import { Icon } from '../icons'
import type {
  DashboardResponse,
  DashboardRow,
  Sale,
  SalesSummary,
} from '../types'
import { CategoryBadge, EmptyState, KpiCard } from './ui'

type Tab = 'overview' | 'inventory' | 'sales' | 'notifications'

export function Overview({
  refreshKey,
  onNavigate,
  onSell,
  onNewSale,
  onNewProduct,
}: {
  refreshKey: number
  onNavigate: (tab: Tab) => void
  onSell: (row: DashboardRow) => void
  onNewSale: () => void
  onNewProduct: () => void
}) {
  const [data, setData] = useState<DashboardResponse | null>(null)
  const [summary, setSummary] = useState<SalesSummary | null>(null)
  const [recent, setRecent] = useState<Sale[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [exportingSales, setExportingSales] = useState(false)
  const [exportingStock, setExportingStock] = useState(false)

  const exportSalesExcel = async () => {
    setExportingSales(true)
    setError(null)
    try {
      const { url } = await api.exportSales()
      window.open(url, '_blank')
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setExportingSales(false)
    }
  }

  const exportStockExcel = async () => {
    setExportingStock(true)
    setError(null)
    try {
      const { url } = await api.exportStock()
      window.open(url, '_blank')
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setExportingStock(false)
    }
  }

  useEffect(() => {
    let active = true
    setLoading(true)
    Promise.all([api.dashboard(), api.salesSummary(), api.sales(5)])
      .then(([dashboard, salesSummary, sales]) => {
        if (!active) return
        setData(dashboard)
        setSummary(salesSummary)
        setRecent(sales)
        setError(null)
      })
      .catch((err: Error) => {
        if (active) setError(err.message)
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [refreshKey])

  const totals = data?.totals[0]
  const lowCount = data?.low_stock_count ?? 0
  const outOfStock = (data?.products ?? []).filter(
    (row) => row.stock_synced && row.quantity === 0,
  ).length
  const maxDaily = Math.max(
    1,
    ...(summary?.daily ?? []).map((entry) => entry.revenue),
  )

  if (loading && !data) {
    return <div className="loading-state">Cargando resumen…</div>
  }

  return (
    <div className="stack">
      {error && (
        <div className="alert alert-error">
          <Icon name="alert" />
          <span>{error}</span>
        </div>
      )}

      <section className="export-section">
        <div className="export-buttons">
          <button
            className="btn btn-primary"
            onClick={exportSalesExcel}
            disabled={exportingSales}
          >
            {exportingSales ? (
              <span className="btn-loader">
                <span className="spin" />
                Exportando ventas…
              </span>
            ) : (
              <span>
                <Icon name="download" size={16} /> Exportar ventas a Excel
              </span>
            )}
          </button>
          <button
            className="btn btn-primary"
            onClick={exportStockExcel}
            disabled={exportingStock}
          >
            {exportingStock ? (
              <span className="btn-loader">
                <span className="spin" />
                Exportando stock…
              </span>
            ) : (
              <span>
                <Icon name="download" size={16} /> Exportar inventario a Excel
              </span>
            )}
          </button>
        </div>
      </section>

      {data?.bcv_rates && (
        <div className="rates-bar">
          <span className="rates-label">Tasa BCV</span>
          <span className="rates-value">
            {data.bcv_rates.oficial ? `${data.bcv_rates.oficial.toLocaleString(
              'es-ES',
              { minimumFractionDigits: 2 },
            )} Bs` : '—'}
          </span>
          <span className="rates-divider">/</span>
          <span className="rates-value">
            {data.bcv_rates.paralelo ? `${data.bcv_rates.paralelo.toLocaleString(
              'es-ES',
              { minimumFractionDigits: 2 },
            )} Bs` : '—'}
          </span>
          <span className="rates-divider">/</span>
          <span className="rates-factor">
            factor {data.bcv_factor?.toFixed(2) ?? '—'}
          </span>
        </div>
      )}

      <section className="kpi-grid">
        <KpiCard
          label="Valor de venta"
          value={money(totals?.retail_value ?? 0)}
          detail={`${data?.total_units ?? 0} unidades en stock`}
          tone="accent"
        />
        <KpiCard
          label="Valor al precio BCV"
          value={money(totals?.bcv_retail_value ?? 0)}
          detail={`${totals?.phone_units ?? 0} teléfonos`}
        />
        <KpiCard
          label="En teléfonos"
          value={money(totals?.phone_retail_value ?? 0)}
          detail={`${totals?.phone_units ?? 0} teléfonos`}
        />
        <KpiCard
          label="Ventas hoy"
          value={money(summary?.today.revenue ?? 0)}
          detail={`${summary?.today.sales ?? 0} ventas · ticket ${money(
            summary?.today.average_ticket ?? 0,
          )}`}
          tone="success"
        />
        <KpiCard
          label="Bajo stock"
          value={data?.low_stock_count ?? 0}
          detail={`${outOfStock} productos sin stock`}
          tone={outOfStock > 0 ? 'danger' : 'warn'}
        />
      </section>

      <section className="overview-grid">
        <div className="panel chart-panel">
          <div className="panel-head">
            <div>
              <h2>Ventas de los últimos 7 días</h2>
              <p className="muted">Ingresos registrados por día.</p>
            </div>
            <button className="link-btn" onClick={() => onNavigate('sales')}>
              Ver ventas
              <Icon name="chevronDown" size={14} />
            </button>
          </div>
          <div className="bar-chart">
            {(summary?.daily ?? []).map((entry) => (
              <div className="bar-col" key={entry.date}>
                <div className="bar-track">
                  <div
                    className="bar-fill"
                    style={{
                      height: `${Math.max(
                        entry.revenue > 0 ? 8 : 2,
                        (entry.revenue / maxDaily) * 100,
                      )}%`,
                    }}
                    title={`${money(entry.revenue)} · ${entry.sales} ventas`}
                  />
                </div>
                <span className="bar-label">{shortDate(entry.date)}</span>
                <span className="bar-value">
                  {entry.revenue > 0 ? money(entry.revenue) : '—'}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="panel">
          <div className="panel-head">
            <div>
              <h2>Necesita atención</h2>
              <p className="muted">Productos en o por debajo del umbral.</p>
            </div>
            <span className={`badge ${lowCount ? 'badge-warn' : 'badge-ok'}`}>
              {data?.low_stock_count ?? 0}
            </span>
          </div>
          <div className="low-stock-list">
            {(data?.products ?? [])
              .filter((row) => row.low_stock)
              .sort((a, b) => a.quantity - b.quantity)
              .slice(0, 5)
              .map((row) => (
                <div key={row.id} className="low-row">
                  <div>
                    <strong>{row.product_name}</strong>
                    <span className="muted small">{row.sku}</span>
                  </div>
                  <span className={`badge ${
                    row.quantity === 0 ? 'badge-danger' : 'badge-warn'
                  }`}>
                    {row.quantity} uds
                  </span>
                  {row.quantity > 0 && (
                    <button
                      className="icon-btn small"
                      onClick={() => onSell(row)}
                      title="Vender"
                    >
                      <Icon name="receipt" size={15} />
                    </button>
                  )}
                </div>
              ))}
          </div>
          <div className="panel-actions">
            <button
              className="btn btn-ghost btn-sm"
              onClick={() => onNavigate('inventory')}
            >
              Gestionar inventario
            </button>
            <button className="btn btn-primary btn-sm" onClick={onNewProduct}>
              <Icon name="plus" size={15} />
              Producto
            </button>
          </div>
        </div>
      </section>

      <section className="overview-grid">
        <div className="panel">
          <div className="panel-head">
            <div>
              <h2>Últimas ventas</h2>
              <p className="muted">Movimientos más recientes del negocio.</p>
            </div>
            <button className="link-btn" onClick={() => onNavigate('sales')}>
              Historial
              <Icon name="chevronDown" size={14} />
            </button>
          </div>
          {recent.length === 0 ? (
            <EmptyState
              title="Aún no hay ventas"
              detail="Registra la primera venta para empezar a ver métricas."
              action={
                <button className="btn btn-primary btn-sm" onClick={onNewSale}>
                  Nueva venta
                </button>
              }
            />
          ) : (
            <div className="table-wrap compact">
              <table className="table">
                <thead>
                  <tr>
                    <th>Venta</th>
                    <th>Productos</th>
                    <th>Pago</th>
                    <th>Total</th>
                    <th>Fecha</th>
                  </tr>
                </thead>
                <tbody>
                  {recent.map((sale) => (
                    <tr key={sale.id}>
                      <td className="mono small">{sale.sale_number}</td>
                      <td className="small">
                        {sale.items[0]?.product_name}
                        {sale.items.length > 1
                          ? ` +${sale.items.length - 1}`
                          : ''}
                      </td>
                      <td className="small">{paymentLabel(sale.payment_method)}</td>
                      <td className="strong">{money(sale.total)}</td>
                      <td className="small muted">{dateTime(sale.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="panel">
          <div className="panel-head">
            <div>
              <h2>Más vendidos</h2>
              <p className="muted">Ranking por unidades vendidas.</p>
            </div>
          </div>
          {(summary?.top_products ?? []).length === 0 ? (
            <EmptyState
              title="Sin datos todavía"
              detail="El ranking aparecerá cuando registres ventas."
            />
          ) : (
            <ol className="ranking-list">
              {(summary?.top_products ?? []).map((product, index) => (
                <li key={product.product_id}>
                  <span className="rank-index">{index + 1}</span>
                  <div className="mini-list-main">
                    <strong>{product.product_name}</strong>
                    <span className="muted small">
                      {product.units} unidades ·{' '}
                      {money(product.revenue)}
                    </span>
                  </div>
                  <CategoryBadge category={product.category} />
                </li>
              ))}
            </ol>
          )}
        </div>
      </section>
    </div>
  )
}
