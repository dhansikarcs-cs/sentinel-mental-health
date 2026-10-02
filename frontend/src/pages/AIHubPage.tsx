import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import { useNavigate } from 'react-router-dom'
import { getUser } from '../stores/auth'

interface Msg { id: number | string; role: string; content: string; created_at?: string }

const SUGGESTIONS = [
  'Help me sort out my thoughts from today',
  'What should I focus on this week?',
  'I feel anxious about tomorrow',
  'Celebrate with me — something good happened',
]

const LEVEL_COLORS: Record<string, string> = {
  urgent: 'var(--danger)',
  watch: 'var(--warn)',
  info: 'var(--accent)',
  positive: 'var(--ok)',
}

export default function AIHubPage() {
  const navigate = useNavigate()
  const [tab, setTab] = useState<'chat' | 'insights'>('chat')

  // chat state
  const [messages, setMessages] = useState<Msg[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [plan, setPlan] = useState<any>(null)
  const [planLoading, setPlanLoading] = useState(false)
  const [error, setError] = useState('')
  const endRef = useRef<HTMLDivElement>(null)

  // insights state
  const [agentOnline, setAgentOnline] = useState<boolean | null>(null)
  const [reflect, setReflect] = useState<any>(null)
  const [forecast, setForecast] = useState<any>(null)
  const [earlyWarning, setEarlyWarning] = useState<any>(null)
  const [goals, setGoals] = useState<any[]>([])
  const [insightsLoading, setInsightsLoading] = useState(true)

  useEffect(() => {
    api.get('/agent/status').then((s: any) => setAgentOnline(!!s.agent_client_ready)).catch(() => setAgentOnline(null))
    api.get('/agent/history').then((d: any) => setMessages(Array.isArray(d?.messages) ? d.messages : [])).catch(() => {})
    api.post('/agent/weekly-plan', { focus: '' }).then(setPlan).catch(() => {})
  }, [])

  useEffect(() => {
    if (tab !== 'insights') return
    setInsightsLoading(true)
    const me = getUser()?.username || 'me'
    Promise.allSettled([
      api.get('/agents/reflect-prompt').then(setReflect),
      api.get('/agents/mood-forecast').then(setForecast),
      api.get(`/agents/early-warning/${encodeURIComponent(me)}`).then(setEarlyWarning),
      api.get('/agents/goal-suggestions').then((g: any) => setGoals(Array.isArray(g) ? g : g?.suggestions || [])),
    ]).finally(() => setInsightsLoading(false))
  }, [tab])

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, sending])

  async function send(text: string) {
    const message = text.trim()
    if (!message || sending) return
    setError('')
    setInput('')
    setMessages(prev => [...prev, { id: `local-${Date.now()}`, role: 'user', content: message }])
    setSending(true)
    try {
      const res = await api.post('/agent/chat', { message })
      setMessages(prev => [...prev, { id: `reply-${Date.now()}`, role: 'assistant', content: res.reply }])
      if (res.crisis_resources_shown) {
        setError('If you are in danger right now, please use the Emergency button — real help is one tap away.')
      }
    } catch (e: any) {
      setError(e?.message || 'Could not reach the companion just now.')
    } finally {
      setSending(false)
    }
  }

  async function newPlan() {
    setPlanLoading(true)
    try { setPlan(await api.post('/agent/weekly-plan', { focus: '' })) } catch {} finally { setPlanLoading(false) }
  }

  async function clearChat() {
    if (!window.confirm('Clear your conversation with the companion?')) return
    try {
      await api.delete('/agent/history')
      setMessages([])
    } catch (e: any) { setError(e?.message || 'Could not clear history.') }
  }

  function refreshInsights() {
    setTab('insights')
    setTimeout(() => setTab('chat'), 0)
    setTimeout(() => setTab('insights'), 0)
  }

  return (
    <div>
      {/* ══ Tab switcher ══ */}
      <div className="segmented-control" style={{ marginBottom: '16px', maxWidth: 420 }}>
        <button className={`segmented-btn${tab === 'chat' ? ' active' : ''}`} onClick={() => setTab('chat')}>💬 Companion</button>
        <button className={`segmented-btn${tab === 'insights' ? ' active' : ''}`} onClick={() => setTab('insights')}>📊 My Insights</button>
      </div>

      {tab === 'chat' ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) 300px', gap: '18px', alignItems: 'start' }}>
          {/* ══ Chat column ══ */}
          <div className="card" style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 300px)', minHeight: 440, padding: 0, overflow: 'hidden' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '14px 18px', borderBottom: '1px solid var(--border-soft)' }}>
              <span className="rail-logo" style={{ width: 34, height: 34, fontSize: '1rem' }}>✳</span>
              <div style={{ flex: 1 }}>
                <strong style={{ fontSize: '0.9rem' }}>Sentinel Companion</strong>
                <div style={{ fontSize: '0.7rem', color: 'var(--muted)' }}>
                  {agentOnline === null ? 'checking…' : agentOnline ? 'Azure AI agent · online' : 'offline mode · supportive fallbacks'}
                </div>
              </div>
              <button className="btn-ghost" style={{ fontSize: '0.72rem', padding: '5px 10px' }} onClick={clearChat}>Clear chat</button>
            </div>

            <div style={{ flex: 1, overflowY: 'auto', padding: '16px 18px', display: 'flex', flexDirection: 'column', gap: 10 }}>
              {messages.length === 0 && (
                <div style={{ color: 'var(--muted)', fontSize: '0.85rem', lineHeight: 1.6, padding: '18px 8px', textAlign: 'center' }}>
                  This is a space to think out loud with a supportive AI companion.<br />
                  It keeps this conversation private and is never a replacement for your clinician.<br />
                  <span style={{ fontSize: '0.75rem', color: 'var(--faint)' }}>In crisis? Use the red Emergency button — it alerts real people instantly.</span>
                </div>
              )}
              {messages.map(m => (
                <div key={m.id} style={{
                  alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
                  maxWidth: '78%',
                  background: m.role === 'user' ? 'var(--accent-soft)' : 'var(--surface-soft)',
                  border: `1px solid ${m.role === 'user' ? 'color-mix(in srgb, var(--accent) 30%, transparent)' : 'var(--border-soft)'}`,
                  borderRadius: m.role === 'user' ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
                  padding: '10px 14px',
                  fontSize: '0.85rem',
                  lineHeight: 1.55,
                  whiteSpace: 'pre-wrap',
                }}>
                  {m.content}
                </div>
              ))}
              {sending && <div style={{ alignSelf: 'flex-start', color: 'var(--faint)', fontSize: '0.8rem', padding: '6px 10px' }}>Companion is thinking…</div>}
              <div ref={endRef} />
            </div>

            {error && (
              <div style={{ margin: '0 18px 8px', padding: '9px 12px', borderRadius: 12, background: 'var(--danger-alpha)', color: 'var(--danger)', fontSize: '0.78rem', fontWeight: 600 }}>
                {error}
              </div>
            )}

            <div style={{ borderTop: '1px solid var(--border-soft)', padding: '12px 18px 14px' }}>
              <div style={{ display: 'flex', gap: 8, marginBottom: 8, flexWrap: 'wrap' }}>
                {SUGGESTIONS.map(s => (
                  <button key={s} className="chip" style={{ fontSize: '0.7rem' }} onClick={() => send(s)} disabled={sending}>{s}</button>
                ))}
              </div>
              <form style={{ display: 'flex', gap: 8 }} onSubmit={e => { e.preventDefault(); send(input) }}>
                <input
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  placeholder="Write anything — the companion listens…"
                  style={{ flex: 1, padding: '11px 14px', borderRadius: 14, border: '1px solid var(--border)', background: 'var(--surface-soft)', fontSize: '0.85rem' }}
                  maxLength={4000}
                />
                <button className="btn-primary" type="submit" disabled={sending || !input.trim()} style={{ padding: '11px 18px' }}>Send</button>
              </form>
            </div>
          </div>

          {/* ══ Side column: weekly plan ══ */}
          <div className="card" style={{ padding: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
              <strong style={{ fontSize: '0.85rem' }}>This week's plan</strong>
              <button className="btn-ghost" style={{ fontSize: '0.7rem', padding: '4px 10px' }} onClick={newPlan} disabled={planLoading}>
                {planLoading ? '…' : 'Refresh'}
              </button>
            </div>
            {plan ? (
              <>
                <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--accent)', marginBottom: 8 }}>{plan.theme}</div>
                <ul style={{ margin: 0, paddingLeft: 18, display: 'flex', flexDirection: 'column', gap: 7 }}>
                  {(plan.days || []).map((d: string, i: number) => (
                    <li key={i} style={{ fontSize: '0.78rem', lineHeight: 1.45, color: 'var(--secondary)' }}>{d}</li>
                  ))}
                </ul>
                <div style={{ marginTop: 10, fontSize: '0.65rem', color: 'var(--faint)' }}>source: {plan.source}</div>
              </>
            ) : (
              <div style={{ color: 'var(--faint)', fontSize: '0.78rem' }}>{planLoading ? 'Drafting…' : 'No plan yet'}</div>
            )}
            <div style={{ marginTop: 14, padding: '10px 12px', borderRadius: 12, background: 'var(--surface-soft)', fontSize: '0.68rem', color: 'var(--muted)', lineHeight: 1.5 }}>
              The companion is supportive, not clinical. It never diagnoses or prescribes, and in a crisis it will always point you to real help.
            </div>
          </div>
        </div>
      ) : (
        /* ══════════ INSIGHTS TAB ══════════ */
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 18 }}>
          {/* Reflect prompt */}
          <div className="card" style={{ padding: 16 }}>
            <strong style={{ fontSize: '0.85rem' }}>✍️ Today's reflection prompt</strong>
            {reflect ? (
              <>
                <div style={{ marginTop: 10, fontSize: '0.95rem', fontWeight: 600, lineHeight: 1.5 }}>{reflect.prompt}</div>
                {reflect.why && <div style={{ marginTop: 6, fontSize: '0.75rem', color: 'var(--muted)' }}>{reflect.why}</div>}
                <div style={{ marginTop: 10, fontSize: '0.65rem', color: 'var(--faint)' }}>source: {reflect.source}</div>
              </>
            ) : (
              <div style={{ marginTop: 10, color: 'var(--faint)', fontSize: '0.8rem' }}>{insightsLoading ? 'Loading…' : 'Unavailable'}</div>
            )}
          </div>

          {/* Mood forecast */}
          <div className="card" style={{ padding: 16 }}>
            <strong style={{ fontSize: '0.85rem' }}>🌤️ 3-day mood outlook</strong>
            {forecast ? (
              <>
                <div style={{ display: 'flex', gap: 8, marginTop: 10, flexWrap: 'wrap' }}>
                  {(forecast.forecast || []).map((f: any, i: number) => (
                    <div key={i} style={{
                      flex: 1, minWidth: 86, textAlign: 'center', padding: '10px 8px', borderRadius: 12,
                      background: f.label === 'rough' ? 'var(--danger-alpha)' : f.label === 'good' ? 'var(--ok-alpha)' : 'var(--surface-soft)',
                      fontSize: '0.78rem', fontWeight: 700,
                      color: f.label === 'rough' ? 'var(--danger)' : f.label === 'good' ? 'var(--ok)' : 'var(--secondary)',
                    }}>
                      Day +{f.day}<br />
                      <span style={{ fontSize: '0.85rem' }}>{f.label}</span>
                    </div>
                  ))}
                </div>
                <div style={{ marginTop: 10, fontSize: '0.78rem', color: 'var(--secondary)', lineHeight: 1.5 }}>{forecast.summary}</div>
                {forecast.tip && <div style={{ marginTop: 6, fontSize: '0.72rem', color: 'var(--muted)' }}>💡 {forecast.tip}</div>}
                <div style={{ marginTop: 8, fontSize: '0.65rem', color: 'var(--faint)' }}>source: {forecast.source}</div>
              </>
            ) : (
              <div style={{ marginTop: 10, color: 'var(--faint)', fontSize: '0.8rem' }}>{insightsLoading ? 'Loading…' : 'Unavailable'}</div>
            )}
          </div>

          {/* Early warning */}
          <div className="card" style={{ padding: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <strong style={{ fontSize: '0.85rem' }}>🛰️ Early-warning signals</strong>
              <button className="btn-ghost" style={{ fontSize: '0.7rem', padding: '4px 10px' }} onClick={refreshInsights}>Refresh</button>
            </div>
            {earlyWarning ? (
              (earlyWarning.signals || []).length === 0 ? (
                <div style={{ marginTop: 10, color: 'var(--ok)', fontSize: '0.8rem', fontWeight: 600 }}>✓ Nothing flagged — steady as she goes</div>
                ) : (
                <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {(earlyWarning.signals || []).map((s: any, i: number) => (
                    <div key={i} style={{ padding: '9px 12px', borderRadius: 12, borderLeft: `3px solid ${LEVEL_COLORS[s.level] || 'var(--accent)'}`, background: 'var(--surface-soft)' }}>
                      <div style={{ fontSize: '0.8rem', fontWeight: 700 }}>{s.signal}</div>
                      <div style={{ fontSize: '0.72rem', color: 'var(--muted)', marginTop: 2 }}>{s.evidence}</div>
                    </div>
                  ))}
                </div>
              )
            ) : (
              <div style={{ marginTop: 10, color: 'var(--faint)', fontSize: '0.8rem' }}>{insightsLoading ? 'Loading…' : 'Unavailable'}</div>
            )}
          </div>

          {/* Goal suggestions */}
          <div className="card" style={{ padding: 16 }}>
            <strong style={{ fontSize: '0.85rem' }}>🎯 Suggested micro-goals</strong>
            {goals.length > 0 ? (
              <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 8 }}>
                {goals.map((g: any, i: number) => (
                  <div key={i} style={{ padding: '9px 12px', borderRadius: 12, background: 'var(--surface-soft)' }}>
                    <div style={{ fontSize: '0.8rem', fontWeight: 700 }}>{g.title}</div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--muted)', marginTop: 2 }}>{g.why}</div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ marginTop: 10, color: 'var(--faint)', fontSize: '0.8rem' }}>{insightsLoading ? 'Loading…' : 'No suggestions yet'}</div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
