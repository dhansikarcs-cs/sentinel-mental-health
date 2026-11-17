import { formatDateTime } from '../constants'

/**
 * Always-visible wearable vitals space.
 *
 * A dash means that signal was NOT measured — nothing is estimated or
 * simulated. When there are no readings at all the card still renders with
 * dashes and a clear "connect your ring" message, so an empty account never
 * looks like broken UI. `lastSynced` / `syncDue` come from the server and are
 * based on real stored rows only.
 */

export interface RingVitalsData {
  ring: {
    bpm: number | null
    spo2: number | null
    hrv: number | null
    temperature: number | null
    stress: number | null
    sleep: number | null
    device_id?: string
    logged_at?: string
  } | null
  last_synced?: string | null
  sync_due?: boolean
  reading_count?: number
}

export function relativeTime(ts?: string | null): string {
  if (!ts) return 'never'
  const then = new Date(ts).getTime()
  if (Number.isNaN(then)) return 'unknown'
  const mins = Math.max(0, Math.floor((Date.now() - then) / 60000))
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins} min ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs} h ago`
  const days = Math.floor(hrs / 24)
  return `${days} day${days === 1 ? '' : 's'} ago`
}

export default function RingVitalsCard({
  data,
  title = '💍 Wearable Vitals',
  subtitle,
}: {
  data: RingVitalsData | null
  title?: string
  subtitle?: string
}) {
  const ring = data?.ring ?? null
  const hasData = ring !== null
  const syncDue = data?.sync_due ?? true
  const lastSynced = data?.last_synced ?? null

  const metrics: Array<[string, number | null, string]> = [
    ['Heart rate', ring?.bpm ?? null, 'bpm'],
    ['SpO₂', ring?.spo2 ?? null, '%'],
    ['HRV', ring?.hrv ?? null, 'ms'],
    ['Temperature', ring?.temperature ?? null, '°C'],
    ['Stress', ring?.stress ?? null, ''],
    ['Sleep', ring?.sleep ?? null, 'h'],
  ]

  return (
    <div className="card" style={{ padding: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', flexWrap: 'wrap', gap: '8px' }}>
        <div style={{ fontSize: '0.8125rem', color: 'var(--secondary)', fontWeight: 600 }}>{title}</div>
        <div style={{ fontSize: '0.65rem', color: 'var(--muted)' }}>
          {subtitle ?? (hasData ? `${ring?.device_id || 'wearable'} · ${formatDateTime(ring?.logged_at)}` : 'no device linked yet')}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(96px, 1fr))', gap: '12px', marginTop: '14px' }}>
        {metrics.map(([label, value, unit]) => (
          <div key={label} className="metric-card" style={{ textAlign: 'center', padding: '12px' }}>
            <div style={{ color: 'var(--secondary)', fontSize: '0.7rem' }}>{label}</div>
            <div style={{ color: 'var(--heading)', fontSize: '1.35rem', fontWeight: 700 }}>
              {value === null || value === undefined ? '—' : value}
              {value !== null && value !== undefined && unit && (
                <span style={{ fontSize: '0.65rem', fontWeight: 400, marginLeft: '3px' }}>{unit}</span>
              )}
            </div>
          </div>
        ))}
      </div>

      <div style={{ marginTop: '10px', fontSize: '0.7rem', lineHeight: 1.6 }}>
        <div style={{ color: syncDue ? 'var(--warn)' : 'var(--ok)', fontWeight: 600 }}>
          {hasData ? '🟢 Ring linked' : '🔴 No readings yet'} · Last synced: {relativeTime(lastSynced)}
          {syncDue && ' · 🟡 Sync due today'}
        </div>
        {!hasData && (
          <div style={{ color: 'var(--muted)', marginTop: '2px' }}>
            Connect your ring to pull the readings it has stored. Until then every signal shows a dash — nothing is estimated.
          </div>
        )}
        <div style={{ color: 'var(--muted)', marginTop: '6px', fontSize: '0.65rem' }}>
          Recorded from a physical wearable. A dash means that signal was not measured — nothing is estimated or simulated.
          These readings assist monitoring; they are not a clinical assessment.
        </div>
      </div>
    </div>
  )
}
