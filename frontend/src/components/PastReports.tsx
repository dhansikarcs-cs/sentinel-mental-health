import { useEffect, useMemo, useRef, useState } from 'react'
import { api } from '../api/client'
import { formatDate } from '../constants'

/**
 * Past reports: the clinician's library of structured one-page session
 * reports for the selected client. Read, edit every field, create, delete,
 * attach a file, and export as a formatted text page.
 */

const FIELDS: { key: string; label: string; rows?: number }[] = [
  { key: 'presenting_concerns', label: 'Presenting concerns', rows: 3 },
  { key: 'mental_state', label: 'Mental state (MSE)', rows: 3 },
  { key: 'interventions', label: 'Interventions this session', rows: 4 },
  { key: 'risk_assessment', label: 'Risk assessment', rows: 3 },
  { key: 'progress_note', label: 'Progress since last', rows: 3 },
  { key: 'homework', label: 'Homework set', rows: 2 },
  { key: 'plan', label: 'Plan / next steps', rows: 3 },
]

const EMPTY = {
  session_date: new Date().toISOString().slice(0, 10),
  session_type: 'Review',
  duration_min: 50,
  title: '',
  presenting_concerns: '',
  mental_state: '',
  interventions: '',
  risk_assessment: '',
  progress_note: '',
  homework: '',
  plan: '',
}

