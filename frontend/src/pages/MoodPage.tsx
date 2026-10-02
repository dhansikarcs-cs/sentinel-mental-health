import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { MOODS } from '../constants'
import MoodPicker from '../components/MoodPicker'

export default function MoodPage() {
  const [logs, setLogs] = useState<any[]>([])
  const [todayDone, setTodayDone] = useState(false)
  const [todayLabel, setTodayLabel] = useState('')
  const [savedOffline, setSavedOffline] = useState(false)

  async function load() {
    try {
      const data = await api.getMoods()
      setLogs(data || [])
      const today = (data || []).find((m: any) => (m.date || '').slice(0, 10) === new Date().toISOString().split('T')[0])
      if (today) setTodayLabel(today.label)
    } catch {}
    try {
      const t = await api.checkTodayMood()
      setTodayDone(t.logged ?? false)
    } catch {}
  }

  useEffect(() => { load() }, [])

  async function handleMood(label: string) {
    const m = MOODS.find(x => x.label === label)
    if (!m) return
    const date = new Date().toISOString().split('T')[0]
    try {
      const res = await api.logMood(date, m.emoji, m.label)
      setTodayDone(true)
      setTodayLabel(m.label)
      if (res?.queued) setSavedOffline(true)
      await load()
    } catch (err: any) {
      alert(err.message)
    }
  }

  const monthName = new Date().toLocaleDateString('en-US', { month: 'long', year: 'numeric' })

  return (
    <div className="space-y-6 animate-fade-in">
      {!todayDone ? (
        <div className="card-lime" style={{ padding: '30px', textAlign: 'center' }}>
          <div style={{ fontSize: '0.72rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.1em', opacity: 0.7 }}>Daily check-in</div>
          <h2 style={{ fontSize: '1.7rem', margin: '8px 0 6px', color: 'var(--lime-ink) !important' }}>How are you feeling right now?</h2>
          <p style={{ fontSize: '0.85rem', opacity: 0.75, marginBottom: '20px' }}>One honest tap a day builds the picture your care team sees.</p>
          <div style={{ background: 'var(--surface)', borderRadius: '22px', padding: '22px', display: 'inline-block', boxShadow: 'var(--shadow-lg)' }}>
            <MoodPicker onSelect={handleMood} />
          </div>
        </div>
      ) : (
        <div className="card" style={{ borderColor: 'rgba(46,139,87,0.3)', background: 'var(--ok-soft)', padding: '22px', textAlign: 'center' }}>
          <div style={{ fontSize: '2rem' }}>✅</div>
          <div style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--ok)', marginTop: '4px' }}>
            Mood logged for today{todayLabel ? ` — feeling ${todayLabel}` : ''}
          </div>
          <div style={{ fontSize: '0.8rem', color: 'var(--muted)', marginTop: '4px' }}>Check back tomorrow for the next check-in.</div>
        </div>
      )}
      {savedOffline && (
        <div className="card-sm" style={{ borderColor: 'color-mix(in srgb, var(--warn) 30%, transparent)', background: 'var(--warn-soft)', padding: '10px 14px' }}>
          <span style={{ fontSize: '0.78rem', color: 'var(--warn)', fontWeight: 600 }}>📡 You're offline — mood saved on this device. It will sync automatically when you're back online.</span>
        </div>
      )}

      <div>
        <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: '12px' }}>
          <h2 style={{ margin: 0 }}>Recent moods</h2>
          <span style={{ fontSize: '0.75rem', color: 'var(--faint)' }}>{monthName}</span>
        </div>
        <div className="space-y-2">
          {logs.slice(-14).reverse().map((l: any) => (
            <div key={l.id} className="card-stage" style={{ justifyContent: 'space-between' }}>
              <div className="flex items-center gap-3">
                <span style={{ fontSize: '1.3rem' }}>{l.emoji}</span>
                <span style={{ fontSize: '0.875rem', color: 'var(--heading)', textTransform: 'capitalize', fontWeight: 600 }}>{l.label}</span>
              </div>
              <span style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>{l.date}</span>
            </div>
          ))}
          {logs.length === 0 && (
            <div className="card" style={{ textAlign: 'center', color: 'var(--muted)' }}>
              No moods logged yet — today is day one. 🌱
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
