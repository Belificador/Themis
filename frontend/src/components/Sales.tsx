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
import type { Currency, Sale, SalesSummary } from '../types'
import { SaleDetailDrawer } from './SaleDetailDrawer'
import { CategoryBadge, EmptyState, KpiCard } from './ui'

export function Sales({
  refreshKey,
  currency,
  onChanged,
  onNewSale,
}: {
  refreshKey: number
  currency: Currency
  onChanged: () => void
  onNewSale: () => void
}) {
  const [sales, setSales] = useState<Sale[]>([])
  const [summary, setSummary] = useState<SalesSummary | null>(null)
  const [detail, setDetail] = useState<Sale | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    setLoading(true)
    Promise.all([api.sales(100), api.salesSummary(currency)])
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
  }, [refreshKey, currency])

  const maxDaily = Math.max(
    1,
    ...(summary?.daily ?? []).map((entry) => entry.revenue),
  )
  const marginPercent =
    summary && summary.all_time.revenue > 0
      ? Math.round((summary.all_time.margin / summary.all_time.revenue) * 100)
      : 0

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
          label="Ingresos hoy"
          value={money(summary?.today.revenue ?? 0, currency)}
          detail={`${summary?.today.sales ?? 0} ventas · ${summary?.today.units ?? 0} unidades`}
          tone="accent"
        />
        <KpiCard
          label="Ticket medio"
          value={money(summary?.today.average_ticket ?? 0, currency)}
          detail="Media de las ventas de hoy"
        />
        <KpiCard
          label="Margen del mes"
          value={money(summary?.month.margin ?? 0, currency)}
          detail={`${marginPercent}% sobre ingresos históricos`}
          tone="success"
        />
        <KpiCard
          label="Ingresos del mes"
          value={money(summary?.month.revenue ?? 0, currency)}
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
                    title={`${money(entry.revenue, currency)} · ${entry.sales} ventas`}
                  />
                </div>
                <span className="bar-label">{shortDate(entry.date)}</span>
                <span className="bar-value">
                  {entry.revenue > 0 ? money(entry.revenue, currency) : '—'}
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
                      {product.units} uds · {money(product.revenue, currency)}
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
              {money(summary?.all_time.revenue ?? 0, currency)} facturados.
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
            detail="Registra la primera venta para empezar a medir ingresos y margen."
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
                  <th>Artículos</th>
                  <th>Pago</th>
                  <th>Moneda</th>
                  <th>Factura</th>
                  <th className="right">Ingresos</th>
                  <th className="right">Coste</th>
                  <th className="right">Margen</th>
                  <th>Estado</th>
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
                    <td>
                      <span className="badge">{sale.currency}</span>
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
                      {money(sale.total, sale.currency)}
                    </td>
                    <td className="right small muted">
                      {money(sale.cost_total, sale.currency)}
                    </td>
                    <td className="right small text-ok">
                      {money(sale.margin, sale.currency)}
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
