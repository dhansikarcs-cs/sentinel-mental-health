import { useEffect, useState } from 'react'
import { api } from '../api/client'
import AiSourceBadge from '../components/AiSourceBadge'
import { EmotionBars } from '../components/EmotionBar'
import PatientSelector, { usePatientContext } from '../components/PatientSelector'
import PrioritiesPanel from '../components/PrioritiesPanel'
import { moodIcon, formatTime, formatDate } from '../constants'
import SlotNumber from '../components/SlotNumber'
import StressSpikes from '../components/StressSpikes'

const SUB_TABS = [
  { key: 'overview', label: '🔍 Current state' },
  { key: 'raw', label: '📊 Raw data' },
]

export default function PatientInsightsPage() {
  const { patients } = usePatientContext()
  const [selected, setSelected] = useState('')
  const [overview, setOverview] = useState<any>(null)
  const [overviewLoading, setOverviewLoading] = useState(false)
  const [subTab, setSubTab] = useState('overview')

  useEffect(() => {
    if (!selected) { setOverview(null); return }
    setOverviewLoading(true)
    api.getPatientOverview(selected)
      .then(d => setOverview(d))
      .catch(() => setOverview(null))
      .finally(() => setOverviewLoading(false))
  }, [selected])

  return (
    <div className="animate-fade-in">
      <PatientSelector
        patients={patients}
        value={selected}
        onChange={setSelected}
        placeholder="-- Select client --"
        style={{ marginBottom: '16px', maxWidth: '420px' }}
      />

      {selected && (
        <div className="segmented-control">
          {SUB_TABS.map(t => (
            <button key={t.key} className={`segmented-btn${subTab === t.key ? ' active' : ''}`} onClick={() => setSubTab(t.key)}>
              {t.label}
            </button>
          ))}
        </div>
      )}

      {!selected && (
        <div className="card" style={{ textAlign: 'center', padding: '44px' }}>
          <div style={{ fontSize: '2.2rem', marginBottom: '8px' }}>🔍</div>
          <div style={{ fontWeight: 800, fontSize: '1.05rem', marginBottom: '4px' }}>Who are we looking at?</div>
          <div style={{ color: 'var(--muted)', fontSize: '0.82rem' }}>A plain-language read on how your client is doing — numbers stay in the second tab.</div>
        </div>
      )}

      {selected && subTab === 'overview' && <CurrentStateSection patient={selected} overview={overview} />}
      {selected && subTab === 'raw' && <RawDataSection patient={selected} overview={overview} />}
      {selected && (
        <div className="card" style={{ marginTop: '16px' }}>
          <StressSpikes username={selected} />
        </div>
      )}
    </div>
  )
}

