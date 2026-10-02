import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { MOODS, moodColor, moodScore, sourceColor, todayStr, formatDateTime } from '../constants'
import MoodPicker from '../components/MoodPicker'

/** AI/personalized writing nudge shown above the journal editor. */
function ReflectPromptCard({ onUse }: { onUse: (text: string) => void }) {
  const [data, setData] = useState<any>(null)

  useEffect(() => {
    api.getReflectPrompt().then(setData).catch(() => {})
  }, [])

  if (!data?.prompt) return null
  return (
    <div className="card-sm" style={{ background: 'var(--accent-soft)', borderColor: 'color-mix(in srgb, var(--accent) 25%, transparent)', marginBottom: '16px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
        <span style={{ color: 'var(--accent)', fontWeight: 800, fontSize: '0.64rem', textTransform: 'uppercase', letterSpacing: '0.08em' }}>🪞 Today&apos;s reflection nudge</span>
        {data.source === 'ai' && <span className="badge-theme" style={{ fontSize: '0.58rem' }}>AI</span>}
      </div>
      <div style={{ color: 'var(--heading)', fontSize: '0.95rem', fontWeight: 700, lineHeight: 1.45, marginBottom: '4px' }}>{data.prompt}</div>
      {data.why && <div style={{ color: 'var(--secondary)', fontSize: '0.72rem', lineHeight: 1.5, marginBottom: '10px' }}>{data.why}</div>}
      <button style={{ fontSize: '0.72rem', padding: '5px 12px' }} onClick={() => onUse(`${data.prompt}\n\n`)}>
        ✍️ Start with this
      </button>
    </div>
  )
}

export default function JournalPage() {
  const [text, setText] = useState('')
  const [entries, setEntries] = useState<any[]>([])
  const [reframes, setReframes] = useState<Record<number, any>>({})
  const [reframeLoading, setReframeLoading] = useState<number | null>(null)
  const [saving, setSaving] = useState(false)
  const [lastSummary, setLastSummary] = useState('')
  const [lastSource, setLastSource] = useState('')
  const [lastEmotions, setLastEmotions] = useState('')
  const [todayMood, setTodayMood] = useState<any>(null)
  const [moodLocked, setMoodLocked] = useState(false)
  const [moodHistory, setMoodHistory] = useState<any[]>([])
  const [expandedEntries, setExpandedEntries] = useState<Set<number>>(new Set())
  const [tab, setTab] = useState<'write' | 'history'>('write')
  const [savedOffline, setSavedOffline] = useState(false)
  const [prompts, setPrompts] = useState<any[]>([])
  const [answers, setAnswers] = useState<Record<string, string>>({})

  const [fEmotion, setFEmotion] = useState('')
  const [fDateFrom, setFDateFrom] = useState('')
  const [fDateTo, setFDateTo] = useState('')

  async function load() {
    try {
      const data = await api.getJournals({ emotion: fEmotion, date_from: fDateFrom, date_to: fDateTo })
      setEntries(data?.items || data || [])
    } catch {}
    try {
      const t = await api.checkTodayMood()
      setMoodLocked(t.logged ?? false)
    } catch {}
    try {
      const mh = await api.getMoods()
      if (Array.isArray(mh)) {
        setMoodHistory(mh)
        const tm = mh.find((m: any) => (m.date || '').slice(0, 10) === todayStr())
        if (tm) setTodayMood(tm)
      }
    } catch {}
    try {
      const p = await api.getJournalPrompts()
      if (Array.isArray(p?.prompts)) setPrompts(p.prompts)
    } catch {}
  }

  useEffect(() => { load() }, [fEmotion, fDateFrom, fDateTo])

  async function handleMood(label: string) {
    if (moodLocked) return
    const m = MOODS.find(x => x.label === label)
    if (!m) return
    try {
      await api.logMood(todayStr(), m.emoji, m.label)
      setTodayMood(m)
      setMoodLocked(true)
    } catch {}
  }

  async function handleSave() {
    if (!text.trim()) return
    setSaving(true)
    try {
      const checkin = prompts
        .filter(p => answers[p.key])
        .map(p => ({ question: p.question, answer: answers[p.key] }))
      const res = await api.createJournal(text.trim(), checkin)
      setAnswers({})
      if (res?.queued) {
        setLastSummary('')
        setLastSource('')
        setLastEmotions('')
        setText('')
        setSavedOffline(true)
        setTimeout(() => setSavedOffline(false), 4000)
        await load()
        return
      }
      setLastSummary(res.summary || '')
      setLastSource(res.ai_source || '')
      setLastEmotions(res.emotions || '')
      setText('')
      await load()
    } catch (err: any) {
      alert(err.message)
    } finally {
      setSaving(false)
    }
  }

  function toggleExpanded(id: number) {
    setExpandedEntries(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id); else next.add(id)
      return next
    })
  }

  const wordCount = text.trim() ? text.trim().split(/\s+/).length : 0
  const charCount = text.length

  const recentMoods = moodHistory
    .filter(m => m.date && m.label)
    .sort((a, b) => (a.date || '').localeCompare(b.date || ''))
    .slice(-14)

  return (
    <div className="space-y-4 animate-fade-in">
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.6fr', gap: '14px', alignItems: 'start' }} className="journal-grid">
        {/* Left column — mood + prompts */}
        <div className="space-y-4">
          <div className="card" data-tour="journal">
            <div style={{ fontSize: '0.7rem', fontWeight: 800, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.09em', marginBottom: '12px' }}>Daily check-in</div>
            {todayMood ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '12px 14px', borderRadius: '14px', background: `${moodColor(todayMood.label)}0d`, border: `1px solid ${moodColor(todayMood.label)}33` }}>
                <span style={{ fontSize: '1.5rem', lineHeight: 1 }}>{todayMood.emoji}</span>
                <div>
                  <div style={{ fontWeight: 800, fontSize: '0.95rem', textTransform: 'capitalize', color: moodColor(todayMood.label) }}>{todayMood.label}</div>
                  <div style={{ fontSize: '0.6875rem', color: 'var(--muted)' }}>Next check-in unlocks tomorrow</div>
                </div>
              </div>
            ) : (
              <div>
                <div style={{ color: 'var(--soft)', fontSize: '0.85rem', marginBottom: '12px' }}>How are you feeling right now?</div>
                <MoodPicker locked={moodLocked} onSelect={handleMood} />
              </div>
            )}
          </div>

          {recentMoods.length >= 3 && (
            <div className="card">
              <div style={{ fontSize: '0.7rem', fontWeight: 800, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.09em', marginBottom: '8px' }}>Mood · last 14 days</div>
              <svg viewBox="0 0 280 50" style={{ width: '100%', height: '50px', overflow: 'visible' }}>
                <defs>
                  <linearGradient id="moodFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="rgba(215,246,91,0.35)" />
                    <stop offset="100%" stopColor="rgba(215,246,91,0)" />
                  </linearGradient>
                </defs>
                {(() => {
                  const pts = recentMoods.map((m, i) => {
                    const x = 20 + (i / Math.max(recentMoods.length - 1, 1)) * 240
                    const y = 45 - (moodScore(m.label) / 5) * 35
                    return { x, y, label: m.label }
                  })
                  const linePath = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')
                  const fillPath = linePath + ` L${pts[pts.length - 1].x},45 L${pts[0].x},45 Z`
                  return (
                    <>
                      <path d={fillPath} fill="url(#moodFill)" />
                      <path d={linePath} fill="none" stroke="var(--accent)" strokeWidth="2" />
                      {pts.map((p, i) => (
                        <circle key={i} cx={p.x} cy={p.y} r="3.5" fill={moodColor(p.label)} stroke="var(--surface)" strokeWidth="1.2" />
                      ))}
                    </>
                  )
                })()}
              </svg>
            </div>
          )}
        </div>

        {/* Right column — write + history */}
        <div className="space-y-4">
          <div className="segmented-control">
            <button className={`segmented-btn${tab === 'write' ? ' active' : ''}`} onClick={() => setTab('write')}>✍️ Write</button>
            <button className={`segmented-btn${tab === 'history' ? ' active' : ''}`} onClick={() => setTab('history')}>📖 Past entries</button>
          </div>

          {tab === 'write' && (
            <div className="card" style={{ padding: '22px' }}>
              <ReflectPromptCard onUse={setText} />
              {prompts.length > 0 && (
                <div style={{ marginBottom: '16px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  <div style={{ fontSize: '0.7rem', fontWeight: 800, color: 'var(--accent)', textTransform: 'uppercase', letterSpacing: '0.09em' }}>✨ Quick check-in cards</div>
                  {prompts.map(p => (
                    <div key={p.key} style={{ border: '1px solid var(--border)', borderRadius: '16px', padding: '13px 15px', background: 'var(--surface-soft)' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                        <span style={{ fontSize: '1.25rem', lineHeight: 1 }}>{p.emoji}</span>
                        <div>
                          <div style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--heading)' }}>{p.question}</div>
                          {p.title && <div style={{ fontSize: '0.68rem', color: 'var(--muted)' }}>{p.title}</div>}
                        </div>
                      </div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                        {(p.options || []).map((opt: string) => {
                          const sel = answers[p.key] === opt
                          return (
                            <button
                              key={opt} type="button"
                              className={`chip${sel ? ' active' : ''}`}
                              onClick={() => setAnswers(a => {
                                if (a[p.key] === opt) { const n = { ...a }; delete n[p.key]; return n }
                                return { ...a, [p.key]: opt }
                              })}
                            >
                              {sel ? '✓ ' : ''}{opt}
                            </button>
                          )
                        })}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <textarea
                value={text}
                onChange={e => setText(e.target.value)}
                placeholder={prompts.length > 0 ? 'Anything else on your mind? Write freely…' : 'What\'s on your mind? Write freely…'}
                rows={8}
                style={{ width: '100%', padding: '14px', fontSize: '0.9rem', resize: 'none', lineHeight: 1.65, borderRadius: '16px' }}
              />
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginTop: '10px' }}>
                <span style={{ color: 'var(--faint)', fontSize: '0.72rem', fontWeight: 600 }}>{wordCount} words · {charCount} chars</span>
                <button onClick={handleSave} disabled={saving || !text.trim()} className="btn-primary" style={{ marginLeft: 'auto', padding: '10px 22px' }}>
                  {saving ? 'Saving…' : '💾 Save entry'}
                </button>
              </div>
              {savedOffline && (
                <div style={{ marginTop: '10px', padding: '9px 13px', borderRadius: '12px', background: 'var(--warn-soft)', border: '1px solid color-mix(in srgb, var(--warn) 30%, transparent)', color: 'var(--warn)', fontSize: '0.78rem', fontWeight: 600 }}>
                  📡 You're offline — entry saved on this device. It will sync automatically when you're back online.
                </div>
              )}
              {lastSummary && (
                <div className="ai-box" style={{ marginTop: '12px' }}>
                  <div className="ai-header">Sentinel reflection
                    {lastSource && (
                      <span style={{ background: `${sourceColor(lastSource)}22`, color: sourceColor(lastSource), fontSize: '0.6rem', padding: '1px 7px', borderRadius: '999px', fontWeight: 700, border: `1px solid ${sourceColor(lastSource)}44`, marginLeft: '6px' }}>{lastSource.toUpperCase()}</span>
                    )}
                  </div>
                  <div className="ai-body">{lastSummary}</div>
                  {lastEmotions && <div style={{ fontSize: '0.6875rem', color: 'var(--muted)', marginTop: '6px' }}>Emotions detected: {lastEmotions}</div>}
                </div>
              )}
            </div>
          )}

          {tab === 'history' && (
            <div>
              {/* History filters */}
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '10px', flexWrap: 'wrap' }}>
                <select value={fEmotion} onChange={e => setFEmotion(e.target.value)} style={{ fontSize: '0.78rem', maxWidth: '170px' }}>
                  <option value="">All emotions</option>
                  {['joy', 'sadness', 'anxiety', 'anger', 'calm', 'fear', 'confusion', 'gratitude', 'hope', 'neutral'].map(e => (
                    <option key={e} value={e}>{e}</option>
                  ))}
                </select>
                <input type="date" value={fDateFrom} onChange={e => setFDateFrom(e.target.value)} style={{ width: '140px', fontSize: '0.75rem' }} title="From date" />
                <span style={{ color: 'var(--muted)', fontSize: '0.72rem' }}>→</span>
                <input type="date" value={fDateTo} onChange={e => setFDateTo(e.target.value)} style={{ width: '140px', fontSize: '0.75rem' }} title="To date" />
                {(fEmotion || fDateFrom || fDateTo) && (
                  <button className="btn-ghost" style={{ fontSize: '0.72rem' }} onClick={() => { setFEmotion(''); setFDateFrom(''); setFDateTo('') }}>Clear</button>
                )}
                <span style={{ color: 'var(--faint)', fontSize: '0.72rem', marginLeft: 'auto' }}>
                  {entries.length} entr{entries.length === 1 ? 'y' : 'ies'}
                </span>
              </div>
              {entries.length === 0 && (fEmotion || fDateFrom || fDateTo) && (
                <div className="card-sm" style={{ textAlign: 'center', color: 'var(--muted)', padding: '16px' }}>No entries match these filters.</div>
              )}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {entries.slice(-20).reverse().map((e: any, i: number) => {
                  const id = e.id || i
                  const open = expandedEntries.has(id)
                  const ts = formatDateTime(e.timestamp || e.created_at || Date.now())
                  return (
                    <div key={id}>
                      <button onClick={() => toggleExpanded(id)}
                        style={{ width: '100%', padding: '10px 14px', background: open ? 'var(--accent-soft)' : 'var(--surface)', border: `1px solid ${open ? 'var(--accent)' : 'var(--border)'}`, borderRadius: '14px', color: 'var(--text)', fontSize: '0.8125rem', fontWeight: 600, cursor: 'pointer', textAlign: 'left', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span>📄 {ts}</span>
                        <span style={{ marginLeft: 'auto', color: 'var(--muted)', fontSize: '0.7rem' }}>{open ? 'Collapse' : 'Expand'}</span>
                      </button>
                      {open && (
                        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '16px', padding: '16px', margin: '4px 0 8px', boxShadow: 'var(--shadow)' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px', flexWrap: 'wrap' }}>
                            {e.ai_source && (
                              <span className="badge-theme" style={{ color: sourceColor(e.ai_source), borderColor: `${sourceColor(e.ai_source)}55` }}>{e.ai_source.toUpperCase()}</span>
                            )}
                            {e.emotions && <span style={{ fontSize: '0.65rem', color: 'var(--secondary)' }}>Emotions: {e.emotions}</span>}
                            <button onClick={async (ev) => { ev.stopPropagation(); setReframeLoading(id); try { const r = await api.getJournalReframe(id); setReframes((p: any) => ({ ...p, [id]: r })) } catch {} finally { setReframeLoading(null) }} }
                              style={{ fontSize: '0.65rem', padding: '3px 10px' }}>
                              🪄 {reframes[id] ? 'Reframe' : 'Reframe this'}
                            </button>
                            <button onClick={async (ev) => { ev.stopPropagation(); try { await api.resummarizeJournal(id); await load() } catch {} }}
                              style={{ marginLeft: 'auto', fontSize: '0.65rem', padding: '3px 10px' }}>
                              🔄 Re-summarize
                            </button>
                          </div>
                          <div style={{ color: 'var(--soft)', fontSize: '0.85rem', lineHeight: 1.6 }}>{e.summary || e.raw_content}</div>
                          {reframeLoading === id && <div style={{ marginTop: '10px', fontSize: '0.72rem', color: 'var(--muted)' }}>🪄 Thinking of another angle…</div>}
                          {reframes[id] && (
                            <div style={{ marginTop: '10px', padding: '12px 14px', borderRadius: '12px', background: 'var(--accent-soft)', border: '1px solid var(--accent)' }}>
                              <div style={{ fontSize: '0.7rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--accent)' }}>
                                🪄 {reframes[id].trap} {reframes[id].source === 'ai' ? '· AI' : ''}
                              </div>
                              <div style={{ fontSize: '0.8rem', color: 'var(--text)', lineHeight: 1.55, marginTop: '6px' }}>{reframes[id].reframe}</div>
                              <div style={{ fontSize: '0.75rem', marginTop: '8px', fontStyle: 'italic' }}>💬 “{reframes[id].affirmation}”</div>
                              <div style={{ fontSize: '0.6rem', color: 'var(--muted)', marginTop: '6px' }}>{reframes[id].disclaimer}</div>
                            </div>
 )}
                          {e.summary && e.summary !== e.raw_content && (
                            <div style={{ marginTop: '10px', padding: '8px 12px', borderRadius: '10px', background: 'var(--warn-soft)', border: '1px solid color-mix(in srgb, var(--warn) 25%, transparent)', color: 'var(--warn)', fontSize: '0.68rem', lineHeight: 1.5 }}>
                              This summary was generated by AI and has not been reviewed by a clinician. Sentinel assists monitoring — it never determines whether you are safe. If you feel unsafe, seek help immediately.
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )
                })}
                {entries.length === 0 && <p style={{ color: 'var(--muted)', fontSize: '0.875rem' }}>💬 No entries yet. Start writing — one honest paragraph is plenty.</p>}
              </div>
            </div>
          )}
        </div>
      </div>

      <style>{`
        @media (max-width: 960px) { .journal-grid { grid-template-columns: 1fr !important; } }
      `}</style>
    </div>
  )
}
