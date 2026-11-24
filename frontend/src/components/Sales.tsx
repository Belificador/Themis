import { useEffect, useState } from 'react'
import { api } from '../api'
import {
  dateTime,
  money,
  paymentLabel,
  shortDate,
  statusLabel,
} from '../format'
import { Icon } from '../icons'
import type { Sale, SalesSummary } from '../types'
import { SaleDetailDrawer } from './SaleDetailDrawer'
import { CategoryBadge, EmptyState, KpiCard } from './ui'

export function Sales({
  refreshKey,
  onChanged,
  onNewSale,
}: {
  refreshKey: number
  onChanged: () => void
  onNewSale: () => void
}) {
  const [sales, setSales] = useState<Sale[]>([])
  const [summary, setSummary] = useState<SalesSummary | null>(null)
  const [detail, setDetail] = useState<Sale | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    setLoading(true)
    Promise.all([api.sales(100), api.salesSummary()])
      .then(([saleList, salesSummary]) => {
        if (!active) return
        setSales(saleList)
        setSummary(salesSummary)
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

  const maxDaily = Math.max(
    1,
    ...(summary?.daily ?? []).map((entry) => entry.revenue),
  )

  const handleDeleteSale = async (sale: Sale) => {
    if (
      !window.confirm(
        `¿Eliminar la venta ${sale.sale_number} y restaurar su stock?`,
      )
    )
      return
    setDeleteError(null)
    try {
      await api.deleteSale(sale.id)
      const updated = await api.sales(100)
      setSales(updated)
    } catch (err) {
      setDeleteError((err as Error).message)
    }
  }

  return (
    <div className="stack">
      {error && (
        <div className="alert alert-error">
          <Icon name="alert" />
          <span>{error}</span>
        </div>
      )}
      {deleteError && (
        <div className="alert alert-error">
          <Icon name="alert" />
          <span>{deleteError}</span>
        </div>
      )}

      <section className="kpi-grid kpi-grid-4">
        <KpiCard
          label="Ingresos hoy"
          value={money(summary?.today.revenue ?? 0)}
          detail={`${summary?.today.sales ?? 0} ventas · ${summary?.today.units ?? 0} unidades`}
          tone="accent"
        />
        <KpiCard
          label="Ticket medio"
          value={money(summary?.today.average_ticket ?? 0)}
          detail="Media de las ventas de hoy"
        />
        <KpiCard
          label="Ingresos del mes"
          value={money(summary?.month.revenue ?? 0)}
          detail={`${summary?.month.sales ?? 0} ventas`}
        />
      </section>

      <section className="overview-grid">
        <div className="panel chart-panel">
          <div className="panel-head">
            <div>
              <h2>Ritmo de ventas</h2>
              <p className="muted">Ingresos de los últimos 7 días.</p>
            </div>
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
              <h2>Más vendidos</h2>
              <p className="muted">Productos que más rotan.</p>
            </div>
            <button className="btn btn-primary btn-sm" onClick={onNewSale}>
              <Icon name="plus" size={15} />
              Vender
            </button>
          </div>
          {(summary?.top_products ?? []).length === 0 ? (
            <EmptyState
              title="Aún no hay ventas"
              detail="El ranking se llenará con tu primera venta."
            />
          ) : (
            <ol className="ranking-list">
              {(summary?.top_products ?? []).map((product, index) => (
                <li key={product.product_id}>
                  <span className="rank-index">{index + 1}</span>
                  <div className="mini-list-main">
                    <strong>{product.product_name}</strong>
                    <span className="muted small">
                      {product.units} uds · {money(product.revenue)}
                    </span>
                  </div>
                  <CategoryBadge category={product.category} />
                </li>
              ))}
            </ol>
          )}
        </div>
      </section>

      <section className="panel">
        <div className="panel-head">
          <div>
            <h2>Historial de ventas</h2>
            <p className="muted">
              {summary?.all_time.sales ?? 0} ventas ·{' '}
              {money(summary?.all_time.revenue ?? 0)} facturados.
            </p>
          </div>
          <button className="btn btn-primary" onClick={onNewSale}>
            <Icon name="receipt" />
            Nueva venta
          </button>
        </div>

        {loading && sales.length === 0 ? (
          <div className="loading-state">Cargando ventas…</div>
        ) : sales.length === 0 ? (
          <EmptyState
            title="Todavía no hay ventas"
            detail="Registra la primera venta para empezar a medir ingresos."
            action={
              <button className="btn btn-primary btn-sm" onClick={onNewSale}>
                Registrar venta
              </button>
            }
          />
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Venta</th>
                  <th>Fecha</th>
                  <th>Cliente</th>
                  <th>Vendedor</th>
                  <th>Artículos</th>
                  <th>Pago</th>
                  <th>IMEI</th>
                  <th>Factura</th>
                  <th className="right">Ingresos</th>
                  <th>Estado</th>
                  <th className="right">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {sales.map((sale) => (
                  <tr key={sale.id}>
                    <td className="mono small">
                      <button
                        className="link-btn mono"
                        onClick={() => setDetail(sale)}
                      >
                        {sale.sale_number}
                      </button>
                    </td>
                    <td className="small muted">
                      {dateTime(sale.created_at)}
                    </td>
                    <td className="small">
                      {sale.customer_name ?? '—'}
                    </td>
                    <td className="small">
                      {sale.vendedor ?? '—'}
                    </td>
                    <td>
                      <div className="product-cell">
                        <strong>
                          {sale.items[0]?.product_name ?? '—'}
                          {sale.items.length > 1
                            ? ` +${sale.items.length - 1}`
                            : ''}
                        </strong>
                        <span className="muted small">
                          {sale.items.reduce(
                            (sum, item) => sum + item.quantity,
                            0,
                          )}{' '}
                          unidades
                        </span>
                      </div>
                    </td>
                    <td className="small">{paymentLabel(sale.payment_method)}</td>
                    <td className="small muted">
                      {sale.items
                        .map((item) => item.imei)
                        .filter(Boolean)
                        .join(', ') || '—'}
                    </td>
                    <td>
                      <button
                        className="link-btn small"
                        onClick={() => setDetail(sale)}
                      >
                        {sale.invoice_uploaded_at ? 'Ver factura' : 'Adjuntar'}
                      </button>
                    </td>
                    <td className="right strong">
                      {money(sale.total)}
                    </td>
                    <td>
                      <span
                        className={`badge ${
                          sale.status === 'completed'
                            ? 'badge-ok'
                            : sale.status === 'pending'
                              ? 'badge-warn'
                              : 'badge-danger'
                        }`}
                      >
                        {statusLabel(sale.status)}
                      </span>
                    </td>
                    <td className="right">
                      <button
                        className="link-btn small text-danger"
                        onClick={() => handleDeleteSale(sale)}
                      >
                        <Icon name="close" size={14} />
                        Eliminar
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {detail && (
        <SaleDetailDrawer
          sale={detail}
          onClose={() => setDetail(null)}
          onChanged={() => onChanged()}
        />
      )}
    </div>
  )
}
