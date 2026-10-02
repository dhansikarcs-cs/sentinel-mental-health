import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { sourceColor } from '../constants'

export default function PsychJournalPage() {
  const [wellness, setWellness] = useState<any>(null)

  useEffect(() => {
    api.getWellness().then(setWellness).catch(() => {})
  }, [])

  return (
    <div className="space-y-4 animate-fade-in">
      <div className="card-lime" style={{ padding: '24px 26px', display: 'flex', alignItems: 'center', gap: '18px', flexWrap: 'wrap' }}>
        {wellness?.mood && (
          <>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '2.2rem' }}>{wellness.mood.emoji}</div>
              <div style={{ fontSize: '0.68rem', fontWeight: 700, textTransform: 'capitalize', opacity: 0.8 }}>{wellness.mood.label}</div>
            </div>
            <div style={{ width: '1px', height: '48px', background: 'rgba(0,0,0,0.15)' }} />
          </>
        )}
        <div style={{ flex: 1, minWidth: '180px' }}>
          <h2 style={{ margin: 0, color: 'var(--lime-ink) !important' }}>Your own wellness matters too</h2>
          <div style={{ fontSize: '0.82rem', opacity: 0.78 }}>
            Reflect on your day, your sessions, and your capacity. {wellness?.journals_today ? `${wellness.journals_today} entr${wellness.journals_today === 1 ? 'y' : 'ies'} logged today ✓` : 'No entries today yet.'}
          </div>
        </div>
      </div>

      <MyJournal />
    </div>
  )
}

function MyJournal() {
  const [subTab, setSubTab] = useState<'write' | 'history'>('write')
  const [text, setText] = useState('')
  const [saving, setSaving] = useState(false)
  const [entries, setEntries] = useState<any[]>([])
  const [expanded, setExpanded] = useState<Set<number>>(new Set())

  useEffect(() => {
    api.getPsychJournals().then(setEntries).catch(() => {})
  }, [])

  async function handleSave() {
    if (!text.trim()) return
    setSaving(true)
    try {
      await api.createPsychJournal(text.trim())
      setText('')
      const updated = await api.getPsychJournals()
      setEntries(updated)
    } catch {}
    setSaving(false)
  }

  const wordCount = text.trim() ? text.trim().split(/\s+/).length : 0

  return (
    <div>
      <div className="segmented-control">
        <button className={`segmented-btn${subTab === 'write' ? ' active' : ''}`} onClick={() => setSubTab('write')}>✍️ Write</button>
        <button className={`segmented-btn${subTab === 'history' ? ' active' : ''}`} onClick={() => setSubTab('history')}>📖 History ({entries.length})</button>
      </div>

      {subTab === 'write' ? (
        <div className="card" style={{ padding: '24px' }}>
          <textarea value={text} onChange={e => setText(e.target.value)}
            placeholder="Write freely about your day, thoughts, or sessions…"
            style={{ width: '100%', minHeight: '220px', padding: '15px', fontSize: '0.9rem', resize: 'vertical', lineHeight: 1.65, borderRadius: '16px' }} />
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '10px' }}>
            <span style={{ color: 'var(--faint)', fontSize: '0.72rem', fontWeight: 600 }}>{wordCount} words</span>
            <button onClick={handleSave} disabled={saving || !text.trim()} className="btn-primary" style={{ padding: '9px 22px' }}>
              {saving ? 'Saving…' : '💾 Save entry'}
            </button>
          </div>
        </div>
      ) : (
        <div>
          {entries.length === 0 ? (
            <div className="card" style={{ textAlign: 'center', padding: '28px', color: 'var(--muted)' }}>
              No entries yet — your reflective practice starts here. 🌱
            </div>
          ) : (
            entries.map((e: any) => {
              const id = e.id
              const open = expanded.has(id)
              const ts = e.timestamp ? new Date(e.timestamp).toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : ''
              return (
                <div key={id} style={{ marginBottom: '8px' }}>
                  <button onClick={() => setExpanded(prev => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n })}
                    style={{
                      width: '100%', padding: '10px 14px', background: open ? 'var(--accent-soft)' : 'var(--surface)',
                      border: `1px solid ${open ? 'var(--accent)' : 'var(--border)'}`, borderRadius: '14px',
                      color: 'var(--text)', fontSize: '0.82rem', fontWeight: 600, cursor: 'pointer', textAlign: 'left',
                      display: 'flex', alignItems: 'center', gap: '8px',
                    }}>
                    <span>📄 {ts}</span>
                    <span style={{ marginLeft: 'auto', color: 'var(--muted)', fontSize: '0.7rem' }}>{open ? 'Collapse' : 'Expand'}</span>
                  </button>
                  {open && (
                    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '16px', padding: '16px', margin: '4px 0 0', boxShadow: 'var(--shadow)' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px', flexWrap: 'wrap' }}>
                        {e.ai_source && (
                          <span className="badge-theme" style={{ color: sourceColor(e.ai_source), borderColor: `${sourceColor(e.ai_source)}55` }}>{e.ai_source.toUpperCase()}</span>
                        )}
                        {e.emotions && <span style={{ fontSize: '0.65rem', color: 'var(--secondary)' }}>Emotions: {e.emotions}</span>}
                      </div>
                      <div style={{ color: 'var(--text)', fontSize: '0.84rem', lineHeight: 1.65 }}>{e.summary}</div>
                    </div>
                  )}
                </div>
              )
            })
          )}
        </div>
      )}
    </div>
  )
}
