import { useEffect, useState } from 'react'

/* Shared "Advanced settings" flag (Settings → Profile page).
   Lives in localStorage so it persists per browser and syncs across
   open tabs via the `storage` event + a same-tab custom event. */

const KEY = 'sentinel-advanced-panels'
const EVT = 'sentinel-advanced-change'

export function getAdvancedPanels(): boolean {
  try { return localStorage.getItem(KEY) === '1' } catch { return false }
}

export function setAdvancedPanels(on: boolean) {
  try {
    localStorage.setItem(KEY, on ? '1' : '0')
    window.dispatchEvent(new CustomEvent(EVT))
  } catch {}
}

export function useAdvancedPanels(): boolean {
  const [on, setOn] = useState(getAdvancedPanels)
  useEffect(() => {
    const handler = () => setOn(getAdvancedPanels())
    window.addEventListener(EVT, handler)
    window.addEventListener('storage', handler)
    return () => { window.removeEventListener(EVT, handler); window.removeEventListener('storage', handler) }
  }, [])
  return on
}