export default function PastReports({ patient }: { patient: string }) {
  const [reports, setReports] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [q, setQ] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [openId, setOpenId] = useState<number | null>(null)
  const [editingId, setEditingId] = useState<number | null>(null) // null = not editing, 'new' = creating
  const [draft, setDraft] = useState<any>(null)
  const [busy, setBusy] = useState(false)
  const fileInput = useRef<HTMLInputElement>(null)
  const uploadTarget = useRef<number | null>(null)

  async function load() {
    setLoading(true)
    setError('')
    try {
      setReports(await api.getReports(patient))
    } catch (e: any) {
      setError(e.message || 'Failed to load reports')
    }
    setLoading(false)
  }

  useEffect(() => {
    setOpenId(null); setEditingId(null); setDraft(null); setQ(''); setTypeFilter('')
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [patient])

  const filtered = useMemo(() => {
    let list = reports
    if (typeFilter) list = list.filter(r => r.session_type === typeFilter)
    if (q.trim()) {
      const needle = q.toLowerCase()
      list = list.filter(r =>
        [r.title, r.session_type, r.clinician_summary, r.presenting_concerns, r.progress_note, r.session_date]
          .some((v: string) => (v || '').toLowerCase().includes(needle)),
      )
    }
    return list
  }, [reports, q, typeFilter])

  const types = useMemo(() => Array.from(new Set(reports.map(r => r.session_type))).sort(), [reports])

  function startCreate() {
    setDraft({ ...EMPTY })
    setEditingId(-1) // -1 = new
    setOpenId(null)
  }

  function startEdit(r: any) {
    setDraft({
      session_date: r.session_date, session_type: r.session_type,
      duration_min: r.duration_min, title: r.title,
      presenting_concerns: r.presenting_concerns || '', mental_state: r.mental_state || '',
      interventions: r.interventions || '', risk_assessment: r.risk_assessment || '',
      progress_note: r.progress_note || '', homework: r.homework || '', plan: r.plan || '',
    })
    setEditingId(r.id)
    setOpenId(null)
  }

  async function saveDraft() {
    if (!draft) return
    setBusy(true)
    try {
      if (editingId === -1) {
        const created = await api.createReport({ patient, ...draft })
        setOpenId(created.id)
      } else if (editingId !== null) {
        await api.updateReport(editingId, draft)
      }
      setEditingId(null); setDraft(null)
      await load()
    } catch (e: any) {
      alert(e.message || 'Save failed')
    }
    setBusy(false)
  }

  async function remove(r: any) {
    if (!window.confirm(`Delete the ${r.session_date} report "${r.title || 'Untitled'}"? This cannot be undone.`)) return
    setBusy(true)
    try {
      await api.deleteReport(r.id)
      if (openId === r.id) setOpenId(null)
      await load()
    } catch (e: any) {
      alert(e.message || 'Delete failed')
    }
    setBusy(false)
  }

  async function approve(r: any) {
    setBusy(true)
    try {
      await api.approveReport(r.id)
      await load()
    } catch (e: any) {
      alert(e.message || 'Approve failed')
    }
    setBusy(false)
  }

  async function doUpload(id: number) {
    uploadTarget.current = id
    fileInput.current?.click()
  }

  async function onFilePicked(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    e.target.value = ''
    const id = uploadTarget.current
    if (!file || !id) return
    setBusy(true)
    try {
      await api.uploadReportFile(id, file)
      await load()
    } catch (err: any) {
      alert(err.message || 'Upload failed')
    }
    setBusy(false)
  }

  async function exportReport(r: any) {
    try {
      await api.downloadReportExport(r.id, `session_report_${r.patient}_${r.session_date}.txt`)
    } catch (e: any) {
      alert(e.message || 'Export failed')
    }
  }

  async function downloadAttachment(r: any) {
    try {
      await api.downloadReportAttachment(r.id, r.file_name || 'attachment')
    } catch (e: any) {
      alert(e.message || 'Download failed')
    }
  }

  return (
    <div className="card" style={{ marginTop: '16px' }} data-tour="reports">
      <input ref={fileInput} type="file" style={{ display: 'none' }} onChange={onFilePicked}
        accept=".pdf,.doc,.docx,.txt,.md,.png,.jpg,.jpeg,.csv,.xlsx" />
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap', marginBottom: '10px' }}>
        <div style={{ color: 'var(--accent)', fontWeight: 800, fontSize: '0.68rem', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
          📄 Past reports
        </div>
        <span style={{ color: 'var(--muted)', fontSize: '0.62rem' }}>{reports.length} on file</span>
        <div style={{ flex: 1 }} />
        <input
          value={q} onChange={e => setQ(e.target.value)} placeholder="Search reports…"
          style={{ padding: '6px 12px', fontSize: '0.72rem', borderRadius: 999, border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--on-ink)', width: '160px' }}
        />
        {types.length > 0 && (
          <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)}
            style={{ padding: '6px 10px', fontSize: '0.68rem', borderRadius: 999, border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--on-ink)' }}>
            <option value="">All types</option>
            {types.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        )}
        <button className="btn-primary" style={{ fontSize: '0.68rem', padding: '6px 14px' }} onClick={startCreate} disabled={busy}>
          ＋ New report
        </button>
      </div>

      {loading && <div style={{ color: 'var(--muted)', fontSize: '0.75rem', padding: '10px 0' }}>Loading reports…</div>}
      {!loading && error && <div style={{ color: 'var(--danger)', fontSize: '0.75rem', padding: '10px 0' }}>⚠️ {error}</div>}

      {!loading && !error && filtered.length === 0 && (
        <div style={{ color: 'var(--muted)', fontSize: '0.75rem', padding: '14px 0', textAlign: 'center' }}>
          {reports.length === 0 ? '📝 No reports yet — file the first one after today\'s session.' : 'No reports match that search.'}
        </div>
      )}

      {/* Editor (create or edit) */}
      {editingId !== null && draft && (
        <div style={{ border: '2px solid var(--accent)', borderRadius: '16px', padding: '14px', marginBottom: '12px', background: 'var(--surface)' }}>
          <div style={{ fontWeight: 800, fontSize: '0.8rem', marginBottom: '10px', color: 'var(--heading)' }}>
            {editingId === -1 ? '🆕 New session report' : '✏️ Editing report'}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '8px', marginBottom: '10px' }}>
            <label style={lbl}>
              Date
              <input type="date" value={draft.session_date} onChange={e => setDraft({ ...draft, session_date: e.target.value })} style={inp} />
            </label>
            <label style={lbl}>
              Type
              <select value={draft.session_type} onChange={e => setDraft({ ...draft, session_type: e.target.value })} style={inp}>
                {['Intake', 'Review', 'Skills session', 'Telehealth', 'Crisis follow-up', 'Planning'].map(t => <option key={t}>{t}</option>)}
              </select>
            </label>
            <label style={lbl}>
              Duration (min)
              <input type="number" min={10} max={180} value={draft.duration_min} onChange={e => setDraft({ ...draft, duration_min: Number(e.target.value) || 50 })} style={inp} />
            </label>
            <label style={{ ...lbl, gridColumn: '1 / -1' }}>
              Title
              <input value={draft.title} onChange={e => setDraft({ ...draft, title: e.target.value })} placeholder="e.g. Week 6 review — exposure ladder rung 3" style={inp} />
            </label>
          </div>
          {FIELDS.map(f => (
            <label key={f.key} style={{ ...lbl, marginBottom: '8px' }}>
              {f.label}
              <textarea rows={f.rows || 2} value={draft[f.key]} onChange={e => setDraft({ ...draft, [f.key]: e.target.value })} style={{ ...inp, resize: 'vertical', lineHeight: 1.55 }} />
            </label>
          ))}
          <div style={{ display: 'flex', gap: '8px', marginTop: '6px' }}>
            <button className="btn-primary" onClick={saveDraft} disabled={busy || !draft.session_date}>
              {busy ? 'Saving…' : '💾 Save report'}
            </button>
            <button onClick={() => { setEditingId(null); setDraft(null) }} disabled={busy}>✕ Cancel</button>
          </div>
        </div>
      )}

      {/* List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {filtered.map(r => {
          const open = openId === r.id
          return (
            <div key={r.id} style={{ border: '1px solid var(--border)', borderRadius: '14px', overflow: 'hidden' }}>
              <button
                onClick={() => setOpenId(open ? null : r.id)}
                style={{ width: '100%', display: 'flex', alignItems: 'center', gap: '10px', padding: '10px 14px', background: 'var(--surface)', border: 'none', cursor: 'pointer', textAlign: 'left', flexWrap: 'wrap' }}
              >
                <span style={{ fontSize: '0.78rem', fontWeight: 800, color: 'var(--heading)', minWidth: '92px' }}>{r.session_date}</span>
                <span style={{ fontSize: '0.6rem', fontWeight: 800, padding: '3px 9px', borderRadius: 999, background: 'var(--accent-soft, rgba(0,0,0,0.06))', color: 'var(--accent)' }}>{r.session_type}</span>
                <span style={{ flex: 1, minWidth: '140px', fontSize: '0.72rem', color: 'var(--on-ink)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {r.title || r.clinician_summary || 'Untitled session'}
                </span>
                {r.has_file && <span title={`Attachment: ${r.file_name}`}>📎</span>}
                {r.approved_by && <span title={`Approved by ${r.approved_by}`} style={{ fontSize: '0.62rem', color: 'var(--ok)', fontWeight: 800 }}>✓ approved</span>}
                <span style={{ color: 'var(--muted)', fontSize: '0.62rem' }}>{r.duration_min} min {open ? '▾' : '▸'}</span>
              </button>

              {open && (
                <div style={{ padding: '14px 16px', borderTop: '1px solid var(--border)' }}>
                  {/* One-page report layout */}
                  <div className="report-page" style={{ background: 'var(--surface)', borderRadius: '12px', padding: '16px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', flexWrap: 'wrap', gap: '6px', borderBottom: '2px solid var(--border)', paddingBottom: '8px', marginBottom: '10px' }}>
                      <div>
                        <div style={{ fontWeight: 900, fontSize: '0.92rem', color: 'var(--heading)' }}>{r.title || 'Session report'}</div>
                        <div style={{ fontSize: '0.62rem', color: 'var(--muted)' }}>
                          {r.session_date} · {r.session_type} · {r.duration_min} min · clinician @{r.psychologist}
                        </div>
                      </div>
                      {r.approved_by && <div style={{ fontSize: '0.6rem', color: 'var(--ok)', fontWeight: 800 }}>✓ Approved by {r.approved_by}</div>}
                    </div>
                    {FIELDS.map(f => (
                      (r[f.key] || '').trim() && (
                        <div key={f.key} style={{ marginBottom: '9px' }}>
                          <div style={{ fontSize: '0.58rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.07em', color: 'var(--accent)', marginBottom: '2px' }}>{f.label}</div>
                          <div style={{ fontSize: '0.76rem', lineHeight: 1.65, color: 'var(--on-ink)', whiteSpace: 'pre-wrap' }}>{r[f.key]}</div>
                        </div>
                      )
                    ))}
                    {r.has_file && (
                      <div style={{ fontSize: '0.66rem', color: 'var(--muted)', marginTop: '6px' }}>📎 Attachment on file: {r.file_name}</div>
                    )}
                  </div>

                  {/* Actions */}
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginTop: '12px' }}>
                    <button onClick={() => startEdit(r)} disabled={busy} style={act}>✏️ Edit</button>
                    <button onClick={() => exportReport(r)} style={act}>⬇️ Export</button>
                    <button onClick={() => doUpload(r.id)} disabled={busy} style={act}>📤 Upload</button>
                    {r.has_file && <button onClick={() => downloadAttachment(r)} style={act}>📎 Get file</button>}
                    {!r.approved_by && <button onClick={() => approve(r)} disabled={busy} style={{ ...act, color: 'var(--ok)' }}>✓ Approve</button>}
                    <div style={{ flex: 1 }} />
                    <button onClick={() => remove(r)} disabled={busy} style={{ ...act, color: 'var(--danger)' }}>🗑 Delete</button>
                  </div>
                  <div style={{ fontSize: '0.58rem', color: 'var(--faint)', marginTop: '8px' }}>
                    Last updated {r.updated_at ? formatDate(r.updated_at) : '—'} · exports as a formatted one-page text report
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

const lbl: React.CSSProperties = { display: 'flex', flexDirection: 'column', gap: '3px', fontSize: '0.6rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--muted)' }
const inp: React.CSSProperties = { padding: '8px 10px', fontSize: '0.76rem', borderRadius: '10px', border: '1px solid var(--border)', background: 'var(--bg, transparent)', color: 'var(--on-ink)', fontWeight: 400, textTransform: 'none', letterSpacing: 0 }
const act: React.CSSProperties = { background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 999, padding: '5px 13px', fontSize: '0.66rem', fontWeight: 700, cursor: 'pointer', color: 'var(--on-ink)' }
