import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import PatientSelector from '../components/PatientSelector'

interface J2NDraft {
  status: 'draft' | 'empty' | 'error'
  patient: string
  note?: string
  themes?: string[]
  journalDate?: string
  journalPreview?: string
}

export default function ClinicalNotesPage() {
  const [patients, setPatients] = useState<any[]>([])
  const [notes, setNotes] = useState<any[]>([])
  const [selectedPatient, setSelectedPatient] = useState('')
  const [rawNotes, setRawNotes] = useState('')
  const [saving, setSaving] = useState(false)
  const [aiDraft, setAiDraft] = useState<any>(null)
  const [j2n, setJ2n] = useState<J2NDraft | null>(null)
  const [j2nLoading, setJ2nLoading] = useState<string | null>(null)
  const [acceptedMsg, setAcceptedMsg] = useState('')
  const [query, setQuery] = useState('')
  const [fPatient, setFPatient] = useState('')
  const [fDateFrom, setFDateFrom] = useState('')
  const [fDateTo, setFDateTo] = useState('')
  const [fApproved, setFApproved] = useState('')
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editText, setEditText] = useState('')
  const [savingEdit, setSavingEdit] = useState(false)
  const editorRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    api.getPsychPatients().then(setPatients).catch(() => {})
    api.getPsychNotes().then(setNotes).catch(() => {})
  }, [])

  function showAccepted(msg: string) {
    setAcceptedMsg(msg)
    window.setTimeout(() => setAcceptedMsg(''), 6000)
  }

  async function saveNote() {
    if (!selectedPatient || !rawNotes.trim()) return
    setSaving(true)
    try {
      await api.createPsychNote({ patient_username: selectedPatient, raw_notes: rawNotes })
      setRawNotes('')
      setAiDraft(null)
      showAccepted('Note saved.')
      const updated = await api.getPsychNotes()
      setNotes(updated || [])
    } catch (err: any) { alert(err.message) }
    setSaving(false)
  }

  function acceptIntoEditor(text: string) {
    setRawNotes(text)
    setAiDraft(null)
    setJ2n(null)
    showAccepted('Draft accepted into the editor — review, then Save Note.')
    editorRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    editorRef.current?.focus()
  }

  async function generateAiDraft() {
    if (!selectedPatient || !rawNotes.trim()) return
    try {
      const note = await api.synthesizeNote(rawNotes)
      setAiDraft(note)
    } catch {
      try {
        const fallback = await api.journalToNote(selectedPatient, rawNotes)
        setAiDraft(fallback)
      } catch {}
    }
  }

  async function journalToNote(p: any) {
    setSelectedPatient(p.username)
    setJ2nLoading(p.username)
    setJ2n(null)
    try {
      const journals = await api.getPatientJournals(p.username)
      if (!journals || journals.length === 0) {
        setJ2n({ status: 'empty', patient: p.username })
        return
      }
      const latest = journals[0]
      const j2n = await api.journalToNote(p.username, latest.raw_content || '', latest.summary || '')
      setJ2n({
        status: 'draft',
        patient: p.username,
        note: j2n.note || j2n.suggestion || '',
        themes: j2n.themes || [],
        journalDate: (latest.timestamp || latest.created_at || '').slice(0, 10),
        journalPreview: (latest.summary || 'Summary pending — the AI note will use this journal entry.').slice(0, 90),
      })
    } catch {
      setJ2n({ status: 'error', patient: p.username })
    } finally {
      setJ2nLoading(null)
    }
  }

  async function loadNotes() {
    try {
      const updated = await api.getPsychNotes({
        patient: fPatient || undefined,
        q: query || undefined,
        date_from: fDateFrom || undefined,
        date_to: fDateTo || undefined,
        approved: fApproved || undefined,
      })
      setNotes(updated || [])
    } catch {}
  }

  useEffect(() => {
    const t = window.setTimeout(loadNotes, 250) // debounce free-text
    return () => window.clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fPatient, query, fDateFrom, fDateTo, fApproved])

  async function saveEdit(id: number) {
    if (!editText.trim()) return
    setSavingEdit(true)
    try {
      await api.updatePsychNote(id, { raw_notes: editText })
      setEditingId(null)
      showAccepted('Note updated.')
      await loadNotes()
    } catch (err: any) { alert(err.message) }
    setSavingEdit(false)
  }

  const shownNotes = notes

  return (
    <div className="space-y-4 animate-fade-in">
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '16px', alignItems: 'start' }} className="notes-grid">
        <div className="space-y-4">
          <div className="card" style={{ padding: '24px' }} data-tour="clinical-notes">
            <h2 style={{ fontSize: '1rem', margin: '0 0 14px 0' }}>✍️ New session note</h2>
            <PatientSelector
              patients={patients}
              value={selectedPatient}
              onChange={setSelectedPatient}
              placeholder="Select client…"
              style={{ width: '100%', marginBottom: '12px' }}
            />
            <textarea
              ref={editorRef}
              value={rawNotes}
              onChange={e => setRawNotes(e.target.value)}
              placeholder="Enter your session observations… (OAP format works great: Observations → Assessment → Plan)"
              rows={9}
              style={{ width: '100%', padding: '14px', fontSize: '0.875rem', resize: 'none', marginBottom: '12px', lineHeight: 1.65, borderRadius: '16px' }}
            />
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              <button onClick={saveNote} disabled={saving || !selectedPatient || !rawNotes.trim()} className="btn-primary">
                {saving ? 'Saving…' : '💾 Save note'}
              </button>
              <button onClick={generateAiDraft} disabled={!selectedPatient || !rawNotes.trim()}>
                🤖 AI draft
              </button>
              {rawNotes && <button className="btn-ghost" onClick={() => setRawNotes('')}>Clear</button>}
            </div>

            {acceptedMsg && (
              <div style={{
                marginTop: '12px', padding: '9px 13px', borderRadius: '12px', fontSize: '0.78rem', fontWeight: 600,
                background: 'var(--ok-soft)', border: '1px solid color-mix(in srgb, var(--ok) 27%, transparent)', color: 'var(--ok)',
              }}>
                ✅ {acceptedMsg}
              </div>
            )}

            {aiDraft && (
              <div className="ai-box" style={{ marginTop: '12px' }}>
                <div className="ai-header">🤖 AI clinical draft</div>
                <div className="ai-body" style={{ whiteSpace: 'pre-wrap' }}>{aiDraft.note || aiDraft.suggestion}</div>
                {aiDraft.themes && (
                  <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap', marginTop: '8px' }}>
                    {aiDraft.themes.map((t: string) => (
                      <span key={t} className="badge-theme">{t}</span>
                    ))}
                  </div>
                )}
                <div style={{ display: 'flex', gap: '8px', marginTop: '10px' }}>
                  <button onClick={() => acceptIntoEditor(aiDraft.note || aiDraft.suggestion)} className="btn-primary" style={{ padding: '6px 14px', fontSize: '0.75rem' }}>
                    ✓ Accept to editor
                  </button>
                  <button onClick={() => setAiDraft(null)} style={{ padding: '6px 14px', fontSize: '0.75rem' }}>
                    ✕ Cancel
                  </button>
                </div>
              </div>
            )}
          </div>

          <div className="card" style={{ padding: '22px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px', gap: '10px', flexWrap: 'wrap' }}>
              <h2 style={{ fontSize: '1rem', margin: 0 }}>📋 Saved notes ({shownNotes.length})</h2>
              <input placeholder="🔍 Search contents…" value={query} onChange={e => setQuery(e.target.value)} style={{ width: '180px', borderRadius: 999 }} />
            </div>

            {/* Filter bar */}
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '12px', flexWrap: 'wrap' }}>
              <select value={fPatient} onChange={e => setFPatient(e.target.value)} style={{ fontSize: '0.78rem', maxWidth: '170px' }}>
                <option value="">All clients</option>
                {(patients || []).map((p: any) => <option key={p.username} value={p.username}>{p.name}</option>)}
              </select>
              <input type="date" value={fDateFrom} onChange={e => setFDateFrom(e.target.value)} style={{ width: '140px', fontSize: '0.75rem' }} title="From date" />
              <span style={{ color: 'var(--muted)', fontSize: '0.72rem' }}>→</span>
              <input type="date" value={fDateTo} onChange={e => setFDateTo(e.target.value)} style={{ width: '140px', fontSize: '0.75rem' }} title="To date" />
              {(['', 'yes', 'no'] as const).map(v => (
                <button key={v || 'all'} className={`chip${fApproved === v ? ' active' : ''}`} onClick={() => setFApproved(v)}>
                  {v === '' ? 'All' : v === 'yes' ? '✅ Approved' : 'Unsigned'}
                </button>
              ))}
              {(fPatient || query || fDateFrom || fDateTo || fApproved) && (
                <button className="btn-ghost" style={{ fontSize: '0.72rem' }} onClick={() => { setFPatient(''); setQuery(''); setFDateFrom(''); setFDateTo(''); setFApproved('') }}>
                  Clear filters
                </button>
              )}
            </div>

            {shownNotes.length === 0 ? (
              <p style={{ color: 'var(--muted)', fontSize: '0.85rem' }}>
                {query || fPatient || fDateFrom || fDateTo || fApproved ? 'No notes match these filters.' : 'No notes yet — save your first session note above.'}
              </p>
            ) : (
              <div className="space-y-2">
                {shownNotes.slice(0, 20).map((n: any) => (
                  <div key={n.id} className="card-stage" style={{ flexDirection: 'column', alignItems: 'stretch' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px', gap: '8px', alignItems: 'center' }}>
                      <span style={{ fontSize: '0.82rem', color: 'var(--accent)', fontWeight: 800 }}>{n.patient}</span>
                      <span style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                        {n.approved_by && <span style={{ fontSize: '0.6rem', color: 'var(--ok)', fontWeight: 700 }}>✅ signed</span>}
                        <span style={{ fontSize: '0.65rem', color: 'var(--muted)' }}>{n.timestamp?.slice(0, 10)}</span>
                        <button
                          style={{ fontSize: '0.66rem', padding: '2px 9px' }}
                          title="Edit this note"
                          onClick={() => { setEditingId(editingId === n.id ? null : n.id); setEditText(n.raw_notes || n.ai_synthesis || '') }}
                        >
                          ✏️ Edit
                        </button>
                      </span>
                    </div>
                    {editingId === n.id ? (
                      <div>
                        <textarea
                          value={editText}
                          onChange={e => setEditText(e.target.value)}
                          rows={6}
                          style={{ width: '100%', padding: '11px', fontSize: '0.8rem', lineHeight: 1.6, borderRadius: '14px', marginBottom: '8px' }}
                        />
                        <div style={{ display: 'flex', gap: '8px' }}>
                          <button className="btn-primary" style={{ fontSize: '0.75rem', padding: '5px 13px' }} disabled={savingEdit || !editText.trim()} onClick={() => saveEdit(n.id)}>
                            {savingEdit ? 'Saving…' : '💾 Save changes'}
                          </button>
                          <button style={{ fontSize: '0.75rem', padding: '5px 13px' }} onClick={() => setEditingId(null)}>Cancel</button>
                        </div>
                      </div>
                    ) : (
                      <div style={{ fontSize: '0.76rem', color: 'var(--secondary)', lineHeight: 1.55, whiteSpace: 'pre-wrap' }}>
                        {(n.raw_notes || n.ai_synthesis || '')?.slice(0, 240)}{(n.raw_notes || n.ai_synthesis || '')?.length > 240 ? '…' : ''}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="card" style={{ padding: '20px', position: 'sticky', top: '90px' }}>
          <h2 style={{ fontSize: '0.95rem', margin: '0 0 8px 0' }}>🤖 Journal → Note</h2>
          <p style={{ fontSize: '0.74rem', color: 'var(--muted)', marginBottom: '14px', lineHeight: 1.6 }}>
            Pick a client — we&apos;ll draft a clinical note from their latest journal entry. Accept it into the editor or cancel.
          </p>

          {!j2n && (
            <div className="space-y-2">
              {patients.length === 0 && <p style={{ color: 'var(--muted)', fontSize: '0.82rem' }}>No clients available.</p>}
              {patients.slice(0, 6).map((p: any) => (
                <button
                  key={p.username}
                  onClick={() => journalToNote(p)}
                  disabled={j2nLoading !== null}
                  style={{
                    width: '100%', textAlign: 'left', padding: '10px 13px', borderRadius: '14px',
                    background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text)', fontSize: '0.82rem',
                    cursor: j2nLoading === p.username ? 'progress' : 'pointer', transition: 'all 0.2s', justifyContent: 'space-between',
                  }}
                >
                  <span style={{ fontWeight: 600 }}>{j2nLoading === p.username ? '⏳ Drafting…' : `👤 ${p.name}`}</span>
                  <span style={{ color: 'var(--faint)', fontSize: '0.65rem' }}>draft →</span>
                </button>
              ))}
            </div>
          )}

          {j2n && j2n.status === 'empty' && (
            <div>
              <div style={{ color: 'var(--secondary)', fontSize: '0.82rem', marginBottom: '12px' }}>
                No journal entries for <strong style={{ color: 'var(--accent)' }}>{j2n.patient}</strong> yet.
              </div>
              <button onClick={() => setJ2n(null)} style={{ padding: '6px 14px', fontSize: '0.75rem' }}>← Back to clients</button>
            </div>
          )}

          {j2n && j2n.status === 'error' && (
            <div>
              <div style={{ color: 'var(--danger)', fontSize: '0.82rem', marginBottom: '12px' }}>
                Could not draft a note for {j2n.patient}. Please try again.
              </div>
              <button onClick={() => setJ2n(null)} style={{ padding: '6px 14px', fontSize: '0.75rem' }}>← Back to clients</button>
            </div>
          )}

          {j2n && j2n.status === 'draft' && (
            <div>
              <div style={{ fontSize: '0.66rem', color: 'var(--muted)', marginBottom: '8px', fontWeight: 600 }}>
                From {j2n.patient}&apos;s journal{j2n.journalDate ? ` · ${j2n.journalDate}` : ''}
              </div>
              <div style={{
                padding: '13px', borderRadius: '14px', fontSize: '0.8rem', lineHeight: 1.65, whiteSpace: 'pre-wrap',
                background: 'var(--surface-soft)', border: '1px solid var(--border)', color: 'var(--text)', maxHeight: '260px', overflow: 'auto',
              }}>
                {j2n.note || '(empty draft)'}
              </div>
              {j2n.themes && j2n.themes.length > 0 && (
                <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap', marginTop: '8px' }}>
                  {j2n.themes.map((t: string) => (
                    <span key={t} className="badge-theme">{t}</span>
                  ))}
                </div>
              )}
              <div style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
                <button onClick={() => acceptIntoEditor(j2n.note || '')} className="btn-primary" style={{ padding: '8px 14px', fontSize: '0.75rem' }}>
                  ✓ Accept to editor
                </button>
                <button onClick={() => setJ2n(null)} style={{ padding: '8px 14px', fontSize: '0.75rem' }}>
                  ✕ Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
      <style>{`@media (max-width: 1100px) { .notes-grid { grid-template-columns: 1fr !important; } .notes-grid > div[style*="sticky"] { position: static !important; } }`}</style>
    </div>
  )
}
