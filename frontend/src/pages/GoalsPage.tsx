import { useEffect, useState } from 'react'
import CustomSelect from '../components/CustomSelect'
import { api } from '../api/client'
import { MOODS } from '../constants'

// eslint-disable-next-line @typescript-eslint/no-unused-vars
const _MOODS = MOODS

/**
 * Goals & Skills — NEW FEATURE (patient-facing, local-first)
 * Two tabs:
 *  1. My Goals — small wellness goals with streak tracking, stored locally
 *     (localStorage) so it works offline and needs no backend migration.
 *  2. Skills Toolbox — guided coping exercises (box breathing, grounding,
 *     muscle relaxation) with animated timers the client can run in-session
 *     or between sessions.
 */

interface Goal {
  id: string
  title: string
  cadence: 'daily' | 'weekly'
  created: string
  done: string[] // ISO dates completed
  archived?: boolean
}

const GOALS_KEY = 'sentinel-goals-v1'

function todayISO() { return new Date().toISOString().slice(0, 10) }

function loadGoals(): Goal[] {
  try {
    const raw = localStorage.getItem(GOALS_KEY)
    if (raw) return JSON.parse(raw)
  } catch {}
  // Seed with gentle defaults the first time
  return [
    { id: 'g1', title: 'Journal 3× per week', cadence: 'weekly', created: todayISO(), done: [] },
    { id: 'g2', title: 'Sleep before midnight', cadence: 'daily', created: todayISO(), done: [] },
  ]
}

function streakOf(goal: Goal): number {
  const set = new Set(goal.done)
  let streak = 0
  const d = new Date()
  // Allow today to be incomplete without breaking the streak count from yesterday
  if (!set.has(d.toISOString().slice(0, 10))) d.setDate(d.getDate() - 1)
  for (;;) {
    const key = d.toISOString().slice(0, 10)
    if (set.has(key)) {
      streak++
      if (goal.cadence === 'weekly') d.setDate(d.getDate() - 7)
      else d.setDate(d.getDate() - 1)
    } else break
  }
  return streak
}

const SKILLS = [
  {
    id: 'box',
    name: 'Box breathing',
    emoji: '🫁',
    tagline: '4-4-4-4 · calm your nervous system in 2 minutes',
    pattern: [4, 4, 4, 4],
    labels: ['Breathe in', 'Hold', 'Breathe out', 'Hold'],
    color: 'var(--info)',
  },
  {
    id: 'ground',
    name: '5-4-3-2-1 Grounding',
    emoji: '🌍',
    tagline: 'Anchor to the room when anxiety spikes',
    pattern: [0, 0, 0, 0, 0],
    labels: ['5 things you SEE', '4 you FEEL', '3 you HEAR', '2 you SMELL', '1 you TASTE'],
    color: 'var(--ok)',
    selfPaced: true,
  },
  {
    id: 'pmr',
    name: 'Muscle release',
    emoji: '💪',
    tagline: 'Tense & release, head to toe',
    pattern: [5, 10, 5, 10],
    labels: ['Tense', 'Hold', 'Release', 'Rest'],
    color: 'var(--violet)',
  },
]

