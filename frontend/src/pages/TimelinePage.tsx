import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { getUser } from '../stores/auth'
import { moodIcon, moodColor, formatTime } from '../constants'
import PatientSelector from '../components/PatientSelector'

const EVENT_STYLES: Record<string, { dot: string; label: string }> = {
  mood: { dot: 'var(--ok)', label: 'Mood' },
  journal: { dot: 'var(--violet)', label: 'Journal' },
  followup: { dot: 'var(--warn)', label: 'Task' },
  crisis: { dot: 'var(--danger)', label: 'Crisis' },
}

export default function TimelinePage() {
  const user = getUser()
  const [patients, setPatients] = useState<any[]>([])
  const [selectedPatient, setSelectedPatient] = useState('')
  const [days, setDays] = useState(30)
  const [metrics, setMetrics] = useState<any>(null)
  const [events, setEvents] = useState<any[]>([])
  const isPsych = user?.role === 'psychologist'

  useEffect(() => {
    if (isPsych) api.getPsychPatients().then(d => setPatients(d || [])).catch(() => {})
    else if (user?.username) { setSelectedPatient(user.username); fetchData(user.username) }
  }, [])

  useEffect(() => { if (selectedPatient) fetchData(selectedPatient) }, [selectedPatient, days])

  async function fetchData(patient: string) {
    try {
      const [m, e] = await Promise.all([
        api.getMetrics(patient),
        api.getTimeline(patient, days)
      ])
      setMetrics(m || {})
      setEvents(e?.events || e || [])
    } catch {}
  }

  const trendArrow = (t?: string) =>
    t === 'improving' || t === 'increasing' ? '↗' : t === 'declining' ? '↘' : t === 'stable' ? '→' : '—'
  const trendColor = (t?: string) =>
    t === 'improving' || t === 'increasing' ? 'var(--ok)' : t === 'declining' ? 'var(--danger)' : 'var(--warn)'

  return (
    <div className="animate-fade-in">
      {isPsych && (
        <div style={{ display: 'flex', gap: '12px', marginBottom: '18px', flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <div style={{ flex: 2, minWidth: '200px' }}>
            <label>Client</label>
            <PatientSelector patients={patients} value={selectedPatient} onChange={setSelectedPatient} placeholder="Select…" />
          </div>
          <div style={{ flex: 1, minWidth: '160px' }}>
            <label>Time range · {days} days</label>
            <input type="range" min={7} max={90} value={days} onChange={e => setDays(Number(e.target.value))} />
          </div>
        </div>
      )}

      {!selectedPatient ? (
        <div className="card" style={{ textAlign: 'center', padding: '32px' }}>
          <div style={{ fontSize: '1.8rem', marginBottom: '6px' }}>🗓</div>
          <div style={{ fontWeight: 700 }}>Select a client to view their timeline</div>
          <div style={{ color: 'var(--muted)', fontSize: '0.8rem' }}>A unified feed of moods, journals, tasks and crises.</div>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '18px', alignItems: 'start' }} className="tl-grid">
          {/* Metrics panel */}
          <div className="card-dark">
            <h3 style={{ marginBottom: '14px' }}>📊 Change metrics</h3>
            {metrics ? (
              <>
                <div style={{ marginBottom: '16px' }}>
                  <div style={{ color: '#A6AC9D', fontSize: '0.62rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Mood trend (7d vs prior)</div>
                  <div style={{ color: trendColor(metrics.mood_trend), fontSize: '1.4rem', fontWeight: 800 }}>
                    {trendArrow(metrics.mood_trend)} {metrics.mood_trend || '—'}
                  </div>
                  <div style={{ color: '#A6AC9D', fontSize: '0.72rem' }}>
                    Now {metrics.current_mood_avg ? Number(metrics.current_mood_avg).toFixed(1) : '—'}/5 · before {metrics.previous_mood_avg ? Number(metrics.previous_mood_avg).toFixed(1) : '—'}/5
                  </div>
                </div>

                <div style={{ marginBottom: '16px' }}>
                  <div style={{ color: '#A6AC9D', fontSize: '0.62rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Engagement</div>
                  <div style={{ color: trendColor(metrics.engagement_trend), fontSize: '1.4rem', fontWeight: 800 }}>
                    {trendArrow(metrics.engagement_trend)} {metrics.journal_count_7 || 0}
                  </div>
                  <div style={{ color: '#A6AC9D', fontSize: '0.72rem' }}>journals this week · {metrics.journal_count_14 || 0} in 14d</div>
                </div>

                {metrics.latest_mood && (
                  <div>
                    <div style={{ color: '#A6AC9D', fontSize: '0.62rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Latest mood</div>
                    <div style={{ fontSize: '1.7rem' }}>{moodIcon(metrics.latest_mood.label)}</div>
                    <div style={{ color: '#A6AC9D', fontSize: '0.72rem' }}>{metrics.latest_mood.label} — {formatTime(metrics.latest_mood.timestamp)}</div>
                  </div>
                )}
              </>
            ) : (
              <div style={{ color: '#A6AC9D', fontSize: '0.82rem' }}>No data available.</div>
            )}
          </div>

          {/* Event feed */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
              <h3 style={{ margin: 0 }}>📅 Event feed</h3>
              <span className="badge-theme">{events.length} events · {days}d</span>
            </div>
            {events.length === 0 ? (
              <div className="card" style={{ textAlign: 'center', color: 'var(--muted)' }}>No events in this window.</div>
            ) : (
              <div style={{ maxHeight: '560px', overflowY: 'auto', paddingRight: '6px', position: 'relative' }}>
                {/* vertical rail */}
                <div style={{ position: 'absolute', left: '17px', top: '10px', bottom: '10px', width: '2px', background: 'var(--border)' }} />
                {events.map((ev: any, i: number) => {
                  const st = EVENT_STYLES[ev.type] || { dot: 'var(--muted)', label: ev.type }
                  const d = ev.data || {}
                  return (
                    <div key={i} style={{ display: 'flex', gap: '12px', marginBottom: '8px', position: 'relative' }}>
                      <div style={{
                        width: '12px', height: '12px', minWidth: '12px', borderRadius: 999,
                        background: st.dot, border: '2.5px solid var(--surface)',
                        marginTop: '14px', zIndex: 1,
                      }} />
                      <div className="card-sm" style={{ flex: 1, borderRadius: '16px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontWeight: 700, fontSize: '0.82rem', color: 'var(--heading)' }}>
                            {ev.type === 'mood' && <>{moodIcon(d.label)} <span style={{ color: moodColor(d.label), textTransform: 'capitalize' }}>{d.label}</span> mood</>}
                            {ev.type === 'journal' && <>📝 {d.title || 'Journal entry'}</>}
                            {ev.type === 'followup' && <>{d.status === 'completed' ? '✅' : '⏳'} {d.title || 'Task'}</>}
                            {ev.type === 'crisis' && <>🚨 {(d.event || 'Crisis').toUpperCase()}</>}
                          </span>
                          <span style={{ fontSize: '0.65rem', color: 'var(--faint)', whiteSpace: 'nowrap' }}>{formatTime(ev.timestamp)}</span>
                        </div>
                        <div style={{ color: 'var(--secondary)', fontSize: '0.74rem', marginTop: '3px', lineHeight: 1.5 }}>
                          {ev.type === 'mood' && `Logged on ${d.date || ''}`}
                          {ev.type === 'journal' && (d.summary || '').slice(0, 180)}
                          {ev.type === 'followup' && (d.description || '')}
                          {ev.type === 'crisis' && (d.details || d.event || '')}
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </div>
      )}
      <style>{`@media (max-width: 960px) { .tl-grid { grid-template-columns: 1fr !important; } }`}</style>
    </div>
  )
}
