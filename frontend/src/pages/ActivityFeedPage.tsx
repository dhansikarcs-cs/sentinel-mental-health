import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { formatDateTime } from '../constants'

const ACTION_ICONS: Record<string, string> = {
  journal: '📝',
  mood: '😊',
  crisis: '🚨',
  booking: '📅',
  clinical_note: '📋',
  followup: '📋',
}

const SEVERITY_COLORS: Record<string, string> = {
  high: 'var(--danger)',
  medium: 'var(--warn)',
  info: 'var(--ok)',
}

export default function ActivityFeedPage() {
  const [events, setEvents] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [days, setDays] = useState(7)
  const [filter, setFilter] = useState('All')

  useEffect(() => {
    setLoading(true)
    api.getActivityFeed(days).then((d: any) => {
      setEvents(Array.isArray(d?.events) ? d.events : [])
    }).catch(() => {}).finally(() => setLoading(false))
  }, [days])

  const types = ['All', ...Array.from(new Set(events.map((e: any) => e.type)))]
  const shown = filter === 'All' ? events : events.filter((e: any) => e.type === filter)

  return (
    <div className="animate-fade-in">
      <div style={{ display: 'flex', gap: '8px', marginBottom: '14px', alignItems: 'center', flexWrap: 'wrap' }}>
        <span style={{ color: 'var(--muted)', fontSize: '0.8rem', fontWeight: 700 }}>Show last:</span>
        {[1, 3, 7, 14, 30].map(d => (
          <button key={d} className={`chip${days === d ? ' active' : ''}`} onClick={() => setDays(d)}>{d}d</button>
        ))}
        <div style={{ marginLeft: 'auto' }} className="chip-row">
          {types.map(t => (
            <button key={t} className={`chip${filter === t ? ' active' : ''}`} onClick={() => setFilter(t)} style={{ textTransform: 'capitalize' }}>{t}</button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="card" style={{ color: 'var(--muted)' }}>Loading…</div>
      ) : shown.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '30px' }}>
          <div style={{ fontSize: '1.8rem', marginBottom: '6px' }}>📡</div>
          <div style={{ fontWeight: 700 }}>No activity found</div>
          <div style={{ color: 'var(--muted)', fontSize: '0.8rem' }}>Try a wider time range.</div>
        </div>
      ) : (
        <div className="card" style={{ padding: '8px' }}>
          {shown.map((e: any, i: number) => (
            <div key={i} style={{
              display: 'flex', alignItems: 'center', gap: '12px',
              padding: '10px 14px', borderRadius: '12px',
              borderBottom: i < shown.length - 1 ? '1px solid var(--border-soft)' : 'none',
            }}>
              <span style={{ fontSize: '1.05rem' }}>{ACTION_ICONS[e.type] || '💬'}</span>
              <span className="dot" style={{ background: SEVERITY_COLORS[e.severity] || 'var(--muted)' }} />
              <span style={{ color: 'var(--faint)', fontSize: '0.68rem', minWidth: '130px', fontWeight: 600 }}>
                {formatDateTime(e.timestamp)}
              </span>
              <span style={{ color: 'var(--accent)', fontSize: '0.76rem', fontWeight: 800, minWidth: '80px' }}>
                {e.patient}
              </span>
              <span style={{ color: 'var(--soft)', fontSize: '0.78rem', flex: 1, minWidth: 0 }}>
                {e.summary || e.type}
              </span>
            </div>
          ))}
          <div style={{ color: 'var(--faint)', fontSize: '0.6875rem', textAlign: 'center', padding: '12px' }}>
            Showing {shown.length} of {events.length} events
          </div>
        </div>
      )}
    </div>
  )
}