export default function GoalsPage() {
  const [tab, setTab] = useState<'goals' | 'skills'>('goals')
  const [goals, setGoals] = useState<Goal[]>(loadGoals)
  const [newTitle, setNewTitle] = useState('')
  const [newCadence, setNewCadence] = useState<'daily' | 'weekly'>('daily')
  const [suggestions, setSuggestions] = useState<any>(null)
  const [suggLoading, setSuggLoading] = useState(false)

  function loadSuggestions() {
    setSuggLoading(true)
    api.getGoalSuggestions().then(setSuggestions).catch(() => {}).finally(() => setSuggLoading(false))
  }

  function addSuggested(title: string) {
    if (goals.some(g => g.title.toLowerCase() === title.toLowerCase())) return
    persist([...goals, { id: `g${Date.now()}`, title, cadence: 'daily', created: todayISO(), done: [] }])
  }

  function persist(next: Goal[]) {
    setGoals(next)
    try { localStorage.setItem(GOALS_KEY, JSON.stringify(next)) } catch {}
  }

  function addGoal() {
    if (!newTitle.trim()) return
    persist([...goals, { id: `g${Date.now()}`, title: newTitle.trim(), cadence: newCadence, created: todayISO(), done: [] }])
    setNewTitle('')
  }

  function toggleToday(id: string) {
    persist(goals.map(g => {
      if (g.id !== id) return g
      const has = g.done.includes(todayISO())
      return { ...g, done: has ? g.done.filter(d => d !== todayISO()) : [...g.done, todayISO()] }
    }))
  }

  function removeGoal(id: string) {
    persist(goals.filter(g => g.id !== id))
  }

  const doneToday = goals.filter(g => g.done.includes(todayISO())).length
  const bestStreak = Math.max(0, ...goals.map(streakOf))

  return (
    <div className="animate-fade-in">
      <div className="segmented-control">
        <button className={`segmented-btn${tab === 'goals' ? ' active' : ''}`} onClick={() => setTab('goals')}>🎯 My goals</button>
        <button className={`segmented-btn${tab === 'skills' ? ' active' : ''}`} onClick={() => setTab('skills')}>🧰 Skills toolbox</button>
      </div>

      {tab === 'goals' && (
        <>
          <div className="card-lime" style={{ padding: '22px 24px', display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap', marginBottom: '14px' }}>
            <div style={{ fontSize: '2.2rem' }}>{doneToday === goals.length && goals.length > 0 ? '🌿' : '🎯'}</div>
            <div style={{ flex: 1, minWidth: '180px' }}>
              <h2 style={{ margin: 0, color: 'var(--lime-ink) !important' }}>
                {doneToday === goals.length && goals.length > 0 ? 'All goals done today — beautiful.' : `${doneToday} of ${goals.length} done today`}
              </h2>
              <div style={{ fontSize: '0.8rem', opacity: 0.78 }}>Longest active streak: {bestStreak} day{bestStreak === 1 ? '' : 's'} 🔥</div>
            </div>
          </div>

          <div className="card" style={{ padding: '18px', marginBottom: '14px' }}>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              <input placeholder="Add a small goal… e.g. 'walk 15 minutes'" value={newTitle} onChange={e => setNewTitle(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') addGoal() }} style={{ flex: 1, minWidth: '200px' }} />
              <CustomSelect
                value={newCadence}
                onChange={v => setNewCadence(v as any)}
                style={{ width: '130px' }}
                options={[{ value: 'daily', label: 'Daily' }, { value: 'weekly', label: 'Weekly' }]}
              />
              <button className="btn-primary" onClick={addGoal} disabled={!newTitle.trim()}>＋ Add</button>
            </div>
          </div>

          {/* AI goal coach */}
          <div className="card" style={{ padding: '16px 18px', marginBottom: '14px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: suggestions ? '10px' : '0', flexWrap: 'wrap' }}>
              <h3 style={{ margin: 0 }}>✨ Goal coach</h3>
              {suggestions?.source === 'ai' && <span className="badge-theme">AI</span>}
              <button className="btn-primary" style={{ marginLeft: 'auto', padding: '6px 14px', fontSize: '0.75rem' }} onClick={loadSuggestions} disabled={suggLoading}>
                {suggLoading ? 'Thinking…' : suggestions ? '🔄 Refresh' : 'Suggest 3 tiny goals'}
              </button>
            </div>
            {suggestions && (
              <>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '8px' }}>
                  {suggestions.suggestions.map((s: any, i: number) => (
                    <div key={i} style={{ background: 'var(--accent-soft)', border: '1px solid var(--accent)', borderRadius: '12px', padding: '12px' }}>
                      <div style={{ fontSize: '0.8rem', fontWeight: 800, color: 'var(--text)' }}>{s.title}</div>
                      <div style={{ fontSize: '0.7rem', color: 'var(--muted)', marginTop: '4px', lineHeight: 1.45 }}>{s.why}</div>
                      <button className="btn-primary" style={{ marginTop: '8px', padding: '4px 12px', fontSize: '0.7rem', width: '100%' }}
                        onClick={() => addSuggested(s.title)} disabled={goals.some(g => g.title.toLowerCase() === s.title.toLowerCase())}>
                        {goals.some(g => g.title.toLowerCase() === s.title.toLowerCase()) ? '✓ Added' : '＋ Add for me'}
                      </button>
                    </div>
                  ))}
                </div>
                <div style={{ fontSize: '0.62rem', color: 'var(--muted)', marginTop: '8px' }}>{suggestions.note}</div>
              </>
            )}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: '12px' }}>
            {goals.map(g => {
              const streak = streakOf(g)
              const done = g.done.includes(todayISO())
              const last7 = Array.from({ length: 7 }, (_, i) => {
                const d = new Date(); d.setDate(d.getDate() - (6 - i))
                return d.toISOString().slice(0, 10)
              })
              return (
                <div key={g.id} className={`lead-card${done ? ' lime' : ''}`}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <strong style={{ fontSize: '0.92rem', color: done ? 'var(--lime-ink)' : 'var(--heading)', flex: 1 }}>{g.title}</strong>
                    <button className="corner" title="Remove goal" onClick={() => removeGoal(g.id)}>✕</button>
                  </div>
                  <div style={{ display: 'flex', gap: '6px', alignItems: 'center', flexWrap: 'wrap' }}>
                    <span className="badge-theme">{g.cadence}</span>
                    {streak > 0 && <span style={{ fontSize: '0.68rem', fontWeight: 800, color: done ? 'var(--lime-ink)' : 'var(--warn)' }}>🔥 {streak} streak</span>}
                  </div>
                  <div style={{ display: 'flex', gap: '4px' }}>
                    {last7.map(d => {
                      const has = g.done.includes(d)
                      return (
                        <div key={d} title={d} style={{
                          flex: 1, height: 26, borderRadius: 8,
                          background: has ? (done ? 'rgba(0,0,0,0.2)' : 'var(--lime-deep)') : 'var(--surface-soft-2)',
                          border: `1px solid ${has ? 'transparent' : 'var(--border)'}`,
                        }} />
                      )
                    })}
                  </div>
                  <button className={done ? 'btn-primary' : 'btn-lime'} style={{ fontSize: '0.78rem', marginTop: 'auto' }} onClick={() => toggleToday(g.id)}>
                    {done ? '✓ Done today' : 'Mark done today'}
                  </button>
                </div>
              )
            })}
          </div>
          {goals.length === 0 && (
            <div className="card" style={{ textAlign: 'center', padding: '30px', color: 'var(--muted)' }}>
              No goals yet — small and specific beats big and vague. 🌱
            </div>
          )}
        </>
      )}

      {tab === 'skills' && <SkillsToolbox />}
    </div>
  )
}

function SkillsToolbox() {
  const [activeSkill, setActiveSkill] = useState<any>(null)
  const [phase, setPhase] = useState(0)
  const [secondsLeft, setSecondsLeft] = useState(0)
  const [running, setRunning] = useState(false)
  const [cycles, setCycles] = useState(0)

  function start(skill: any) {
    setActiveSkill(skill)
    setPhase(0)
    setCycles(0)
    setSecondsLeft(skill.pattern[0] || 0)
    setRunning(!skill.selfPaced)
  }

  function stop() {
    setRunning(false)
    setActiveSkill(null)
  }

  // Phase timer
  return (
    <div>
      <div className="card-sm" style={{ marginBottom: '14px', background: 'var(--accent-soft)', borderColor: 'color-mix(in srgb, var(--accent) 22%, transparent)' }}>
        <div style={{ fontSize: '0.78rem', color: 'var(--secondary)', lineHeight: 1.6 }}>
          🧰 Evidence-informed coping exercises you can run anywhere — before a session, after school, or mid-panic. These are tools, not treatment.
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: '12px' }}>
        {SKILLS.map(s => (
          <div key={s.id} className="lead-card" style={{ cursor: 'pointer' }} onClick={() => start(s)}>
            <div style={{ fontSize: '2rem' }}>{s.emoji}</div>
            <strong style={{ fontSize: '0.95rem' }}>{s.name}</strong>
            <div style={{ fontSize: '0.74rem', color: 'var(--muted)', lineHeight: 1.5 }}>{s.tagline}</div>
            <button className="btn-lime" style={{ fontSize: '0.78rem', marginTop: 'auto' }}>Start exercise →</button>
          </div>
        ))}
      </div>

      {activeSkill && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(10,12,8,0.72)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 999, padding: '20px' }}
          onClick={stop}>
          <div className="card" style={{ maxWidth: '440px', width: '100%', textAlign: 'center', padding: '34px 30px' }} onClick={e => e.stopPropagation()}>
            <div style={{ fontSize: '2.2rem', marginBottom: '4px' }}>{activeSkill.emoji}</div>
            <h3 style={{ marginBottom: '2px' }}>{activeSkill.name}</h3>
            <div style={{ color: 'var(--muted)', fontSize: '0.76rem', marginBottom: '18px' }}>{activeSkill.tagline}</div>

            {activeSkill.selfPaced ? (
              <div className="space-y-2">
                {activeSkill.labels.map((l: string, i: number) => (
                  <div key={i} className="card-sm" style={{ textAlign: 'left', padding: '11px 14px' }}>
                    <strong style={{ color: activeSkill.color }}>{l}</strong>
                  </div>
                ))}
                <button className="btn-primary btn-full" style={{ marginTop: '10px' }} onClick={stop}>Done — I feel steadier</button>
              </div>
            ) : (
              <BreathRunner skill={activeSkill} onDone={(c: number) => { setCycles(c) }} />
            )}

            {!activeSkill.selfPaced && (
              <button className="btn-ghost" style={{ marginTop: '12px', fontSize: '0.75rem' }} onClick={stop}>End exercise</button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function BreathRunner({ skill, onDone }: { skill: any; onDone: (cycles: number) => void }) {
  const [phase, setPhase] = useState(0)
  const [left, setLeft] = useState(skill.pattern[0])
  const [cycles, setCycles] = useState(0)

  useEffect(() => {
    if (left <= 0) {
      const next = (phase + 1) % skill.pattern.length
      if (next === 0) {
        const c = cycles + 1
        setCycles(c)
        onDone(c)
      }
      setPhase(next)
      setLeft(skill.pattern[next])
      return
    }
    const t = setTimeout(() => setLeft((l: number) => l - 1), 1000)
    return () => clearTimeout(t)
  }, [left, phase])

  const scale = skill.id === 'box' || skill.id === 'pmr'
    ? (phase === 0 || phase === 1 ? 1 + (skill.pattern[0] - left) / (skill.pattern[0] * 2) : 1.5 - (skill.pattern[2] - left) / (skill.pattern[2] * 2))
    : 1

  return (
    <div>
      <div style={{ height: '150px', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '10px' }}>
        <div style={{
          width: '110px', height: '110px', borderRadius: 999,
          background: `radial-gradient(circle, ${skill.color} 0%, transparent 75%)`,
          transform: `scale(${Math.max(0.7, Math.min(1.6, scale))})`,
          transition: 'transform 1s linear',
        }} />
      </div>
      <div style={{ fontSize: '1.3rem', fontWeight: 800, color: skill.color }}>{skill.labels[phase]}</div>
      <div style={{ fontSize: '2.4rem', fontWeight: 800, color: 'var(--heading)' }}>{left > 0 ? left : '•'}</div>
      <div style={{ color: 'var(--muted)', fontSize: '0.74rem', marginTop: '6px' }}>Cycles completed: {cycles} 🌊</div>
    </div>
  )
}