function CurrentStateSection({ patient, overview }: { patient: string; overview: any }) {
  const [insights, setInsights] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [theme, setTheme] = useState<any>(null)
  const [warning, setWarning] = useState<any>(null)

  useEffect(() => {
    setLoading(true)
    api.getPlainInsights(patient)
      .then(setInsights)
      .catch(() => setInsights(null))
      .finally(() => setLoading(false))
    api.getWeeklyTheme(patient).then(setTheme).catch(() => {})
    api.getEarlyWarning(patient).then(setWarning).catch(() => {})
  }, [patient])

  const identity = overview?.patient || {}
  const alerts = overview?.alerts || []

  return (
    <>
      {identity.name && (
        <div className="lead-card dark" style={{ padding: '18px 20px', marginBottom: '14px', flexDirection: 'row', alignItems: 'center', flexWrap: 'wrap', gap: '14px' }} data-tour="patient-insights">
          <div className="avatar" style={{ background: 'var(--lime)', color: 'var(--lime-ink)' }}>
            {(identity.name || '?').split(' ').map((w: string) => w[0]).slice(0, 2).join('').toUpperCase()}
          </div>
          <div>
            <div style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--on-ink)' }}>{identity.name}</div>
            <div style={{ color: '#A6AC9D', fontSize: '0.72rem', marginTop: '2px' }}>
              @{identity.username}{identity.age ? ` · ${identity.age} yrs` : ''}{identity.occupation ? ` · ${identity.occupation}` : ''}
            </div>
          </div>
        </div>
      )}

      {alerts.length > 0 && (
        <div style={{ marginBottom: '14px' }}>
          {alerts.map((a: string, i: number) => (
            <div key={i} style={{ background: 'var(--warn-soft)', border: '1px solid color-mix(in srgb, var(--warn) 22%, transparent)', borderLeft: '3px solid var(--warn)', color: '#8A5A10', borderRadius: '14px', padding: '9px 14px', fontSize: '0.78rem', fontWeight: 600, marginBottom: '6px' }}>
              ⚠️ {a}
            </div>
          ))}
        </div>
      )}

      {warning && (
        <div className="card" style={{ marginBottom: '14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', flexWrap: 'wrap' }}>
            <h3 style={{ margin: 0 }}>🛰️ Early-warning scan</h3>
            <span className="badge-theme" style={{
              color: warning.overall === 'urgent' ? '#d6453a' : warning.overall === 'watch' ? '#b7791f' : 'var(--secondary)',
              borderColor: warning.overall === 'urgent' ? '#d6453a' : warning.overall === 'watch' ? '#b7791f' : 'var(--secondary)',
              textTransform: 'uppercase', fontWeight: 800, fontSize: '0.62rem',
            }}>{warning.overall}</span>
            {warning.source === 'ai' && <AiSourceBadge source="ai" />}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {warning.signals.map((s: any, i: number) => {
              const dot = s.level === 'urgent' ? '🔴' : s.level === 'watch' ? '🟡' : '🔵'
              return (
                <div key={i} style={{ padding: '9px 12px', borderRadius: '12px', background: 'var(--surface)', border: '1px solid var(--border)' }}>
                  <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text)' }}>{dot} {s.signal}</div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--muted)', marginTop: '2px' }}>{s.evidence}</div>
                </div>
              )
            })}
          </div>
          <div style={{ fontSize: '0.62rem', color: 'var(--muted)', marginTop: '8px' }}>{warning.disclaimer}</div>
        </div>
      )}

      {loading && (
        <div className="card" style={{ textAlign: 'center', padding: '26px', color: 'var(--muted)' }}>
          Reading through the data…
        </div>
      )}

      {theme?.theme && (
        <div className="card-sm" style={{ padding: '14px 18px', marginBottom: '12px', background: 'var(--accent-soft)', borderColor: 'color-mix(in srgb, var(--accent) 25%, transparent)', display: 'flex', alignItems: 'center', gap: '14px', flexWrap: 'wrap' }}>
          <div style={{ fontSize: '1.4rem' }}>{theme.tone === 'heavy' ? '🌧️' : theme.tone === 'positive' ? '🌤️' : '⛅'}</div>
          <div style={{ flex: 1, minWidth: '200px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
              <span style={{ color: 'var(--accent)', fontWeight: 800, fontSize: '0.62rem', textTransform: 'uppercase', letterSpacing: '0.08em' }}>This week&apos;s thread</span>
              {theme.source === 'ai' && <span className="badge-theme" style={{ fontSize: '0.58rem' }}>AI</span>}
              <span className="badge-theme" style={{ fontSize: '0.6rem' }}>{theme.entries} entries</span>
            </div>
            <div style={{ fontWeight: 800, fontSize: '0.95rem', color: 'var(--heading)', margin: '2px 0' }}>{theme.theme}</div>
            <div style={{ color: 'var(--secondary)', fontSize: '0.74rem', lineHeight: 1.5 }}>{theme.detail}</div>
          </div>
        </div>
      )}

      {!loading && insights && (
        <div className="card" style={{ padding: '24px', marginBottom: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
            <span style={{ color: 'var(--accent)', fontWeight: 800, fontSize: '0.66rem', letterSpacing: '0.08em', textTransform: 'uppercase' }}>How they&apos;re doing</span>
            {insights.source && <div style={{ marginLeft: 'auto' }}><AiSourceBadge source={insights.source} /></div>}
          </div>
          <div style={{ color: 'var(--heading)', fontSize: '1.15rem', fontWeight: 800, lineHeight: 1.45, marginBottom: '16px' }}>{insights.headline}</div>

          {(insights.insights || []).length > 0 && (
            <>
              <div style={{ height: '1px', background: 'var(--border)', marginBottom: '14px' }} />
              <div style={{ color: 'var(--accent)', fontWeight: 800, fontSize: '0.66rem', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: '8px' }}>The detail, in plain words</div>
              {insights.insights.map((text: string, i: number) => (
                <div key={i} style={{ display: 'flex', gap: '10px', marginBottom: '7px', fontSize: '0.82rem', color: 'var(--text)', lineHeight: 1.6 }}>
                  <span style={{ color: 'var(--accent)', flexShrink: 0, fontWeight: 800 }}>•</span>
                  <span>{text}</span>
                </div>
              ))}
            </>
          )}

          {insights.suggestion && (
            <>
              <div style={{ height: '1px', background: 'var(--border)', margin: '14px 0' }} />
              <div style={{ color: 'var(--accent)', fontWeight: 800, fontSize: '0.66rem', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: '6px' }}>What to do next</div>
              <div className="card-sm" style={{ background: 'var(--accent-soft)', borderColor: 'color-mix(in srgb, var(--accent) 25%, transparent)' }}>
                <div style={{ color: 'var(--text)', fontSize: '0.82rem', lineHeight: 1.6 }}>{insights.suggestion}</div>
              </div>
            </>
          )}
        </div>
      )}

      {!loading && !insights && (
        <div className="card" style={{ textAlign: 'center', padding: '26px', color: 'var(--muted)' }}>
          Could not compose a summary right now. The raw data below is still available.
        </div>
      )}

      <PrioritiesPanel priorities={overview?.priorities} />
    </>
  )
}

function OverviewData({ overview }: { overview: any; loading: boolean }) {
  if (!overview) return <div className="card" style={{ textAlign: 'center', padding: '20px', color: 'var(--danger)' }}>Failed to load overview.</div>

  const identity = overview.patient || {}
  const changes = overview.changes_since_last_visit || {}
  const moodTrend = overview.mood_trend || []
  const followups = overview.followups || {}
  const events = overview.timeline || []
  const risk = overview.risk
  const crisis = overview.crisis
  const latestMood = moodTrend.length > 0 ? moodTrend[0] : null

  return (
    <>
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr', gap: '12px', marginBottom: '16px' }} className="ov-grid3">
        <div className="card-sm">
          <div style={{ color: 'var(--accent)', fontWeight: 800, fontSize: '0.62rem', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '6px' }}>Client</div>
          <div style={{ fontSize: '1.05rem', fontWeight: 800, color: 'var(--heading)' }}>{identity.name || identity.username}</div>
          <div style={{ color: 'var(--muted)', fontSize: '0.65rem', marginTop: '4px' }}>
            {identity.age || '?'} yrs · {identity.occupation || '—'} · {identity.clinic || '—'}
          </div>
        </div>

        <div className="card-sm">
          <div style={{ color: 'var(--muted)', fontSize: '0.62rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.07em' }}>Mood trend</div>
          <div style={{ color: changes.mood_trend === 'improving' ? 'var(--ok)' : changes.mood_trend === 'declining' ? 'var(--danger)' : 'var(--warn)', fontSize: '1.1rem', fontWeight: 800 }}>
            {changes.mood_trend === 'improving' ? '↗ improving' : changes.mood_trend === 'declining' ? '↘ declining' : changes.mood_trend === 'stable' ? '→ stable' : '—'}
          </div>
          <div style={{ color: 'var(--soft)', fontSize: '0.65rem' }}>
            Now {changes.current_mood_avg ? Number(changes.current_mood_avg).toFixed(1) : '—'} | prev {changes.previous_mood_avg ? Number(changes.previous_mood_avg).toFixed(1) : '—'}
          </div>
        </div>

        <div className="card-sm">
          <div style={{ color: 'var(--muted)', fontSize: '0.62rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.07em' }}>Engagement</div>
          <div style={{ color: 'var(--heading)', fontSize: '1.1rem', fontWeight: 800 }}>
            {changes.journal_count_7 || 0} <span style={{ fontSize: '0.6rem', color: 'var(--muted)' }}>journals 7d</span>
          </div>
          <div style={{ color: changes.engagement_trend === 'increasing' ? 'var(--ok)' : changes.engagement_trend === 'declining' ? 'var(--danger)' : 'var(--warn)', fontSize: '0.65rem', fontWeight: 700 }}>
            {changes.engagement_trend === 'increasing' ? '↗' : changes.engagement_trend === 'declining' ? '↘' : '→'} {changes.journal_count_14 || 0} in 14d
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '16px' }} className="ov-grid2">
        <div className="card-sm">
          <div style={{ color: 'var(--accent)', fontWeight: 800, fontSize: '0.62rem', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '8px' }}>Risk snapshot</div>
          {risk ? (
            <>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ color: risk.triggered ? 'var(--danger)' : risk.risk_score >= 7 ? 'var(--warn)' : 'var(--ok)', fontSize: '1.4rem', fontWeight: 800 }}>{risk.risk_score}/10</span>
                {risk.triggered && <span style={{ fontSize: '1rem' }}>🚨</span>}
              </div>
              <div style={{ color: 'var(--muted)', fontSize: '0.6rem' }}>
                {formatDate(risk.created_at)} · confidence {risk.confidence ? `${(risk.confidence * 100).toFixed(0)}%` : '—'}{risk.algorithm_version ? ` · engine v${risk.algorithm_version}` : ''}
              </div>
              {(risk.explanation || '').length > 0 && (
                <div style={{ color: 'var(--soft)', fontSize: '0.62rem', marginTop: '4px', lineHeight: 1.55 }}>
                  {risk.explanation.slice(0, 170)}
                </div>
              )}
            </>
          ) : (
            <div style={{ color: 'var(--muted)', fontSize: '0.72rem' }}>No assessments yet.</div>
          )}
        </div>

        <div className="card-sm">
          <div style={{ color: 'var(--accent)', fontWeight: 800, fontSize: '0.62rem', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '8px' }}>Follow-ups</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ color: 'var(--heading)', fontSize: '1.4rem', fontWeight: 800 }}>{followups.pending || 0}</span>
            <span style={{ color: 'var(--muted)', fontSize: '0.65rem' }}>open of {followups.total || 0}</span>
          </div>
          <div style={{ color: 'var(--ok)', fontSize: '0.65rem', fontWeight: 700 }}>{followups.completed || 0} completed</div>
          {(followups.list || []).slice(0, 3).map((f: any) => (
            <div key={f.id} style={{ color: 'var(--soft)', fontSize: '0.62rem', marginTop: '3px' }}>
              {f.status === 'completed' ? '✅' : '⏳'} {f.title}
            </div>
          ))}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '16px' }} className="ov-grid2">
        <div className="card-sm">
          <div style={{ color: 'var(--accent)', fontWeight: 800, fontSize: '0.62rem', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '6px' }}>Clinical brief</div>
          {overview.clinical_brief ? (
            <>
              <div style={{ color: 'var(--heading)', fontSize: '0.72rem', fontWeight: 700 }}>{formatTime(overview.clinical_brief.timestamp)}</div>
              <div style={{ color: 'var(--soft)', fontSize: '0.68rem', marginTop: '4px', lineHeight: 1.55 }}>
                {(overview.clinical_brief.clinical_summary || overview.clinical_brief.summary || '').slice(0, 280)}
              </div>
              {(overview.clinical_brief.emotions || '').length > 0 && (
                <div style={{ color: 'var(--muted)', fontSize: '0.62rem', marginTop: '4px' }}>Emotions: {overview.clinical_brief.emotions}</div>
              )}
              {overview.clinical_brief.ai_analysis && (
                <div style={{ color: 'var(--faint)', fontSize: '0.58rem', marginTop: '6px', lineHeight: 1.6 }}>
                  <AiSourceBadge source={overview.clinical_brief.ai_analysis.provider} detailed />
                </div>
              )}
            </>
          ) : (
            <div style={{ color: 'var(--muted)', fontSize: '0.72rem' }}>No recent journals.</div>
          )}
        </div>

        <div className="card-sm">
          <div style={{ color: 'var(--accent)', fontWeight: 800, fontSize: '0.62rem', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '6px' }}>Last appointment</div>
          {overview.last_appointment ? (
            <>
              <div style={{ color: 'var(--heading)', fontSize: '0.72rem', fontWeight: 700 }}>
                {formatDate(overview.last_appointment.date)} {overview.last_appointment.time}
              </div>
              <div style={{ color: 'var(--soft)', fontSize: '0.68rem', marginTop: '2px' }}>
                {overview.last_appointment.session_type || 'Session'} · {overview.last_appointment.status}
              </div>
              <div style={{ color: 'var(--muted)', fontSize: '0.62rem', marginTop: '2px' }}>{overview.last_appointment.psychologist_username}</div>
            </>
          ) : (
            <div style={{ color: 'var(--muted)', fontSize: '0.72rem' }}>No appointments yet.</div>
          )}
          {crisis && (
            <div style={{ marginTop: '8px', background: 'var(--danger-soft)', border: '1px solid color-mix(in srgb, var(--danger) 33%, transparent)', borderRadius: '12px', padding: '7px 10px' }}>
              <span style={{ color: 'var(--danger)', fontSize: '0.65rem', fontWeight: 800 }}>🚨 CRISIS ACTIVE</span>
              <div style={{ color: 'var(--soft)', fontSize: '0.6rem', marginTop: '2px' }}>
                triggered {formatTime(crisis.triggered_at)} · {crisis.acknowledged ? 'acknowledged' : 'NOT acknowledged'}
              </div>
            </div>
          )}
        </div>
      </div>

      {latestMood && (
        <div className="card-sm" style={{ padding: '12px 14px', marginBottom: '16px' }}>
          <div style={{ color: 'var(--muted)', fontSize: '0.6rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: '6px' }}>Latest mood · 14d strip</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '1.5rem' }}>{moodIcon(latestMood.label)}</span>
            <span style={{ color: 'var(--heading)', fontWeight: 700, fontSize: '0.78rem', textTransform: 'capitalize' }}>{latestMood.label}</span>
            <span style={{ color: 'var(--muted)', fontSize: '0.65rem' }}>{formatTime(latestMood.timestamp)}</span>
            <div style={{ flex: 1, display: 'flex', gap: '3px', justifyContent: 'flex-end' }}>
              {moodTrend.map((m: any, i: number) => (
                <div key={i} style={{ flex: 1, maxWidth: '34px', fontSize: '0.85rem', textAlign: 'center', opacity: m.timestamp === latestMood.timestamp ? 1 : 0.5 }} title={`${m.label} ${formatDate(m.timestamp)}`}>
                  {moodIcon(m.label)}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', margin: '4px 0 8px' }}>
        <h3 style={{ margin: 0 }}>📅 Recent activity</h3>
        <span className="badge-theme">{events.length} events · 30d</span>
      </div>
      {events.length === 0 ? (
        <div className="card-sm" style={{ textAlign: 'center', color: 'var(--muted)', padding: '18px' }}>No events in the last 30 days.</div>
      ) : (
        <div style={{ maxHeight: '400px', overflowY: 'auto', paddingRight: '4px' }}>
          {events.slice(0, 40).map((ev: any, i: number) => {
            const colors: Record<string, string> = { mood: 'var(--ok)', journal: 'var(--violet)', followup: 'var(--warn)', crisis: 'var(--danger)' }
            return (
              <div key={i} style={{ borderLeft: `3px solid ${colors[ev.type] || 'var(--muted)'}`, background: 'var(--surface-soft)', borderRadius: '10px', padding: '8px 12px', margin: '4px 0' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '8px' }}>
                  <span style={{ color: 'var(--heading)', fontWeight: 700, fontSize: '0.78rem' }}>
                    {ev.type === 'mood' ? `${moodIcon(ev.data?.label)} ${(ev.data?.label || '').toUpperCase()}` :
                     ev.type === 'journal' ? `📝 ${ev.data?.title || 'Journal entry'}` :
                     ev.type === 'followup' ? `${ev.data?.status === 'completed' ? '✅' : '⏳'} ${ev.data?.title || 'Task'}` :
                     `🚨 ${(ev.data?.event || 'Crisis').toUpperCase()}`}
                  </span>
                  <span style={{ color: 'var(--muted)', fontSize: '0.65rem', whiteSpace: 'nowrap' }}>{formatTime(ev.timestamp)}</span>
                </div>
                <div style={{ color: 'var(--secondary)', fontSize: '0.7rem', marginTop: '2px' }}>
                  {ev.type === 'mood' ? `Mood: ${ev.data?.label || '—'} on ${ev.data?.date || ''}` :
                   ev.type === 'journal' ? (ev.data?.summary || '').slice(0, 150) :
                   ev.data?.description || ev.data?.details || ''}
                </div>
              </div>
            )
          })}
        </div>
      )}
      <style>{`
        @media (max-width: 860px) { .ov-grid3, .ov-grid2 { grid-template-columns: 1fr !important; } }
      `}</style>
    </>
  )
}

function RawDataSection({ patient, overview }: { patient: string; overview: any }) {
  return (
    <>
      <div className="card-sm" style={{ padding: '12px 14px', marginBottom: '16px', background: 'var(--accent-soft)', borderColor: 'color-mix(in srgb, var(--accent) 22%, transparent)' }}>
        <div style={{ color: 'var(--secondary)', fontSize: '0.76rem', lineHeight: 1.6 }}>
          📊 This tab holds the raw numbers and AI traces behind the plain-language summary. You don&apos;t need it for everyday work — it&apos;s here when you want to dig in.
        </div>
      </div>

      <h3>🧭 Current state data</h3>
      <OverviewData overview={overview} loading={false} />

      <h3 style={{ marginTop: '24px' }}>🎭 Emotion timeline</h3>
      <EmotionsSection patient={patient} />

      <h3 style={{ marginTop: '24px' }}>🧠 AI trace</h3>
      <AITraceSection patient={patient} />

      <h3 style={{ marginTop: '24px' }}>🔍 Patterns</h3>
      <PatternsSection patient={patient} overview={overview} />

      <h3 style={{ marginTop: '24px' }}>🚨 Crisis history</h3>
      <CrisisHistorySection patient={patient} />
    </>
  )
}

function CrisisHistorySection({ patient }: { patient: string }) {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    api.getCrisisHistory(patient)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false))
  }, [patient])

  if (loading) return <div className="card-sm" style={{ textAlign: 'center', padding: '20px', color: 'var(--muted)' }}>Loading crisis history…</div>
  if (!data) return <div className="card-sm" style={{ textAlign: 'center', padding: '20px', color: 'var(--muted)' }}>Crisis history unavailable.</div>

  const { episodes, stats } = data
  const fmtDuration = (s: number | null) => {
    if (s === null || s === undefined) return 'ongoing'
    if (s < 60) return `${s}s`
    if (s < 3600) return `${Math.round(s / 60)} min`
    return `${(s / 3600).toFixed(1)} h`
  }

  return (
    <>
      <div style={{ display: 'flex', gap: '18px', flexWrap: 'wrap', marginBottom: '10px' }}>
        {[
          { n: stats.total_episodes, label: 'episodes', color: 'var(--heading)' },
          { n: stats.active, label: 'active now', color: 'var(--danger)' },
          { n: fmtDuration(stats.avg_duration_seconds), label: 'avg duration', color: 'var(--heading)', small: true },
          { n: stats.resolved_by_patient, label: 'self-resolved', color: 'var(--ok)' },
        ].map((s, i) => (
          <div key={i}>
            <span className="statnum" style={{ color: s.color, fontSize: s.small ? '1.1rem' : undefined }}><SlotNumber value={s.n} /></span>
            <div style={{ fontSize: '0.7rem', color: 'var(--muted)', fontWeight: 600 }}>{s.label}</div>
          </div>
        ))}
      </div>

      {episodes.length === 0 ? (
        <div className="card-sm" style={{ textAlign: 'center', color: 'var(--muted)', padding: '18px' }}>
          No crisis episodes recorded. 🌿
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {episodes.map((ep: any, i: number) => (
            <div key={i} className="card-sm" style={{ borderLeft: `3px solid ${ep.active ? 'var(--danger)' : 'var(--ok)'}`, display: 'flex', justifyContent: 'space-between', gap: '10px', flexWrap: 'wrap', alignItems: 'center' }}>
              <div>
                <div style={{ fontWeight: 800, fontSize: '0.8rem', color: 'var(--heading)' }}>
                  {ep.active ? '🚨 Active episode' : '✅ Resolved'} · triggered {formatDate(ep.triggered_at)}
                </div>
                <div style={{ color: 'var(--muted)', fontSize: '0.68rem', marginTop: '2px' }}>
                  {ep.active ? `started ${formatTime(ep.triggered_at)}` : `triggered ${formatTime(ep.triggered_at)} → resolved ${formatTime(ep.resolved_at)}`}
                  {ep.resolved_by ? ` · by ${ep.resolved_by === patient ? 'the client themselves' : ep.resolved_by}` : ''}
                </div>
              </div>
              <span className="badge-theme" style={{ fontWeight: 800 }}>{fmtDuration(ep.duration_seconds)}</span>
            </div>
          ))}
        </div>
      )}
    </>
  )
}

function EmotionsSection({ patient }: { patient: string }) {
  const [data, setData] = useState<any>(null)

  useEffect(() => {
    api.getEmotionTimeline(patient, 30).then(setData).catch(() => {})
  }, [patient])

  if (!data) return <div className="card-sm" style={{ textAlign: 'center', padding: '20px', color: 'var(--muted)' }}>Loading emotional state…</div>

  const summary = data.emotion_summary || {}
  const timeline = data.timeline || []
  const entriesCount = data.entries_count ?? 0
  const pct = (v: number) => Math.round((v || 0) * 100)

  const dominant = Object.entries(summary)
    .sort(([, a]: any, [, b]: any) => (b.average || 0) - (a.average || 0))
    .slice(0, 3)
  const mostConsistent = Object.entries(summary).sort(([, a]: any, [, b]: any) => (b.count || 0) - (a.count || 0))[0] as [string, any] | undefined

  const half = Math.floor(timeline.length / 2)
  const early = timeline.slice(0, half)
  const late = timeline.slice(half)
  const avgProb = (pts: any[], emo: string) => {
    const vals = pts
      .map((p: any) => p.emotion_probabilities?.[emo] || 0)
      .filter((v: number) => v > 0)
    return vals.length ? vals.reduce((a: number, b: number) => a + b, 0) / vals.length : 0
  }
  const allEmos = new Set<string>()
  ;[...early, ...late].forEach((p: any) => Object.keys(p.emotion_probabilities || {}).forEach(e => allEmos.add(e)))

  const shiftNotes: { emo: string; dir: 'up' | 'down'; diff: number }[] = []
  allEmos.forEach(emo => {
    if (early.length === 0 || late.length === 0) return
    const e = avgProb(early, emo)
    const l = avgProb(late, emo)
    const diff = l - e
    if (Math.abs(diff) >= 0.12 && (e > 0 || l > 0)) {
      shiftNotes.push({ emo, dir: diff > 0 ? 'up' : 'down', diff })
    }
  })
  shiftNotes.sort((a, b) => Math.abs(b.diff) - Math.abs(a.diff))

  const topLabels = (point: any) =>
    Object.entries(point.emotion_probabilities || {})
      .filter(([, p]) => (p as number) > 0)
      .sort((a, b) => (b[1] as number) - (a[1] as number))
      .slice(0, 3)
      .map(([e]) => e)

  if (entriesCount === 0) {
    return <div className="card-sm" style={{ textAlign: 'center', padding: '20px', color: 'var(--muted)' }}>No analyzed journal entries in this window.</div>
  }

  return (
    <>
      <div className="card-sm" style={{ padding: '16px', marginBottom: '14px' }}>
        <div style={{ color: 'var(--accent)', fontWeight: 800, fontSize: '0.66rem', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '10px' }}>
          Emotional state · {entriesCount} entries (30d)
        </div>
        {dominant.length > 0 && (
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '10px' }}>
            {dominant.map(([emo, info]: [string, any]) => (
              <div key={emo} className="chip" style={{ cursor: 'default' }}>
                <strong style={{ textTransform: 'capitalize', color: 'var(--heading)' }}>{emo}</strong>
                <span style={{ fontSize: '0.65rem', color: 'var(--muted)' }}>{pct(info.average)}% avg</span>
              </div>
            ))}
          </div>
        )}
        {mostConsistent && (
          <div style={{ fontSize: '0.7rem', color: 'var(--soft)' }}>
            Most consistent: <strong style={{ textTransform: 'capitalize' }}>{mostConsistent[0]}</strong> — present in {mostConsistent[1].count} of {entriesCount} entries
          </div>
        )}
      </div>

      {shiftNotes.length > 0 && (
        <div className="card-sm" style={{ padding: '16px', marginBottom: '14px' }}>
          <div style={{ color: 'var(--accent)', fontWeight: 800, fontSize: '0.66rem', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '8px' }}>Notable shifts</div>
          {shiftNotes.slice(0, 4).map(s => (
            <div key={s.emo} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px', fontSize: '0.78rem' }}>
              <span style={{ color: s.dir === 'up' ? 'var(--danger)' : 'var(--info)', fontWeight: 800 }}>{s.dir === 'up' ? '↑' : '↓'}</span>
              <span style={{ textTransform: 'capitalize', fontWeight: 700 }}>{s.emo}</span>
              <span style={{ color: 'var(--soft)' }}>{s.dir === 'up' ? 'rising' : 'receding'} in recent entries ({pct(s.diff)}pt swing)</span>
            </div>
          ))}
        </div>
      )}

      <h4 style={{ fontSize: '0.85rem', color: 'var(--secondary)', fontWeight: 700, margin: '12px 0 8px' }}>Journal timeline ({entriesCount} entries)</h4>
      {timeline.map((point: any) => {
        const labels = topLabels(point)
        return (
          <div key={point.journal_id} className="card-sm" style={{ padding: '10px 13px', marginBottom: '6px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
              <span style={{ color: 'var(--muted)', fontSize: '0.68rem', fontWeight: 600 }}>{point.timestamp?.slice(0, 10)}</span>
              <span style={{ flex: 1, fontSize: '0.78rem', color: 'var(--text)' }}>
                {labels.length > 0 ? (
                  labels.map(l => (
                    <span key={l} className="chip" style={{ cursor: 'default', padding: '3px 10px', fontSize: '0.65rem', marginRight: '6px', background: 'var(--accent-soft)', borderColor: 'color-mix(in srgb, var(--accent) 25%, transparent)', color: 'var(--accent)' }}>{l}</span>
                  ))
                ) : (
                  (point.emotions || '').split(',').map((e: string) => e.trim()).filter(Boolean).slice(0, 3).join(' · ')
                )}
              </span>
            </div>
          </div>
        )
      })}
    </>
  )
}

function AITraceSection({ patient }: { patient: string }) {
  const [analyses, setAnalyses] = useState<any[]>([])
  const [risks, setRisks] = useState<any[]>([])
  const [emotionResults, setEmotionResults] = useState<any[]>([])

  useEffect(() => {
    Promise.allSettled([
      api.getAIAnalysesForPatient(patient),
      api.getRiskAssessmentsForPatient(patient),
      api.getEmotionResultsForPatient(patient),
    ]).then(([a, r, e]) => {
      setAnalyses(a.status === 'fulfilled' ? (a.value as any) || [] : [])
      setRisks(r.status === 'fulfilled' ? (r.value as any) || [] : [])
      setEmotionResults(e.status === 'fulfilled' ? (e.value as any) || [] : [])
    })
  }, [patient])

  return (
    <>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', marginBottom: '20px' }}>
        <div className="card-sm" style={{ textAlign: 'center', padding: '12px' }}>
          <div style={{ color: 'var(--muted)', fontSize: '0.62rem', fontWeight: 700, textTransform: 'uppercase' }}>AI analyses</div>
          <div style={{ color: 'var(--accent)', fontSize: '1.3rem', fontWeight: 800 }}>{analyses.length}</div>
        </div>
        <div className="card-sm" style={{ textAlign: 'center', padding: '12px' }}>
          <div style={{ color: 'var(--muted)', fontSize: '0.62rem', fontWeight: 700, textTransform: 'uppercase' }}>Risk assessments</div>
          <div style={{ color: 'var(--danger)', fontSize: '1.3rem', fontWeight: 800 }}>{risks.length}</div>
        </div>
        <div className="card-sm" style={{ textAlign: 'center', padding: '12px' }}>
          <div style={{ color: 'var(--muted)', fontSize: '0.62rem', fontWeight: 700, textTransform: 'uppercase' }}>Emotion results</div>
          <div style={{ color: 'var(--info)', fontSize: '1.3rem', fontWeight: 800 }}>{emotionResults.length}</div>
        </div>
      </div>

      {risks.length > 0 && (
        <>
          <h4 style={{ fontSize: '0.85rem', color: 'var(--secondary)', fontWeight: 700 }}>Risk assessments</h4>
          {risks.slice(0, 10).map((r: any) => (
            <div key={r.id} className="expander" style={{ cursor: 'default' }}>
              <div className="expander-header">
                <span>{r.created_at?.slice(0, 10)} · Risk: {r.risk_score}/10 {r.triggered ? '🚨' : ''}</span>
                <span style={{ color: 'var(--muted)', fontSize: '0.6rem' }}>v{r.algorithm_version}</span>
              </div>
              <div className="expander-body">
                <div style={{ fontSize: '0.68rem', color: 'var(--soft)', lineHeight: 1.65 }}>
                  {r.explanation && (() => {
                    try {
                      const exp = JSON.parse(r.explanation)
                      return (
                        <>
                          {exp.top_contributors?.map((c: any, i: number) => (
                            <div key={i}>&bull; {c.emotion}: P={c.probability?.toFixed(2)}, weight={c.weight}, contribution={c.contribution?.toFixed(3)}</div>
                          ))}
                          <div style={{ marginTop: '4px', color: 'var(--muted)' }}>
                            Keyword: {exp.keyword_base_score} | Emotion: {exp.emotion_risk_score} | Blended: {exp.blended_score}
                          </div>
                        </>
                      )
                    } catch { return r.explanation }
                  })()}
                </div>
              </div>
            </div>
          ))}
        </>
      )}

      {analyses.length > 0 && (
        <>
          <h4 style={{ fontSize: '0.85rem', color: 'var(--secondary)', fontWeight: 700, marginTop: '16px' }}>AI analysis history</h4>
          {analyses.slice(0, 10).map((a: any) => (
            <div key={a.id} className="card-sm" style={{ marginBottom: '6px', padding: '10px 13px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px' }}>
                <span style={{ color: 'var(--accent)', fontWeight: 700, fontSize: '0.7rem' }}>{a.created_at?.slice(0, 10)} · {a.priority}</span>
                <span className="badge-theme">{a.provider} v{a.model_version}</span>
              </div>
              <div style={{ color: 'var(--soft)', fontSize: '0.65rem', marginTop: '2px' }}>
                Confidence: {a.confidence != null ? `${(a.confidence * 100).toFixed(1)}%` : '—'}
              </div>
            </div>
          ))}
        </>
      )}

      {emotionResults.length > 0 && (
        <>
          <h4 style={{ fontSize: '0.85rem', color: 'var(--secondary)', fontWeight: 700, marginTop: '16px' }}>Emotion probability history</h4>
          {emotionResults.slice(0, 5).map((er: any) => {
            const probs: Record<string, number> = {}
            const fields = ['admiration','amusement','anger','annoyance','approval','caring','confusion','curiosity','desire','disappointment','disapproval','disgust','embarrassment','excitement','fear','gratitude','grief','joy','love','nervousness','optimism','pride','realization','relief','remorse','sadness','surprise','neutral']
            fields.forEach(f => { if (er[f] > 0) probs[f] = er[f] })
            return (
              <div key={er.id} className="card-sm" style={{ marginBottom: '6px', padding: '10px 13px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <span style={{ color: 'var(--accent)', fontSize: '0.7rem', fontWeight: 700 }}>{er.created_at?.slice(0, 10)}</span>
                  <span style={{ color: 'var(--muted)', fontSize: '0.55rem' }}>v{er.model_version}</span>
                </div>
                <EmotionBars emotionProbabilities={probs} maxItems={8} />
              </div>
            )
          })}
        </>
      )}

      {analyses.length === 0 && risks.length === 0 && emotionResults.length === 0 && (
        <div className="card-sm" style={{ textAlign: 'center', padding: '20px', color: 'var(--muted)' }}>
          No AI analysis data for this client yet.
        </div>
      )}
    </>
  )
}

function PatternsSection({ patient, overview }: { patient: string; overview: any }) {
  const [patterns, setPatterns] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    const timelineRaw = overview?.timeline || []
    const timeline = Array.isArray(timelineRaw) ? timelineRaw : timelineRaw.events || []

    Promise.allSettled([
      overview?.changes_since_last_visit
        ? Promise.resolve(overview.changes_since_last_visit)
        : api.getMetrics(patient),
      api.getEmotionTimeline(patient, 30),
      api.getRiskAssessmentsForPatient(patient),
      overview?.timeline ? Promise.resolve({ events: timeline }) : api.getTimeline(patient, 30),
    ]).then(([metricsRes, emoRes, riskRes, timelineRes]) => {
      const metrics = metricsRes.status === 'fulfilled' ? metricsRes.value : null
      const emoData = emoRes.status === 'fulfilled' ? emoRes.value : null
      const risks = riskRes.status === 'fulfilled' ? ((riskRes.value as any) || []) : []
      const tl = timelineRes.status === 'fulfilled' ? timelineRes.value : []
      const timelineEvents = (tl as any)?.events || (tl as any) || timeline

      const moodEvents = (timelineEvents as any[]).filter((e: any) => e.type === 'mood')
      const journalEvents = (timelineEvents as any[]).filter((e: any) => e.type === 'journal')

      const moodCounts: Record<string, number> = {}
      moodEvents.forEach((e: any) => {
        const label = e.data?.label || 'unknown'
        moodCounts[label] = (moodCounts[label] || 0) + 1
      })

      const dayOfWeekMood: Record<string, number[]> = {}
      moodEvents.forEach((e: any) => {
        const day = new Date(e.timestamp).toLocaleDateString('en-US', { weekday: 'short' })
        if (!dayOfWeekMood[day]) dayOfWeekMood[day] = []
        const score = e.data?.score || 3
        dayOfWeekMood[day].push(score)
      })
      const avgByDay: Record<string, number> = {}
      Object.entries(dayOfWeekMood).forEach(([day, scores]) => {
        avgByDay[day] = scores.reduce((a: number, b: number) => a + b, 0) / scores.length
      })

      const journalLengths = journalEvents.map((e: any) => (e.data?.content || '').length)
      const avgJournalLength = journalLengths.length > 0 ? Math.round(journalLengths.reduce((a: number, b: number) => a + b, 0) / journalLengths.length) : 0

      const riskScores = (risks as any[]).map((r: any) => r.risk_score || 0)
      const avgRisk = riskScores.length > 0 ? (riskScores.reduce((a: number, b: number) => a + b, 0) / riskScores.length).toFixed(1) : 'N/A'
      const maxRisk = riskScores.length > 0 ? Math.max(...riskScores) : 0

      const topEmotions = Object.entries(emoData?.emotion_summary || {})
        .sort(([, a]: [string, any], [, b]: [string, any]) => (b.average || 0) - (a.average || 0))
        .slice(0, 5)

      setPatterns({
        moodCounts,
        avgByDay,
        avgJournalLength,
        journalCount: journalEvents.length,
        avgRisk,
        maxRisk,
        riskCount: riskScores.length,
        topEmotions,
        moodTrend: (metrics as any)?.mood_trend || 'N/A',
        engagementTrend: (metrics as any)?.engagement_trend || 'N/A',
      })
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [patient, overview])

  if (loading) return <div className="card-sm" style={{ textAlign: 'center', padding: '20px', color: 'var(--muted)' }}>Analyzing patterns…</div>
  if (!patterns) return <div className="card-sm" style={{ textAlign: 'center', padding: '20px', color: 'var(--muted)' }}>No data available.</div>

  const dayOrder = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

  return (
    <>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '20px' }} className="ov-grid2">
        <div className="card-sm" style={{ padding: '16px' }}>
          <div style={{ color: 'var(--accent)', fontWeight: 800, fontSize: '0.66rem', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '10px' }}>Mood distribution</div>
          {Object.keys(patterns.moodCounts).length === 0 ? (
            <div style={{ color: 'var(--muted)', fontSize: '0.7rem' }}>No mood data.</div>
          ) : (
            Object.entries(patterns.moodCounts).sort(([, a], [, b]) => (b as number) - (a as number)).map(([label, count]: [string, any]) => {
              const max = Math.max(...(Object.values(patterns.moodCounts) as number[]))
              return (
                <div key={label} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '5px' }}>
                  <span style={{ color: 'var(--secondary)', fontSize: '0.65rem', width: '54px', textTransform: 'capitalize' }}>{label}</span>
                  <div className="track" style={{ flex: 1 }}>
                    <div style={{ width: `${(count / max) * 100}%`, background: 'var(--lime-deep)' }} />
                  </div>
                  <span style={{ color: 'var(--muted)', fontSize: '0.6rem', width: '18px', textAlign: 'right' }}>{count}</span>
                </div>
              )
            })
          )}
        </div>

        <div className="card-sm" style={{ padding: '16px' }}>
          <div style={{ color: 'var(--accent)', fontWeight: 800, fontSize: '0.66rem', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '10px' }}>Mood by weekday</div>
          {Object.keys(patterns.avgByDay).length === 0 ? (
            <div style={{ color: 'var(--muted)', fontSize: '0.7rem' }}>Not enough data.</div>
          ) : (
            dayOrder.filter(d => patterns.avgByDay[d] != null).map(day => {
              const avg = patterns.avgByDay[day]
              const p = ((avg - 1) / 4) * 100
              return (
                <div key={day} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '5px' }}>
                  <span style={{ color: 'var(--secondary)', fontSize: '0.65rem', width: '30px' }}>{day}</span>
                  <div className="track" style={{ flex: 1 }}>
                    <div style={{ width: `${p}%`, background: avg >= 3.5 ? 'var(--ok)' : avg >= 2.5 ? 'var(--warn)' : 'var(--danger)' }} />
                  </div>
                  <span style={{ color: 'var(--muted)', fontSize: '0.6rem', width: '24px', textAlign: 'right' }}>{avg.toFixed(1)}</span>
                </div>
              )
            })
          )}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '10px', marginBottom: '20px' }}>
        <div className="card-sm" style={{ textAlign: 'center', padding: '12px' }}>
          <div style={{ color: 'var(--muted)', fontSize: '0.6rem', fontWeight: 700, textTransform: 'uppercase' }}>Mood trend</div>
          <div style={{ color: patterns.moodTrend === 'improving' ? 'var(--ok)' : patterns.moodTrend === 'declining' ? 'var(--danger)' : 'var(--warn)', fontSize: '1rem', fontWeight: 800 }}>
            {patterns.moodTrend === 'improving' ? '↗ improving' : patterns.moodTrend === 'declining' ? '↘ declining' : patterns.moodTrend}
          </div>
        </div>
        <div className="card-sm" style={{ textAlign: 'center', padding: '12px' }}>
          <div style={{ color: 'var(--muted)', fontSize: '0.6rem', fontWeight: 700, textTransform: 'uppercase' }}>Engagement</div>
          <div style={{ fontSize: '1rem', fontWeight: 800 }}>{patterns.journalCount} journals</div>
        </div>
        <div className="card-sm" style={{ textAlign: 'center', padding: '12px' }}>
          <div style={{ color: 'var(--muted)', fontSize: '0.6rem', fontWeight: 700, textTransform: 'uppercase' }}>Avg entry</div>
          <div style={{ color: 'var(--accent)', fontSize: '1rem', fontWeight: 800 }}>{patterns.avgJournalLength} ch</div>
        </div>
        <div className="card-sm" style={{ textAlign: 'center', padding: '12px' }}>
          <div style={{ color: 'var(--muted)', fontSize: '0.6rem', fontWeight: 700, textTransform: 'uppercase' }}>Avg risk</div>
          <div style={{ color: Number(patterns.avgRisk) >= 5 ? 'var(--danger)' : 'var(--ok)', fontSize: '1rem', fontWeight: 800 }}>{patterns.avgRisk}/10</div>
        </div>
      </div>

      {patterns.topEmotions.length > 0 && (
        <div className="card-sm" style={{ padding: '16px' }}>
          <div style={{ color: 'var(--accent)', fontWeight: 800, fontSize: '0.66rem', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '10px' }}>Top emotions (30d)</div>
          {patterns.topEmotions.map(([emotion, info]: [string, any]) => {
            const p = Math.round((info.average || 0) * 100)
            return (
              <div key={emotion} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '5px' }}>
                <span style={{ color: 'var(--secondary)', fontSize: '0.65rem', width: '100px', textTransform: 'capitalize' }}>{emotion}</span>
                <div className="track" style={{ flex: 1 }}>
                  <div style={{ width: `${p}%`, background: 'var(--violet)' }} />
                </div>
                <span style={{ color: 'var(--muted)', fontSize: '0.6rem', width: '58px', textAlign: 'right' }}>{p}% (×{info.count})</span>
              </div>
            )
          })}
        </div>
      )}
    </>
  )
}
