import type { ReactNode } from 'react'
import { categoryLabel, money } from '../format'
import type { Category } from '../types'

export function KpiCard({
  label,
  value,
  detail,
  tone = 'default',
}: {
  label: string
  value: ReactNode
  detail?: ReactNode
  tone?: 'default' | 'accent' | 'warn' | 'danger' | 'success'
}) {
  return (
    <div className={`kpi kpi-${tone}`}>
      <span className="kpi-label">{label}</span>
      <span className="kpi-value">{value}</span>
      {detail && <span className="kpi-detail">{detail}</span>}
    </div>
  )
}

export function CategoryBadge({ category }: { category: Category | string }) {
  return (
    <span className={`category-badge category-${category}`}>
      {categoryLabel(category)}
    </span>
  )
}

export function Money({
  value,
  currency,
  className,
}: {
  value: number | string
  currency?: string
  className?: string
}) {
  return <span className={className}>{money(value, currency)}</span>
}

export function EmptyState({
  title,
  detail,
  action,
}: {
  title: string
  detail?: string
  action?: ReactNode
}) {
  return (
    <div className="empty-state">
      <strong>{title}</strong>
      {detail && <p>{detail}</p>}
      {action}
    </div>
  )
}
