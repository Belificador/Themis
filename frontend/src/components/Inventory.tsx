import { useEffect, useMemo, useState } from 'react'
import { api } from '../api'
import { money, productCost, productPrice, stockStatus } from '../format'
import { Icon } from '../icons'
import type {
  Category,
  Currency,
  DashboardResponse,
  DashboardRow,
  Product,
} from '../types'
import { productImageUrl } from '../media'
import { StockDrawer, type StockMode } from './StockDrawer'
import { CategoryBadge, EmptyState, KpiCard } from './ui'

const CATEGORY_FILTERS: { id: 'all' | Category; label: string }[] = [
  { id: 'all', label: 'Todos' },
  { id: 'phone', label: 'Teléfonos' },
  { id: 'tablet', label: 'Tablets' },
  { id: 'accessory', label: 'Accesorios' },
]

type StatusFilter = 'all' | 'low' | 'out'

export function Inventory({
  refreshKey,
  currency,
  onChanged,
  onSell,
  onEdit,
  onNewProduct,
  onToast,
}: {
  refreshKey: number
  currency: Currency
  onChanged: () => void
  onSell: (row: DashboardRow) => void
  onEdit: (product: Product) => void
  onNewProduct: () => void
  onToast: (message: string) => void
}) {
  const [data, setData] = useState<DashboardResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState<'all' | Category>('all')
  const [status, setStatus] = useState<StatusFilter>('all')
  const [stockTarget, setStockTarget] = useState<{
    row: DashboardRow
    mode: StockMode
  } | null>(null)

  useEffect(() => {
    let active = true
    setLoading(true)
    api
      .dashboard()
      .then((response) => {
        if (!active) return
        setData(response)
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

  const rows = useMemo(() => {
    const query = search.trim().toLowerCase()
    return (data?.products ?? []).filter((row) => {
      if (category !== 'all' && row.category !== category) return false
      if (status === 'low' && !row.low_stock) return false
      if (status === 'out' && row.quantity !== 0) return false
      if (!query) return true
      return [row.product_name, row.sku, row.brand, row.model, row.color]
        .join(' ')
        .toLowerCase()
        .includes(query)
    })
  }, [data, search, category, status])

  const totals =
    data?.totals.find((entry) => entry.currency === currency) ?? data?.totals[0]
  const otherCurrency: Currency = currency === 'EUR' ? 'USD' : 'EUR'
  const outOfStock = (data?.products ?? []).filter(
    (row) => row.stock_synced && row.quantity === 0,
  ).length
  const potentialMargin = (totals?.retail_value ?? 0) - (totals?.cost_value ?? 0)

  return (
    <div className="stack">
      {error && (
        <div className="alert alert-error">
          <Icon name="alert" />
          <span>{error}</span>
        </div>
      )}

      <section className="kpi-grid kpi-grid-4">
        <KpiCard
          label="Valor de venta"
          value={money(totals?.retail_value ?? 0, currency)}
          detail={`${data?.total_units ?? 0} unidades`}
          tone="accent"
        />
        <KpiCard
          label="Valor al costo"
          value={money(totals?.cost_value ?? 0, currency)}
          detail={`Margen potencial ${money(potentialMargin, currency)}`}
        />
        <KpiCard
          label="Bajo stock"
          value={data?.low_stock_count ?? 0}
          detail={`${outOfStock} sin stock`}
          tone="warn"
        />
        <KpiCard
          label="Catálogo"
          value={data?.count ?? 0}
          detail="Productos activos"
        />
      </section>

      <section className="panel">
        <div className="panel-head">
          <div>
            <h2>Catálogo</h2>
            <p className="muted">
              Pulsa el stock para fijarlo a cualquier valor, incluido 0.
            </p>
          </div>
          <button className="btn btn-primary" onClick={onNewProduct}>
            <Icon name="plus" />
            Nuevo producto
          </button>
        </div>

        <div className="toolbar toolbar-wrap">
          <label className="search-box">
            <Icon name="search" size={16} />
            <input
              placeholder="Buscar por marca, modelo, SKU o color…"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </label>
          <div className="chip-row">
            {CATEGORY_FILTERS.map((entry) => (
              <button
                key={entry.id}
                className={category === entry.id ? 'chip active' : 'chip'}
                onClick={() => setCategory(entry.id)}
              >
                {entry.label}
              </button>
            ))}
          </div>
          <select
            className="select"
            value={status}
            onChange={(event) => setStatus(event.target.value as StatusFilter)}
          >
            <option value="all">Todo el stock</option>
            <option value="low">Bajo stock</option>
            <option value="out">Sin stock</option>
          </select>
        </div>

        {loading && !data ? (
          <div className="loading-state">Cargando inventario…</div>
        ) : rows.length === 0 ? (
          <EmptyState
            title="No hay productos que coincidan"
            detail="Prueba con otra búsqueda o cambia los filtros."
          />
        ) : (
          <div className="table-wrap inventory-table">
            <table className="table">
              <thead>
                <tr>
                  <th>Producto</th>
                  <th>Categoría</th>
                  <th className="right">Costo</th>
                  <th className="right">PVP</th>
                  <th className="right">Stock</th>
                  <th className="right">Valor</th>
                  <th>Estado</th>
                  <th className="right">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => {
                  const statusInfo = stockStatus(
                    row.quantity,
                    row.threshold,
                    row.stock_synced,
                  )
                  return (
                    <tr key={row.id}>
                      <td>
                        <div className="product-cell product-cell-media">
                          {productImageUrl(row) ? (
                            <img
                              className="product-thumb"
                              src={productImageUrl(row) ?? undefined}
                              alt=""
                              loading="lazy"
                            />
                          ) : (
                            <span className="product-thumb product-thumb-empty">
                              <Icon name="box" size={17} />
                            </span>
                          )}
                          <div>
                            <strong>{row.product_name}</strong>
                            <span className="muted small">
                              {row.sku}
                              {row.ram_gb > 0 ? ` · ${row.ram_gb} GB RAM` : ''}
                              {row.storage_gb > 0
                                ? ` · ${row.storage_gb} GB`
                                : ''}
                            </span>
                          </div>
                        </div>
                      </td>
                      <td>
                        <CategoryBadge category={row.category} />
                      </td>
                      <td className="right small muted">
                        {money(productCost(row, currency), currency)}
                      </td>
                      <td className="right strong">
                        {money(productPrice(row, currency), currency)}
                        <span className="price-sub">
                          {money(productPrice(row, otherCurrency), otherCurrency)}
                        </span>
                      </td>
                      <td className="right">
                        <button
                          className={`stock-pill stock-${statusInfo.tone}`}
                          onClick={() =>
                            setStockTarget({ row, mode: 'set' })
                          }
                          title="Fijar stock"
                        >
                          {row.stock_synced ? row.quantity : '—'}
                        </button>
                      </td>
                      <td className="right small">
                        {money(
                          productPrice(row, currency) * row.quantity,
                          currency,
                        )}
                      </td>
                      <td>
                        <span className={`badge badge-${statusInfo.tone}`}>
                          {statusInfo.label}
                        </span>
                      </td>
                      <td>
                        <div className="row-actions">
                          <button
                            className="btn btn-ghost btn-sm"
                            onClick={() => onSell(row)}
                            disabled={!row.stock_synced || row.quantity === 0}
                          >
                            Vender
                          </button>
                          <button
                            className="icon-btn small"
                            onClick={() => setStockTarget({ row, mode: 'set' })}
                            title="Stock e historial"
                            aria-label="Stock e historial"
                          >
                            <Icon name="box" size={15} />
                          </button>
                          <button
                            className="icon-btn small"
                            onClick={() => onEdit(row)}
                            title="Editar producto"
                            aria-label="Editar producto"
                          >
                            <Icon name="edit" size={15} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {stockTarget && (
        <StockDrawer
          row={stockTarget.row}
          currency={currency}
          mode={stockTarget.mode}
          onClose={() => setStockTarget(null)}
          onDone={(message) => {
            setStockTarget(null)
            onChanged()
            onToast(message)
          }}
        />
      )}
    </div>
  )
}
