import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { sourceColor } from '../constants'
import SlotNumber from '../components/SlotNumber'
import { Shimmer, FloatingEmpty } from '../components/fx'
import { useAdvancedPanels } from '../hooks/useAdvanced'

const READINESS_META: Record<string, { color: string; label: string }> = {
  high: { color: 'var(--ok)', label: 'ready' },
  medium: { color: 'var(--warn)', label: 'shaky' },
  low: { color: 'var(--danger)', label: 'fragile' },
}

const TIER_META: Record<string, { label: string; dot: string; badgeBg: string }> = {
  crisis: { label: 'CRISIS', dot: 'var(--danger)', badgeBg: 'var(--danger-soft)' },
  high: { label: 'HIGH', dot: '#E8763B', badgeBg: 'var(--warn-soft)' },
  attention: { label: 'ATTENTION', dot: 'var(--warn)', badgeBg: 'var(--warn-soft)' },
  stable: { label: 'STABLE', dot: 'var(--ok)', badgeBg: 'var(--ok-soft)' },
}

export default function PsychTriagePage() {
  const navigate = useNavigate()
  const [patients, setPatients] = useState<any[]>([])
  const [priorities, setPriorities] = useState<any[]>([])
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})
  const [riskAssessments, setRiskAssessments] = useState<Record<string, any>>({})
  const [explainOpen, setExplainOpen] = useState<Record<string, boolean>>({})
  const [filter, setFilter] = useState('All')
  const [query, setQuery] = useState('')
  const [cols, setCols] = useState(() => {
    const saved = typeof localStorage !== 'undefined' ? localStorage.getItem('caseloadCols') : null
    return saved === '1' || saved === '2' || saved === '3' ? Number(saved) : 3
  })
  const [caseload, setCaseload] = useState<any>(null)
  const [digest, setDigest] = useState<any>(null)
  const [readiness, setReadiness] = useState<Record<string, any>>({})
  const [recommending, setRecommending] = useState<string>('')
  const advanced = useAdvancedPanels()
  const [recTitle, setRecTitle] = useState('')
  const [recCategory, setRecCategory] = useState('calming')

  useEffect(() => {
    api.getPsychPatients().then(async (pts) => {
      setPatients(pts || [])
      if (pts?.length) {
        const results = await Promise.allSettled(
          pts.map((p: any) => api.triageSummary(p.username || p).catch(() => null))
        )
        const computed = pts.map((p: any, i: any) => {
          const result = results[i]?.status === 'fulfilled' ? results[i].value : null
          const tier: string = result?.tier || 'stable'
          const crisis: boolean = result?.crisis ?? false
          const score: number = result?.priority_score ?? 0
          return { patient: p.username || p, name: p.name || p, score, tier, crisis, ...(result || {}) }
        })
        computed.sort((a: any, b: any) => b.score - a.score)
        setPriorities(computed)
      }
    }).catch(() => {})
    api.getCaseloadHealth().then(setCaseload).catch(() => {})
    api.getWeeklyDigest().then(setDigest).catch(() => {})
  }, [])

  async function loadReadiness(patient: string) {
    try {
      const r = await api.getSessionReadiness(patient)
      setReadiness((prev: any) => ({ ...prev, [patient]: r }))
    } catch {}
  }

  async function recommendTool(patient: string) {
    if (!recTitle.trim()) return
    try {
      await api.recommendCopingTool({ patient_username: patient, title: recTitle, category: recCategory })
      setRecommending('')
      setRecTitle('')
    } catch {}
  }

  const counts: Record<string, number> = { crisis: 0, high: 0, attention: 0, stable: 0 }
  priorities.forEach((p: any) => { const t: string = p.tier || ''; counts[t] = (counts[t] || 0) + 1 })

  function pickCols(n: number) {
    setCols(n)
    try { localStorage.setItem('caseloadCols', String(n)) } catch {}
  }

  const shown = priorities
    .filter((p: any) => filter === 'All' || p.tier === filter.toLowerCase())
    .filter((p: any) => !query || (p.name || '').toLowerCase().includes(query.toLowerCase()) || (p.patient || '').toLowerCase().includes(query.toLowerCase()))

  async function assessRisk(patient: string, lastRaw: string) {
    if (!lastRaw) return
    try {
      const result = await api.assessRisk(lastRaw)
      setRiskAssessments({ ...riskAssessments, [patient]: result })
    } catch {}
  }

  return (
    <div className="animate-fade-in">
      {/* Stat row like the mock (34 Deals · 20 won · 3 lost) */}
      <div style={{ display: 'flex', gap: 'clamp(18px, 4vw, 52px)', flexWrap: 'wrap', alignItems: 'center', marginBottom: '22px' }}>
        {[
          { n: counts.crisis, label: 'Crisis', color: 'var(--danger)', delta: counts.crisis > 0 ? 'live' : null, pulse: counts.crisis > 0 },
          { n: counts.high, label: 'High', color: '#E8763B', delta: null },
          { n: counts.attention, label: 'Attention', color: 'var(--warn)', delta: null },
          { n: counts.stable, label: 'Stable', color: 'var(--ok)', delta: null },
        ].map(s => (
          <div key={s.label}>
            <span className={`statnum${s.pulse ? ' heartbeat' : ''}`} style={{ color: s.color }}>
              <SlotNumber value={s.n} />
              {s.delta && <span className="stat-delta delta-up" style={{ background: 'var(--danger-soft)', color: 'var(--danger-deep)' }}>⚡ {s.delta}</span>}
            </span>
            <div style={{ fontSize: '0.78rem', color: 'var(--muted)', fontWeight: 600 }}>{s.pulse ? <><span className="live-dot" style={{ marginRight: 5 }} />{s.label}</> : s.label}</div>
          </div>
        ))}
        <button className="btn-primary" style={{ marginLeft: 'auto' }} onClick={() => navigate('/open-session')}>
          🧑‍⚕️ Open a session
        </button>
      </div>

      {advanced && digest && digest.summary && (
        <div className="card-sm" style={{ padding: '12px 18px', marginBottom: '14px', background: 'var(--accent-soft)', borderColor: 'color-mix(in srgb, var(--accent) 22%, transparent)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <span style={{ color: 'var(--accent)', fontWeight: 800, fontSize: '0.66rem', textTransform: 'uppercase', letterSpacing: '0.08em' }}>📅 Week of {digest.week_of}</span>
            <span className="badge-theme">
              {digest.summary.checkins} check-ins {digest.summary.checkin_trend === 'up' ? '↗' : digest.summary.checkin_trend === 'down' ? '↘' : '→'}
              {digest.summary.checkin_delta !== 0 ? ` (${digest.summary.checkin_delta > 0 ? '+' : ''}${digest.summary.checkin_delta})` : ''}
            </span>
            <span className="badge-theme">✅ {digest.summary.followups_completed} follow-ups done</span>
            {digest.summary.crisis_episodes_resolved > 0 && <span className="badge-theme">🚨 {digest.summary.crisis_episodes_resolved} crisis episode(s) resolved</span>}
          </div>
          {digest.highlights?.length > 0 && (
            <div style={{ marginTop: '6px', fontSize: '0.72rem', color: 'var(--secondary)', lineHeight: 1.6 }}>
              {digest.highlights.slice(0, 3).map((h: any, i: number) => (
                <div key={i}>• <strong>{h.name}</strong> — {h.text}</div>
              ))}
            </div>
          )}
        </div>
      )}

      {advanced && caseload && caseload.summary && (
        <div className="card-sm" style={{ padding: '14px 18px', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '18px', flexWrap: 'wrap' }}>
          <div style={{ fontSize: '1.5rem' }}>{caseload.summary.active_crises > 0 ? '🚨' : caseload.summary.disengaged > 0 ? '👀' : '🌿'}</div>
          <div style={{ flex: 1, minWidth: '220px' }}>
            <div style={{ fontWeight: 800, fontSize: '0.92rem', color: 'var(--heading)' }}>
              {caseload.summary.active_crises > 0
                ? `${caseload.summary.active_crises} active crisis${caseload.summary.active_crises === 1 ? '' : 'es'} — act now`
                : caseload.summary.disengaged > 0
                  ? `${caseload.summary.disengaged} client${caseload.summary.disengaged === 1 ? '' : 's'} disengaged — worth a check-in`
                  : 'Caseload looks steady today'}
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--muted)', marginTop: '2px' }}>
              {caseload.summary.total_clients} clients · {caseload.summary.checked_in_today} checked in today · {caseload.summary.pending_followups} pending follow-up{caseload.summary.pending_followups === 1 ? '' : 's'}
            </div>
          </div>
          {(caseload.clients || []).slice(0, 4).map((c: any) => (
            <button
              key={c.username}
              className="chip"
              title={`${c.name}: ${c.attention}${c.days_quiet !== null && c.days_quiet !== undefined ? `, quiet ${c.days_quiet}d` : ''}`}
              onClick={() => navigate('/patient-insights')}
              style={c.attention === 'crisis' ? { borderColor: 'var(--danger)', color: 'var(--danger)', fontWeight: 800 } : undefined}
            >
              {c.attention === 'crisis' ? '🚨' : c.attention === 'disengaged' ? '💤' : c.attention === 'watch' ? '👀' : '✅'} {c.name.split(' ')[0]}
            </button>
          ))}
        </div>
      )}

      {/* Filter bar */}
      <div style={{ display: 'flex', gap: '10px', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap' }}>
        <h2 style={{ margin: 0, fontSize: '1.15rem' }}>Caseload</h2>
        <span style={{ fontSize: '0.78rem', color: 'var(--muted)', fontWeight: 700, borderBottom: '2px solid var(--ink)', paddingBottom: '2px' }}>{shown.length} shown</span>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
          <input placeholder="🔍 Search…" value={query} onChange={e => setQuery(e.target.value)} style={{ width: '170px', borderRadius: 999 }} />
          {['All', 'Crisis', 'High', 'Attention', 'Stable'].map(f => (
            <button key={f} className={`chip${filter === f ? ' active' : ''}`} onClick={() => setFilter(f)}>{f}</button>
          ))}
          <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }} title="Cards per row">
            {[3, 2, 1].map(n => (
              <button key={n} className={`chip${cols === n ? ' active' : ''}`} onClick={() => pickCols(n)} aria-label={`${n} per row`}>
                {'▮'.repeat(n)}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Client cards */}
      <div className={`caseload-grid cols-${cols}`}>
        {shown.map((p: any) => {
          const meta = TIER_META[p.tier] || TIER_META.stable
          const isCrisis = p.crisis
          const open = expanded[p.patient]
          const mood = (p.mood || p.recent_mood || 'neutral').toLowerCase()
          return (
            <div
              key={p.patient}
              className={`lead-card${isCrisis ? ' calm-pulse' : ''}`}
              style={isCrisis ? { borderColor: 'var(--danger)', borderWidth: '2px' } : undefined}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div className="avatar-sm" style={{ background: 'var(--surface-soft-2)', border: '1px solid var(--border)', color: 'var(--heading)' }}>
                  {(p.name || '?').split(' ').map((w: any) => w[0]).slice(0, 2).join('').toUpperCase()}
                </div>
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div style={{ fontWeight: 800, fontSize: '0.95rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{p.name}</div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    Feeling {mood} · score {p.score}
                  </div>
                </div>
                <button
                  className="corner"
                  title={isCrisis ? 'View emergency center' : 'Open session'}
                  onClick={() => navigate(isCrisis ? '/crisis' : `/open-session?patient=${p.patient}`)}
                >↗</button>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                <span style={{ fontSize: '0.62rem', fontWeight: 800, padding: '3px 9px', borderRadius: 999, background: meta.badgeBg, color: meta.dot, border: `1px solid ${meta.dot}33`, display: 'inline-flex', alignItems: 'center', gap: 5 }}>
                  {isCrisis && <span className="live-dot" style={{ width: 6, height: 6 }} />}
                  {isCrisis ? '🚨 ACTIVE CRISIS' : meta.label}
                </span>
                <span className="dot" style={{ background: meta.dot }} />
                {p.bpm ? <span className="badge-theme">❤️ {p.bpm} bpm</span> : null}
                {p.stress ? <span className="badge-theme">🧘 stress {p.stress}</span> : null}
              </div>

              {open && (
                <div style={{ borderTop: '1px solid var(--border)', paddingTop: '10px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {p.summary && (
                    <div className="ai-box" style={{ margin: 0 }}>
                      <div className="ai-header">AI clinical insight
                        {p.ai_source && (
                          <span style={{ background: `${sourceColor(p.ai_source)}22`, color: sourceColor(p.ai_source), fontSize: '0.6rem', padding: '1px 7px', borderRadius: 999, fontWeight: 700, border: `1px solid ${sourceColor(p.ai_source)}44`, marginLeft: '6px' }}>{p.ai_source.toUpperCase()}</span>
                        )}
                      </div>
                      <div className="ai-body">{p.summary}</div>
                      {p.emotions && <div style={{ color: 'var(--muted)', fontSize: '0.65rem', marginTop: '4px' }}>Detected: {p.emotions}</div>}
                    </div>
                  )}

                  <button style={{ fontSize: '0.72rem', width: '100%' }} onClick={() => setExplainOpen({ ...explainOpen, [p.patient]: !explainOpen[p.patient] })}>
                    🔍 Why this summary?
                  </button>
                  {explainOpen[p.patient] && (
                    <div className="card-sm" style={{ background: 'var(--surface-soft)' }}>
                      <div style={{ color: 'var(--accent)', fontSize: '0.65rem', fontWeight: 800, marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Explainability</div>
                      <div style={{ color: 'var(--soft)', fontSize: '0.68rem', lineHeight: 1.6 }}>
                        AI Source: <strong>{p.ai_source ? p.ai_source.charAt(0).toUpperCase() + p.ai_source.slice(1) : 'N/A'}</strong><br />
                        Prompt Mode: <strong>Clinical Summarization</strong><br />
                        {p.emotions ? `Detected Emotions: ${p.emotions}\n` : ''}
                        Generated by {p.ai_source || 'rule-based'} inference with a clinical documentation prompt. No raw journal text is exposed — privacy preserved.
                      </div>
                    </div>
                  )}

                  {p.last_raw && (
                    riskAssessments[p.patient] ? (
                      <div className="card-sm" style={{ borderColor: riskAssessments[p.patient].triggered ? 'var(--danger)' : 'color-mix(in srgb, var(--ok) 27%, transparent)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                          <div style={{ color: riskAssessments[p.patient].triggered ? 'var(--danger)' : 'var(--ok)', fontSize: '0.68rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Crisis risk</div>
                          <div style={{ color: riskAssessments[p.patient].triggered ? 'var(--danger)' : 'var(--ok)', fontSize: '1.05rem', fontWeight: 800 }}>{riskAssessments[p.patient].risk_score || '?'}/10</div>
                        </div>
                        <div style={{ color: 'var(--soft)', fontSize: '0.68rem', lineHeight: 1.6 }}>{riskAssessments[p.patient].reasoning || 'No reasoning available.'}</div>
                      </div>
                    ) : (
                      <button style={{ fontSize: '0.72rem', width: '100%' }} onClick={() => assessRisk(p.patient, p.last_raw)}>⚠️ Assess crisis risk</button>
                    )
                  )}

                  {/* Session readiness */}
                  {readiness[p.patient] ? (
                    <div className="card-sm" style={{ background: 'var(--surface-soft)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                        <div style={{ color: 'var(--accent)', fontSize: '0.68rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Session readiness</div>
                        <ReadinessRing score={readiness[p.patient].score} band={readiness[p.patient].band} />
                      </div>
                      {readiness[p.patient].factors.slice(0, 4).map((f: any) => (
                        <div key={f.factor} title={f.detail} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.64rem', color: 'var(--soft)', marginBottom: '2px' }}>
                          <span style={{ width: '110px', flexShrink: 0 }}>{f.factor}</span>
                          <div style={{ flex: 1, height: 4, borderRadius: 999, background: 'var(--border)' }}>
                            <div style={{ width: `${(f.points / f.max_points) * 100}%`, height: '100%', borderRadius: 999, background: 'var(--accent)' }} />
                          </div>
                          <span style={{ width: '28px', textAlign: 'right' }}>{f.points}/{f.max_points}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <button style={{ fontSize: '0.72rem', width: '100%' }} onClick={() => loadReadiness(p.patient)}>
                      🩺 How ready are they for a session?
                    </button>
                  )}

                  {/* Recommend a coping tool */}
                  {recommending === p.patient ? (
                    <div className="card-sm" style={{ background: 'var(--surface-soft)', display: 'flex', gap: '6px', flexWrap: 'wrap', alignItems: 'center' }}>
                      <input value={recTitle} onChange={e => setRecTitle(e.target.value)} placeholder="Strategy to suggest…" style={{ flex: 1, minWidth: '140px', fontSize: '0.75rem' }} />
                      <select value={recCategory} onChange={e => setRecCategory(e.target.value)} style={{ fontSize: '0.72rem' }}>
                        <option value="calming">😌 Calming</option>
                        <option value="distraction">🎧 Distraction</option>
                        <option value="physical">🏃 Physical</option>
                        <option value="social">💬 Social</option>
                        <option value="professional">🧑‍⚕️ Professional</option>
                      </select>
                      <button className="btn-primary" style={{ fontSize: '0.72rem', padding: '5px 12px' }} onClick={() => recommendTool(p.patient)}>Send</button>
                      <button style={{ fontSize: '0.72rem' }} onClick={() => setRecommending('')}>Cancel</button>
                    </div>
                  ) : (
                    <button style={{ fontSize: '0.72rem', width: '100%' }} onClick={() => { setRecommending(p.patient); setRecTitle('') }}>
                      🧰 Suggest a coping strategy
                    </button>
                  )}

                  {(p.email || p.trusted_contact) && (
                    <div style={{ fontSize: '0.65rem', color: 'var(--muted)', lineHeight: 1.6 }}>
                      {p.email ? `📧 ${p.email}` : ''}{p.email && p.trusted_contact ? ' · ' : ''}{p.trusted_contact ? `👤 TC: ${p.trusted_contact}` : ''}
                    </div>
                  )}
                </div>
              )}

              <div style={{ display: 'flex', gap: '8px', marginTop: 'auto' }}>
                <button style={{ flex: 1, fontSize: '0.75rem' }} onClick={() => setExpanded({ ...expanded, [p.patient]: !open })}>
                  {open ? 'Collapse' : 'Details'}
                </button>
                <button className="btn-primary" style={{ flex: 1, fontSize: '0.75rem' }} onClick={() => navigate(`/open-session?patient=${p.patient}`)}>
                  Open session
                </button>
              </div>
            </div>
          )
        })}
      </div>

      {priorities.length === 0 && (
        <FloatingEmpty emoji="🪴" title="No clients registered yet" sub="Clients appear here after they register and are assigned to you." />
      )}
    </div>
  )
}

function ReadinessRing({ score, band }: { score: number; band: string }) {
  const color = (READINESS_META[band] || READINESS_META.medium).color
  const r = 15
  const c = 2 * Math.PI * r
  const [offset, setOffset] = useState(c)
  useEffect(() => {
    const t = window.setTimeout(() => setOffset(c - (score / 100) * c), 60)
    return () => window.clearTimeout(t)
  }, [score])
  return (
    <span className="readiness-ring" style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
      <svg width="38" height="38" viewBox="0 0 38 38" aria-hidden>
        <circle className="ring-track" cx="19" cy="19" r={r} fill="none" strokeWidth="3.5" />
        <circle
          className="ring-fill"
          cx="19" cy="19" r={r} fill="none" strokeWidth="3.5"
          stroke={color}
          strokeDasharray={c}
          strokeDashoffset={offset}
        />
        <text x="19" y="23" textAnchor="middle" fontSize="10" fontWeight="800" fill={color}>{score}</text>
      </svg>
      <span style={{ color, fontSize: '0.66rem', fontWeight: 800 }}>/100</span>
    </span>
  )
}
