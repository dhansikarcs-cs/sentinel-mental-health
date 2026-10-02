import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { getUser } from '../stores/auth'
import { moodColor, moodIcon, moodScore, formatDate, todayStr } from '../constants'
import SlotNumber from '../components/SlotNumber'
import { Confetti, useRipple, useToast } from '../components/fx'

/* Deterministic per-user vitals so the dashboard shows stable numbers. */
function hashSeed(s: string): number {
  let h = 0
  for (let i = 0; i < s.length; i++) h = ((h << 5) - h + s.charCodeAt(i)) | 0
  return Math.abs(h)
}
function seededVitals(username: string) {
  const seed = hashSeed(username + new Date().toDateString())
  const rnd = (n: number) => ((seed >> (n * 3)) % 1000) / 1000
  return {
    bpm: 62 + Math.round(rnd(1) * 22),
    stress: 18 + Math.round(rnd(2) * 42),
    sleep: Math.round((6.2 + rnd(3) * 2.4) * 10) / 10,
    hrv: 38 + Math.round(rnd(4) * 34),
    spo2: 96 + Math.round(rnd(5) * 3),
  }
}

export default function Dashboard() {
  const navigate = useNavigate()
  const user = getUser()
  const toast = useToast()
  const ripple = useRipple()
  const [wellness, setWellness] = useState<any>(null)
  const [followups, setFollowups] = useState<any[]>([])
  const [bookings, setBookings] = useState<any[]>([])
  const [streaks, setStreaks] = useState<any>(null)
  const [celebrated, setCelebrated] = useState<number | null>(null)
  const [week, setWeek] = useState<any>(null)
  const [forecast, setForecast] = useState<any>(null)

  useEffect(() => {
    api.getWellness().then(setWellness).catch(() => {})
    api.getFollowups().then((d: any) => setFollowups(Array.isArray(d) ? d : [])).catch(() => {})
    api.getBookings().then((d: any) => setBookings(Array.isArray(d) ? d : [])).catch(() => {})
    api.getStreaks().then(setStreaks).catch(() => {})
    api.getWeekSummary().then(setWeek).catch(() => {})
    api.getMoodForecast().then(setForecast).catch(() => {})
  }, [])

  const firstName = (user?.name || user?.username || 'there').split(' ')[0]
  const ring = wellness?.ring
  const v = ring && (ring.bpm > 0 || ring.stress > 0) ? ring : seededVitals(user?.username || 'demo')
  const moodTrend: any[] = wellness?.mood_trend || []
  const avgMood = moodTrend.length
    ? moodTrend.reduce((a: number, m: any) => a + moodScore(m.label), 0) / moodTrend.length
    : 0

  const pendingTasks = followups.filter((f: any) => f.patient_username === user?.username && f.status === 'pending')
  const doneTasks = followups.filter((f: any) => f.patient_username === user?.username && f.status === 'completed')
  const nextSession = bookings
    .filter((b: any) => (b.status === 'Approved') && b.date >= todayStr())
    .sort((a: any, b: any) => (a.date + a.time).localeCompare(b.date + b.time))[0]
  const daysUntil = nextSession
    ? Math.max(0, Math.round((new Date(nextSession.date + 'T00:00:00').getTime() - new Date(todayStr() + 'T00:00:00').getTime()) / 86400000))
    : null

  const hour = new Date().getHours()
  const greeting = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening'

  // Celebrate streak milestones (3, 7, 14, 30…) once per load
  const milestone = streaks?.current_streak > 0 && [3, 7, 14, 30, 60, 100].includes(streaks.current_streak) ? streaks.current_streak : null
  useEffect(() => {
    if (milestone && milestone !== celebrated) {
      setCelebrated(milestone)
      toast('success', `🎉 ${milestone}-day check-in streak — that's real momentum!`)
    }
  }, [milestone])

  const stressLevel = v.stress <= 35 ? { label: 'Low', color: 'var(--ok)' } : v.stress <= 60 ? { label: 'Moderate', color: 'var(--warn)' } : { label: 'High', color: 'var(--danger)' }

  return (
    <div className="animate-fade-in space-y-4">
      <Confetti trigger={milestone} />
      {/* ── Greeting hero ── */}
      <div className="card-lime" style={{ padding: '26px 28px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '18px', flexWrap: 'wrap' }}>
        <div>
          <div style={{ fontSize: '0.72rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.09em', opacity: 0.7 }}>{greeting}, {firstName}</div>
          <h2 style={{ fontSize: '1.8rem', margin: '6px 0 2px', color: 'var(--lime-ink) !important' }}>
            {wellness?.mood ? `Feeling ${wellness.mood.label} today` : 'How are you, really?'}
          </h2>
          <div style={{ fontSize: '0.85rem', opacity: 0.75 }}>
            {wellness?.journals_today > 0 ? 'Journal logged ✓ — nice consistency.' : 'Your journal is waiting — one honest paragraph is plenty.'}
          </div>
        </div>
        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          <button className="btn-primary" onClick={() => navigate('/journal')}>📝 Write today&apos;s entry</button>
          <button onClick={() => navigate('/mood')}>😊 Log mood</button>
        </div>
      </div>

      {/* ── Stat row ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '10px' }}>
        <div className="card-sm" style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
          <span style={{ fontSize: '0.65rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.07em', color: 'var(--muted)' }}>Mood (7d avg)</span>
          <span className="statnum"><SlotNumber value={avgMood ? avgMood.toFixed(1) : '—'} /><small>/5</small></span>
        </div>
        <div className="card-sm">
          <span style={{ fontSize: '0.65rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.07em', color: 'var(--muted)' }}>Entries today</span>
          <span className="statnum"><SlotNumber value={wellness?.journals_today ?? 0} /></span>
        </div>
        <div className="card-sm">
          <span style={{ fontSize: '0.65rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.07em', color: 'var(--muted)' }}>Open tasks</span>
          <span className="statnum"><SlotNumber value={pendingTasks.length} /></span>
        </div>
        <div className="card-sm">
          <span style={{ fontSize: '0.65rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.07em', color: 'var(--muted)' }}>Check-in streak</span>
          <span className="statnum">
            <SlotNumber value={streaks ? (streaks.current_streak > 0 ? `🔥 ${streaks.current_streak}` : '—') : '…'} replayKey={streaks?.current_streak ?? ''} />
          </span>
          {streaks && streaks.current_streak > 0 && (
            <span style={{ fontSize: '0.6rem', color: 'var(--muted)' }}>best: {streaks.longest_streak}</span>
          )}
        </div>
        <div className="card-sm">
          <span style={{ fontSize: '0.65rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.07em', color: 'var(--muted)' }}>Next session</span>
          <span style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--heading)' }}>
            {nextSession ? `${formatDate(nextSession.date)} · ${nextSession.time}` : '—'}
          </span>
          {daysUntil !== null && (
            <span style={{ fontSize: '0.62rem', fontWeight: 800, color: daysUntil === 0 ? 'var(--ok)' : 'var(--accent)' }}>
              {daysUntil === 0 ? '🎉 Today!' : `in ${daysUntil} day${daysUntil === 1 ? '' : 's'}`}
            </span>
          )}
        </div>
      </div>

      {/* ── Check-in heatmap ── */}
      {streaks && (
        <div className="card" style={{ padding: '18px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px', flexWrap: 'wrap', gap: '6px' }}>
            <h3 style={{ margin: 0 }}>🗓️ Last 28 days</h3>
            <span style={{ fontSize: '0.7rem', color: 'var(--muted)' }}>
              {streaks.checked_in_today ? '✅ Checked in today' : 'No check-in yet today — a journal entry or mood log counts'}
            </span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(14, 1fr)', gap: '4px', maxWidth: '440px' }}>
            {streaks.heatmap.map((d: any) => (
              <div
                key={d.date}
                title={`${d.date}${d.checked ? ' · checked in' : ''}`}
                style={{
                  paddingTop: '100%', borderRadius: 4,
                  background: d.checked ? 'var(--ok)' : 'var(--surface-soft)',
                  border: '1px solid var(--border-soft)',
                  opacity: d.checked ? 0.85 : 1,
                }}
              />
            ))}
          </div>
        </div>
      )}

      {/* ── Main grid ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.25fr 1fr', gap: '14px', alignItems: 'start' }} className="dash-grid">
        {/* Left column */}
        <div className="space-y-4">
          {/* Mood trend strip */}
          <div className="card">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
              <h3 style={{ margin: 0 }}>Mood trend</h3>
              <button className="btn-ghost" style={{ fontSize: '0.72rem' }} onClick={() => navigate('/mood')}>View all →</button>
            </div>
            {moodTrend.length > 0 ? (
              <div style={{ display: 'flex', gap: '6px', alignItems: 'flex-end', height: '110px' }}>
                {moodTrend.slice(0, 7).map((m: any, i: number) => {
                  const score = moodScore(m.label)
                  return (
                    <div key={i} style={{ flex: 1, textAlign: 'center' }} title={`${m.label} · ${m.date}`}>
                      <div style={{
                        height: `${(score / 5) * 80 + 12}px`, borderRadius: '10px 10px 4px 4px',
                        background: `linear-gradient(180deg, ${moodColor(m.label)}, ${moodColor(m.label)}88)`,
                        margin: '0 3px 6px', display: 'flex', alignItems: 'flex-start', justifyContent: 'center', paddingTop: '6px',
                      }}>
                        <span style={{ fontSize: '0.9rem' }}>{m.emoji}</span>
                      </div>
                      <div style={{ fontSize: '0.6rem', color: 'var(--faint)' }}>{m.date?.slice(8)}</div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <p style={{ color: 'var(--muted)', fontSize: '0.82rem' }}>Log your mood for 7 days to see your trend here.</p>
            )}
          </div>

          {/* Follow-ups preview */}
          <div className="card">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
              <h3 style={{ margin: 0 }}>My care tasks</h3>
              <button className="btn-ghost" style={{ fontSize: '0.72rem' }} onClick={() => navigate('/followups')}>All tasks →</button>
            </div>
            {followups.length === 0 ? (
              <p style={{ color: 'var(--muted)', fontSize: '0.82rem' }}>Nothing assigned yet — your psychologist will add care tasks here.</p>
            ) : (
              <div className="space-y-2">
                {[...pendingTasks.slice(0, 3), ...doneTasks.slice(0, 1)].map((t: any) => (
                  <div key={t.id} className="card-stage" style={{ justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
                      <span>{t.status === 'completed' ? '✅' : '⏳'}</span>
                      <div style={{ minWidth: 0 }}>
                        <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--heading)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{t.title}</div>
                        {t.due_date && <div style={{ fontSize: '0.65rem', color: t.due_date < todayStr() ? 'var(--danger)' : 'var(--muted)' }}>Due {formatDate(t.due_date)}</div>}
                      </div>
                    </div>
                    {t.grade && t.grade !== 'none' ? (
                      <span className="badge-theme">{t.grade === 'green' ? '🟢 Great' : t.grade === 'yellow' ? '🟡 Partial' : '🔴 Needs work'}</span>
                    ) : (
                      <span className="badge-theme">{t.status === 'completed' ? 'Done' : 'Open'}</span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right column */}
        <div className="space-y-4">
          {/* Mood forecast */}
          {forecast && forecast.forecast?.length > 0 && (
            <div className="card">
              <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', margin: '0 0 8px' }}>🔮 Next 3 days</h3>
              <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
                {forecast.forecast.map((f: any, i: number) => {
                  const d = new Date(Date.now() + (i + 1) * 86400000)
                  const color = f.label === 'good' ? 'var(--secondary)' : f.label === 'okay' ? '#d9c34a' : '#e07a5f'
                  return (
                    <div key={i} style={{ flex: 1, background: 'rgba(127,255,0,0.06)', border: '1px solid rgba(127,255,0,0.18)', borderRadius: '12px', padding: '10px 8px', textAlign: 'center' }}>
                      <div style={{ fontSize: '0.62rem', color: 'var(--muted)', fontWeight: 700, textTransform: 'uppercase' }}>{d.toLocaleDateString(undefined, { weekday: 'short' })}</div>
                      <div style={{ fontSize: '1.05rem', fontWeight: 800, color, marginTop: '2px' }}>{f.label === 'good' ? '☀️' : f.label === 'okay' ? '⛅' : '🌧️'} {f.label}</div>
                      <div style={{ fontSize: '0.58rem', color: 'var(--muted)', marginTop: '2px' }}>{f.confidence} confidence</div>
                    </div>
                  )
                })}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--muted)', lineHeight: 1.5 }}>{forecast.summary}</div>
              <div style={{ fontSize: '0.72rem', marginTop: '6px', fontWeight: 600 }}>💡 {forecast.tip}</div>
              <div style={{ fontSize: '0.6rem', color: 'var(--muted)', marginTop: '6px' }}>
                Pattern from your last {forecast.basis} check-ins · a guess with training wheels, not a promise
              </div>
            </div>
          )}

          {/* Week recap */}
          {week && (
            <div className="card">
              <h3 style={{ margin: '0 0 10px' }}>🗓️ Your week so far</h3>
              <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flexWrap: 'wrap', marginBottom: '8px' }}>
                <span className="statnum" style={{ fontSize: '1.6rem' }}>
                  <SlotNumber value={week.checkins_7d} />
                </span>
                <span style={{ fontSize: '0.75rem', color: 'var(--muted)', fontWeight: 600 }}>
                  check-ins · {week.trend === 'up' ? '↗ more than last week' : week.trend === 'down' ? '↘ a bit less than last week' : '→ same as last week'}
                </span>
              </div>
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                <span className="badge-theme">📝 {week.journals_7d} journals</span>
                <span className="badge-theme">😊 {week.positive_days} good day{week.positive_days === 1 ? '' : 's'}</span>
                {week.best_day && <span className="badge-theme pop">best: {week.best_day.emoji} {week.best_day.label}</span>}
                {week.next_session && <span className="badge-theme">📅 session {formatDate(week.next_session.date)}</span>}
              </div>
              {week.top_emotions?.length > 0 && (
                <div style={{ fontSize: '0.72rem', color: 'var(--muted)', marginTop: '8px' }}>
                  Most-written feelings: {week.top_emotions.join(', ')}
                </div>
              )}
            </div>
          )}

          {/* Ring vitals */}
          <div className="card-dark">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
              <h3 style={{ margin: 0 }}>⌚ Ring vitals</h3>
              <span className="badge-psych">LIVE</span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              {[
                { label: 'Heart rate', value: `${v.bpm}`, unit: 'bpm', icon: '❤️' },
                { label: 'Stress', value: `${v.stress}`, unit: `/100 · ${stressLevel.label}`, icon: '🧘' },
                { label: 'Sleep', value: `${v.sleep}`, unit: 'hrs', icon: '🌙' },
                { label: 'HRV', value: `${v.hrv}`, unit: 'ms', icon: '📈' },
              ].map(m => (
                <div key={m.label} style={{ background: 'rgba(255,255,255,0.06)', borderRadius: '14px', padding: '12px' }}>
                  <div style={{ fontSize: '0.62rem', color: '#A6AC9D', textTransform: 'uppercase', letterSpacing: '0.07em', fontWeight: 700 }}>{m.icon} {m.label}</div>
                  <div style={{ fontSize: '1.45rem', fontWeight: 800, color: 'var(--on-ink)', marginTop: '2px' }}>{m.value}</div>
                  <div style={{ fontSize: '0.62rem', color: '#A6AC9D' }}>{m.unit}</div>
                </div>
              ))}
            </div>
            <div style={{ fontSize: '0.62rem', color: '#8B9184', marginTop: '10px' }}>
              Simulated readings while your ring is pairing. Never used to determine safety on its own.
            </div>
          </div>

          {/* AI insights */}
          {wellness?.ai_insights && (
            <div className="card">
              <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>📊 My AI insights</h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', marginBottom: '10px' }}>
                <div className="metric-card" style={{ padding: '10px' }}>
                  <div style={{ fontSize: '0.6rem', color: 'var(--muted)' }}>Journals 7d</div>
                  <div style={{ fontSize: '1.3rem', fontWeight: 800 }}>{wellness.ai_insights.journal_count || 0}</div>
                </div>
                <div className="metric-card" style={{ padding: '10px' }}>
                  <div style={{ fontSize: '0.6rem', color: 'var(--muted)' }}>Compliance</div>
                  <div style={{ fontSize: '1.3rem', fontWeight: 800 }}>{wellness.ai_insights.compliance || 0}%</div>
                </div>
                <div className="metric-card" style={{ padding: '10px' }}>
                  <div style={{ fontSize: '0.6rem', color: 'var(--muted)' }}>Missed</div>
                  <div style={{ fontSize: '1.3rem', fontWeight: 800 }}>{wellness.ai_insights.missed || 0}</div>
                </div>
              </div>
              {wellness.ai_insights.grades && (
                <div style={{ fontSize: '0.72rem', color: 'var(--muted)', marginBottom: '6px' }}>
                  Grades: 🟢 {wellness.ai_insights.grades.green || 0} · 🟡 {wellness.ai_insights.grades.yellow || 0} · 🔴 {wellness.ai_insights.grades.red || 0}
                </div>
              )}
              {wellness.ai_insights.mood_message && (
                <div style={{ fontSize: '0.8rem', color: 'var(--soft)', marginBottom: '6px' }}>{wellness.ai_insights.mood_message}</div>
              )}
              {wellness.ai_insights.relapse_flag && (
                <div className="card-sm" style={{ borderColor: 'var(--danger)', color: 'var(--danger)', fontSize: '0.8rem', fontWeight: 600 }}>
                  ⚠️ {wellness.ai_insights.relapse_message || 'Warning flagged'}
                </div>
              )}
              <div style={{ fontSize: '0.6rem', color: 'var(--faint)', lineHeight: 1.5, marginTop: '8px' }}>
                AI-generated, not reviewed by your psychologist. Sentinel assists monitoring — it never determines whether you are safe. If you feel unsafe, seek help immediately.
              </div>
            </div>
          )}

          {/* Quick actions */}
          <div className="card">
            <h3 style={{ marginBottom: '10px' }}>Quick actions</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
              {[
                { label: '📔 Journal', to: '/journal' },
                { label: '📅 Book session', to: '/bookings' },
                { label: '🔍 My timeline', to: '/timeline' },
                { label: '🛡 Emergency', to: '/crisis' },
              ].map(a => (
                <button key={a.to} {...ripple} onClick={() => navigate(a.to)} style={{ padding: '12px', fontSize: '0.8rem', borderRadius: '14px' }}>{a.label}</button>
              ))}
            </div>
          </div>
        </div>
      </div>

      <style>{`
        @media (max-width: 960px) { .dash-grid { grid-template-columns: 1fr !important; } }
      `}</style>
    </div>
  )
}
