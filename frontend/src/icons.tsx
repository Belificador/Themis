import type { ReactNode, SVGProps } from 'react'

export type IconName =
  | 'overview'
  | 'inventory'
  | 'sales'
  | 'bell'
  | 'plus'
  | 'sun'
  | 'moon'
  | 'search'
  | 'more'
  | 'close'
  | 'edit'
  | 'history'
  | 'arrowDown'
  | 'arrowUp'
  | 'check'
  | 'alert'
  | 'box'
  | 'receipt'
  | 'chevronDown'
  | 'download'
  | 'logout'
  | 'user'
  | 'key'
  | 'eye'
  | 'eye-off'
  | 'refresh'

const PATHS: Record<IconName, ReactNode> = {
  overview: (
    <>
      <rect x="3" y="3" width="7" height="7" rx="1.5" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" />
    </>
  ),
  inventory: (
    <>
      <path d="M21 8.5 12 3 3 8.5v7L12 21l9-5.5z" />
      <path d="M3.3 8.5 12 13l8.7-4.5" />
      <path d="M12 21v-8" />
    </>
  ),
  sales: (
    <>
      <path d="M6 3h9l3 3v15H6z" />
      <path d="M15 3v3h3" />
      <path d="M9 11h6M9 15h6" />
    </>
  ),
  bell: (
    <>
      <path d="M18 8a6 6 0 1 0-12 0c0 6-2 7-2 7h16s-2-1-2-7" />
      <path d="M10 20a2 2 0 0 0 4 0" />
    </>
  ),
  plus: <path d="M12 5v14M5 12h14" />,
  sun: (
    <>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
    </>
  ),
  moon: <path d="M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5z" />,
  search: (
    <>
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3.5-3.5" />
    </>
  ),
  more: (
    <>
      <circle cx="5" cy="12" r="1.2" fill="currentColor" stroke="none" />
      <circle cx="12" cy="12" r="1.2" fill="currentColor" stroke="none" />
      <circle cx="19" cy="12" r="1.2" fill="currentColor" stroke="none" />
    </>
  ),
  close: <path d="M6 6l12 12M18 6 6 18" />,
  edit: (
    <>
      <path d="M12 20h9" />
      <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4z" />
    </>
  ),
  history: (
    <>
      <path d="M3 12a9 9 0 1 0 3-6.7L3 8" />
      <path d="M3 3v5h5" />
      <path d="M12 7v5l3 2" />
    </>
  ),
  arrowDown: <path d="M12 4v14m0 0 5-5m-5 5-5-5" />,
  arrowUp: <path d="M12 20V6m0 0 5 5m-5 5-5 5" />,
  check: <path d="m4 12 5 5L20 6" />,
  alert: (
    <>
      <path d="M12 3 2.5 20h19z" />
      <path d="M12 9v5M12 17h.01" />
    </>
  ),
  box: (
    <>
      <path d="M21 8.5 12 3 3 8.5v7L12 21l9-5.5z" />
      <path d="M3.3 8.5 12 13l8.7-4.5M12 21v-8" />
    </>
  ),
  receipt: (
    <>
      <path d="M5 3h14v18l-3-2-2 2-2-2-2 2-2-2-3 2z" />
      <path d="M9 8h6M9 12h6" />
    </>
  ),
  chevronDown: <path d="m6 9 6 6 6-6" />,
  download: (
    <>
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="7 10 12 15 17 10" />
      <line x1="12" y1="15" x2="12" y2="3" />
    </>
  ),
  logout: (
    <>
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <polyline points="16 17 21 12 16 7" />
      <line x1="21" y1="12" x2="9" y2="12" />
    </>
  ),
  user: (
    <>
      <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </>
  ),
  key: (
    <>
      <path d="M24.75 9.59a18.48 18.48 0 0 0-3.96-5.57 18.48 18.48 0 0 0-5.57-3.96c-2.66-2.66-6.79-2.66-9.46 0s-2.66 6.79 0 9.46a17.4 17.4 0 0 0-2.16 5.84l-1.64-2.31a4 4 0 0 1-.37-1.42l-.01-.16a4 4 0 0 1 .37-1.42l2.17-2.17a4 4 0 0 1 5.66 0l1.17 1.17 1.17-1.17a4 4 0 0 1 5.66 0l1.17 1.17 1.17-1.17a4 4 0 0 1 5.66 0l1.17 1.17a18.48 18.48 0 0 0 5.84-2.16c2.66-2.66 2.66-6.79 0-9.46Z" />
    </>
  ),
  eye: (
    <>
      <path d="M1 12s4-8 11-8 11 8-4 8-11 8-11-8Z" />
      <circle cx="12" cy="12" r="3" />
    </>
  ),
  "eye-off": (
    <>
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.16M2.41 2.41A18.45 18.45 0 0 1 6.84 2.26c1.94-.93 4-1.44 6.19-1.44a10.07 10.07 0 0 1 5.94 1.7M12 7a3 3 0 1 0-3 3 3 3 0 0 0 3-3Z" />
      <line x1="1" y1="1" x2="23" y2="23" />
    </>
  ),
  refresh: (
    <>
      <path d="M21 4v3a10 10 0 0 1-3.42 7.32l-1.9-1.9a1 1 0 0 0-1.41 0l-2.36 2.36a1 1 0 0 0 0 1.41l1.75 1.75a10 10 0 0 1-3.86 5v0a10 10 0 0 1-7.72-2.95l-1.9-1.9a1 1 0 0 0-1.41 0l-2.36 2.36a1 1 0 0 0 0 1.41l1.75 1.75a10 10 0 0 1-3.86 5v0a10 10 0 0 1-7.72-2.95l-1.9-1.9a1 1 0 0 0-1.41 0l-2.36 2.36a1 1 0 0 0 0 1.41l2.36 2.36a1 1 0 0 0 1.41 0l2.36-2.36a1 1 0 0 0 1.41-1.41l-2.36-2.36a1 1 0 0 0-1.41 0l-2.36 2.36a10 10 0 0 1 6.54 1.45l2.36-2.36a1 1 0 0 0 0-1.41l-2.36-2.36a1 1 0 0 0-1.41 0l-1.75-1.75a10 10 0 0 1 13.52-3.62l1.9 1.9a1 1 0 0 0 1.41 0l2.36-2.36a1 1 0 0 0 0-1.41l-1.95-1.95a10 10 0 0 1 5.62-2.94v0a10 10 0 0 1 5 8.58v0c0 5.52-4.48 10-10 10a10 10 0 0 1-10-10v-3Z" />
    </>
  ),
}

export function Icon({
  name,
  size = 18,
  ...props
}: { name: IconName; size?: number } & SVGProps<SVGSVGElement>) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...props}
    >
      {PATHS[name]}
    </svg>
  )
}
