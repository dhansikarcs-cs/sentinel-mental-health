import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import RingConnect from '../components/RingConnect'
import RingVitalsCard from '../components/RingVitalsCard'

/**
 * Shared wearable space for BOTH patients and psychologists.
 *
 * A psychologist has their OWN ring and their OWN readings — this page never
 * shows another person's data. All values come from /patients/me/wellness for
 * the logged-in account; unmeasured signals stay dashes, nothing is invented.
 */
export default function WearablesPage() {
  const [wellness, setWellness] = useState<any>(null)

  const refresh = useCallback(() => {
    api.getWellness().then(setWellness).catch(() => {})
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  return (
    <div className="animate-fade-in space-y-4">
      <h2>💍 My Wearables</h2>
      <div style={{ fontSize: '0.75rem', color: 'var(--muted)', lineHeight: 1.6 }}>
        These are your own ring readings. A cloud server has no Bluetooth, so the connection happens
        in your browser — the ring must be nearby and you click Connect once a day. The ring keeps
        its own history, so closing the browser never loses a reading.
      </div>

      <RingConnect onSynced={refresh} />
      <RingVitalsCard data={wellness} />
    </div>
  )
}
