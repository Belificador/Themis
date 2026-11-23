import { useCallback, useEffect, useRef, useState } from 'react'
import { Icon } from '../icons'

export function InstallButton() {
  const [canInstall, setCanInstall] = useState(false)
  const deferred = useRef<PromptEvent | null>(null)

  const install = useCallback(async () => {
    if (!deferred.current) return
    deferred.current.prompt()
    const { outcome } = await deferred.current.userChoice
    deferred.current = null
    if (outcome === 'accepted') setCanInstall(false)
  }, [])

  useEffect(() => {
    if (window.matchMedia('(display-mode: standalone)').matches) {
      setCanInstall(false)
      return
    }

    const handler = (e: Event) => {
      e.preventDefault()
      deferred.current = e as unknown as PromptEvent
      setCanInstall(true)
    }

    window.addEventListener('beforeinstallprompt', handler)
    return () => window.removeEventListener('beforeinstallprompt', handler)
  }, [])

  if (!canInstall) return null

  return (
    <button
      className="btn btn-ghost install-btn"
      onClick={install}
      title="Instalar Themis como app"
      aria-label="Instalar Themis como app"
    >
      <Icon name="download" />
      <span className="btn-label">Instalar app</span>
    </button>
  )
}

interface PromptEvent {
  prompt: () => void
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>
}
