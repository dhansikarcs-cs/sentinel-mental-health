import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { getUser } from '../stores/auth'
import { todayStr, formatDate } from '../constants'
import PatientSelector from '../components/PatientSelector'
import SlotNumber from '../components/SlotNumber'
import { FloatingEmpty } from '../components/fx'

export default function FollowupsPage() {
  const user = getUser()
  if (user?.role === 'psychologist') return <PsychFollowups />
  return <PatientFollowups />
}

const STATUS_BADGE: Record<string, { label: string; color: string; bg: string }> = {
  pending: { label: '⏳ Open', color: '#8A5A10', bg: 'var(--warn-soft)' },
  completed: { label: '✅ Done', color: 'var(--ok)', bg: 'var(--ok-soft)' },
  skipped: { label: '❌ Skipped', color: 'var(--danger)', bg: 'var(--danger-soft)' },
}

function dueInfo(due?: string): { text: string; color: string } | null {
  if (!due) return null
  const today = todayStr()
  if (due < today) return { text: `Overdue · ${formatDate(due)}`, color: 'var(--danger)' }
  if (due === today) return { text: 'Due today', color: '#8A5A10' }
  return { text: `Due ${formatDate(due)}`, color: 'var(--soft)' }
}

function PatientFollowups() {
  const [tasks, setTasks] = useState<any[]>([])
  const [uploadingProof, setUploadingProof] = useState<Record<string, File | null>>({})
  const [busy, setBusy] = useState<Record<string, boolean>>({})

  useEffect(() => { api.getFollowups().then(d => setTasks(d || [])).catch(() => {}) }, [])

  const myTasks = (tasks || []).filter((t: any) => t.patient_username === getUser()?.username)
  const open = myTasks.filter((t: any) => t.status === 'pending')
  const done = myTasks.filter((t: any) => t.status !== 'pending')

  async function refresh() {
    try { setTasks((await api.getFollowups()) || []) } catch {}
  }

  async function run(id: string, fn: () => Promise<any>) {
    setBusy(b => ({ ...b, [id]: true }))
    try { await fn(); await refresh() } catch {} finally {
      setBusy(b => ({ ...b, [id]: false }))
    }
  }

  return (
    <div className="animate-fade-in">
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', marginBottom: '16px' }}>
        <div className="card-sm" style={{ textAlign: 'center' }}>
          <div className="statnum"><SlotNumber value={myTasks.length} /></div>
          <div style={{ fontSize: '0.68rem', color: 'var(--muted)', fontWeight: 600 }}>Total tasks</div>
        </div>
        <div className="card-sm" style={{ textAlign: 'center' }}>
          <div className="statnum" style={{ color: open.length ? 'var(--warn)' : 'var(--ok)' }}>{open.length}</div>
          <div style={{ fontSize: '0.68rem', color: 'var(--muted)', fontWeight: 600 }}>Still open</div>
        </div>
        <div className="card-sm" style={{ textAlign: 'center' }}>
          <div className="statnum" style={{ color: 'var(--ok)' }}>{done.length}</div>
          <div style={{ fontSize: '0.68rem', color: 'var(--muted)', fontWeight: 600 }}>Completed</div>
        </div>
      </div>

      {myTasks.length === 0 ? (
        <FloatingEmpty emoji="🌿" title="No care tasks assigned yet" sub="Your psychologist will add personalized exercises here." />
      ) : (
        <>
          {open.length > 0 && <h3 style={{ marginBottom: '8px' }}>⚡ To do</h3>}
          <div className="space-y-3">
            {open.map((t: any) => (
              <PatientTaskCard key={t.id} t={t} uploadingProof={uploadingProof} setUploadingProof={setUploadingProof} busy={busy} run={run} />
            ))}
          </div>
          {done.length > 0 && <h3 style={{ margin: '18px 0 8px' }}>✅ Completed</h3>}
          <div className="space-y-3">
            {done.map((t: any) => (
              <PatientTaskCard key={t.id} t={t} uploadingProof={uploadingProof} setUploadingProof={setUploadingProof} busy={busy} run={run} />
            ))}
          </div>
        </>
      )}
    </div>
  )
}

function PatientTaskCard({ t, uploadingProof, setUploadingProof, busy, run }: any) {
  const badge = STATUS_BADGE[t.status] || STATUS_BADGE.pending
  const due = dueInfo(t.due_date)
  const proof = uploadingProof[t.id]
  return (
    <div className={`lead-card${t.status === 'pending' ? ' lime' : ''}`} style={{ padding: '16px 18px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px', flexWrap: 'wrap' }}>
        <div style={{ fontWeight: 800, fontSize: '0.95rem', color: t.status === 'pending' ? 'var(--lime-ink)' : 'var(--heading)' }}>{t.title}</div>
        <span style={{ marginLeft: 'auto', fontSize: '0.62rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.05em', color: badge.color, background: badge.bg, padding: '3px 9px', borderRadius: 999 }}>{badge.label}</span>
      </div>
      {t.description && <div style={{ color: t.status === 'pending' ? 'var(--lime-ink)' : 'var(--soft)', fontSize: '0.82rem', opacity: 0.85, marginBottom: '8px' }}>{t.description}</div>}

      {due && <div style={{ fontSize: '0.6875rem', color: t.status === 'pending' ? 'var(--lime-ink)' : due.color, fontWeight: 700, marginBottom: '8px', opacity: t.status === 'pending' ? 0.75 : 1 }}>{due.text}</div>}

      {t.file_path && (
        <div style={{ marginBottom: '8px' }}>
          <a href={`/api/followups/${t.id}/download`} target="_blank" rel="noreferrer" style={{ fontSize: '0.75rem', fontWeight: 700 }}>
            📎 {t.status === 'completed' ? 'View my submission' : 'View attachment'}
          </a>
        </div>
      )}

      {t.status === 'pending' && (
        <div style={{ display: 'flex', gap: '6px', alignItems: 'center', marginTop: '8px', flexWrap: 'wrap' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.7rem', color: 'var(--lime-ink)', flex: 1, minWidth: '150px', opacity: 0.85 }}>
            <span>📎</span>
            <input type="file" onChange={e => setUploadingProof({ ...uploadingProof, [t.id]: e.target.files?.[0] || null })} style={{ fontSize: '0.7rem', color: 'var(--lime-ink)' }} />
          </label>
          <button className="btn-primary" style={{ fontSize: '0.7rem', padding: '6px 12px' }}
            disabled={!proof || busy[t.id]}
            onClick={() => run('proof', t.id, () => api.uploadFollowupProof(t.id, proof!))}>
            {busy[t.id] ? '…' : proof ? '📤 Submit with proof' : 'Submit with proof'}
          </button>
          <button style={{ fontSize: '0.7rem', padding: '6px 12px', background: 'rgba(0,0,0,0.08) !important', borderColor: 'transparent !important', color: 'var(--lime-ink) !important' }}
            disabled={busy[t.id]}
            onClick={() => run('done', t.id, () => api.updateFollowup(t.id, { status: 'completed', grade: 'none' }))}>
            ✅ Mark done
          </button>
          <button style={{ fontSize: '0.7rem', padding: '6px 12px', background: 'rgba(0,0,0,0.08) !important', borderColor: 'transparent !important', color: 'var(--lime-ink) !important' }}
            disabled={busy[t.id]}
            onClick={() => run('skip', t.id, () => api.updateFollowup(t.id, { status: 'skipped', grade: 'none' }))}>
            ❌ Skip
          </button>
        </div>
      )}

      {t.status === 'completed' && (
        <div>
          {t.grade && t.grade !== 'none' ? (
            <div style={{ color: t.grade === 'green' ? 'var(--ok)' : t.grade === 'yellow' ? 'var(--warn)' : 'var(--danger)', fontWeight: 800, fontSize: '0.82rem' }}>
              {t.grade === 'green' ? '🟢 Correctly done' : t.grade === 'yellow' ? '🟡 Partially done' : '🔴 Needs improvement'}
            </div>
          ) : (
            <div style={{ color: 'var(--ok)', fontSize: '0.82rem', fontWeight: 700 }}>✅ Submitted — awaiting review</div>
          )}
          {t.feedback ? (
            <div style={{ marginTop: '8px', padding: '10px 13px', borderRadius: '12px', background: 'var(--accent-soft)', border: '1px solid color-mix(in srgb, var(--accent) 25%, transparent)' }}>
              <div style={{ color: 'var(--accent)', fontSize: '0.65rem', fontWeight: 800, marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.06em' }}>💬 Feedback from your psychologist</div>
              <div style={{ color: 'var(--text)', fontSize: '0.82rem', lineHeight: 1.55 }}>{t.feedback}</div>
            </div>
          ) : t.grade && t.grade !== 'none' ? (
            <div style={{ color: 'var(--muted)', fontSize: '0.6875rem', marginTop: '6px' }}>No written feedback yet.</div>
          ) : null}
        </div>
      )}

      {t.status === 'skipped' && <div style={{ color: 'var(--danger)', fontWeight: 600 }}>❌ Not completed</div>}

      <div style={{ color: 'var(--muted)', fontSize: '0.65rem', marginTop: '8px' }}>Assigned {formatDate(t.assigned_at)}</div>
    </div>
  )
}

function PsychFollowups() {
  const [tasks, setTasks] = useState<any[]>([])
  const [patients, setPatients] = useState<any[]>([])
  const [expanded, setExpanded] = useState<Record<number, boolean>>({})
  const [newPatient, setNewPatient] = useState('')
  const [newTitle, setNewTitle] = useState('')
  const [newDesc, setNewDesc] = useState('')
  const [newDue, setNewDue] = useState('')
  const [newFile, setNewFile] = useState<File | null>(null)
  const [showAssign, setShowAssign] = useState(false)
  const [aiPatient, setAiPatient] = useState('')
  const [agentResult, setAgentResult] = useState<any>(null)
  const [agentBusy, setAgentBusy] = useState(false)
  const [assigningId, setAssigningId] = useState<number | null>(null)
  const [assignedId, setAssignedId] = useState<number | null>(null)
  const [busy, setBusy] = useState<Record<string, boolean>>({})
  const [feedbackBuf, setFeedbackBuf] = useState<Record<string, string>>({})
  const [feedbackSaved, setFeedbackSaved] = useState<Record<string, boolean>>({})
  const [editEval, setEditEval] = useState<Record<string, boolean>>({})
  const [templates, setTemplates] = useState<any[]>([])
  const [showTemplates, setShowTemplates] = useState(false)
  const [savingTpl, setSavingTpl] = useState(false)

  useEffect(() => {
    api.getFollowups().then(d => setTasks(d || [])).catch(() => {})
    api.getPsychPatients().then(d => setPatients(d || [])).catch(() => {})
    api.getFollowupTemplates().then(d => setTemplates(d || [])).catch(() => {})
  }, [])

  const myTasks = (tasks || []).filter((t: any) => t.psychologist_username === getUser()?.username)
  const pendingCount = myTasks.filter(t => t.status === 'pending').length
  const ungraded = myTasks.filter((t: any) => t.status === 'completed' && (!t.grade || t.grade === 'none')).length
  const overdueCount = myTasks.filter((t: any) => t.status === 'pending' && t.due_date && t.due_date < todayStr()).length

  const [taskFilter, setTaskFilter] = useState<'all' | 'pending' | 'completed' | 'overdue'>('all')
  const [patientFilter, setPatientFilter] = useState('')
  const filteredTasks = myTasks
    .filter((t: any) => taskFilter === 'all' || (taskFilter === 'overdue' ? t.status === 'pending' && t.due_date && t.due_date < todayStr() : t.status === taskFilter))
    .filter((t: any) => !patientFilter || t.patient_username === patientFilter)

  async function refresh() {
    try { setTasks((await api.getFollowups()) || []) } catch {}
  }

  async function run(id: string, fn: () => Promise<any>) {
    setBusy(b => ({ ...b, [id]: true }))
    try { await fn(); await refresh() } catch {} finally {
      setBusy(b => ({ ...b, [id]: false }))
    }
  }

  async function assignTask() {
    if (!newPatient || !newTitle.trim()) return
    try {
      const task = await api.createFollowup({ patient_username: newPatient, title: newTitle, description: newDesc, due_date: newDue })
      if (newFile && task?.id) {
        await api.uploadFollowupAttachment(task.id, newFile)
      }
      setNewTitle(''); setNewDesc(''); setNewDue(''); setNewFile(null)
      await refresh()
      setShowAssign(false)
    } catch {}
  }

  async function useTemplate(tpl: any) {
    if (!newPatient) return
    setSavingTpl(true)
    try {
      await api.assignFromTemplate(tpl.id, newPatient, newDue)
      await refresh()
      await api.getFollowupTemplates().then(d => setTemplates(d || [])).catch(() => {})
      setShowTemplates(false)
    } catch {} finally { setSavingTpl(false) }
  }

  async function saveAsTemplate() {
    if (!newTitle.trim()) return
    try {
      await api.createFollowupTemplate({ title: newTitle, description: newDesc, default_due_days: 7 })
      await api.getFollowupTemplates().then(d => setTemplates(d || [])).catch(() => {})
    } catch {}
  }

  async function analyze() {
    if (!aiPatient) return
    setAgentBusy(true); setAssignedId(null)
    try {
      const result = await api.draftFollowup(aiPatient)
      setAgentResult(result)
    } catch {} finally { setAgentBusy(false) }
  }

  async function assignDraft(i: number, task: any) {
    setAssigningId(i)
    try {
      await api.createFollowup({ patient_username: aiPatient, title: task.title, description: task.description, due_date: newDue || '' })
      setAssignedId(i)
      await refresh()
    } catch {} finally { setAssigningId(null) }
  }

  async function gradeTask(id: string, grade: string) {
    const current = (tasks || []).find((t: any) => t.id === id)
    if (current?.grade && current.grade !== 'none' && current.grade !== grade) {
      if (!window.confirm('Changing this grade updates the evaluation the client sees. Continue?')) return
    }
    await run(`grade:${id}`, () => api.updateFollowup(id, { grade, status: 'completed' }))
  }

  async function saveFeedback(id: string, currentGrade: string) {
    const feedback = (feedbackBuf[id] ?? '').trim()
    const grade = currentGrade && currentGrade !== '' ? currentGrade : 'none'
    await run(`feedback:${id}`, () => api.updateFollowup(id, { feedback, grade, status: 'completed' }))
    setFeedbackSaved({ ...feedbackSaved, [id]: true })
    setEditEval({ ...editEval, [id]: false })
  }

  const gradeLabel: Record<string, string> = { green: '🟢 Correctly done', yellow: '🟡 Partially done', red: '🔴 Needs improvement' }
  const fmtTs = (s?: string) => (s ? s.replace('T', ' ').slice(0, 16) : '')

  return (
    <div className="animate-fade-in">
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', marginBottom: '16px' }}>
        <div className="card-sm" style={{ textAlign: 'center' }}>
          <div className="statnum"><SlotNumber value={myTasks.length} /></div>
          <div style={{ fontSize: '0.68rem', color: 'var(--muted)', fontWeight: 600 }}>Total assigned</div>
        </div>
        <div className="card-sm" style={{ textAlign: 'center' }}>
          <div className="statnum" style={{ color: pendingCount ? 'var(--warn)' : 'var(--ok)' }}><SlotNumber value={pendingCount} /></div>
          <div style={{ fontSize: '0.68rem', color: 'var(--muted)', fontWeight: 600 }}>Awaiting clients</div>
        </div>
        <div className="card-sm" style={{ textAlign: 'center' }}>
          <div className="statnum" style={{ color: ungraded ? 'var(--accent)' : 'var(--ok)' }}><SlotNumber value={ungraded} /></div>
          <div style={{ fontSize: '0.68rem', color: 'var(--muted)', fontWeight: 600 }}>To grade</div>
        </div>
      </div>

      {/* Filter chips */}
      <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '14px', flexWrap: 'wrap' }}>
        {([
          ['all', `All (${myTasks.length})`],
          ['pending', `⏳ Pending (${pendingCount})`],
          ['overdue', `🔴 Overdue (${overdueCount})`],
          ['completed', `✅ Completed (${myTasks.length - pendingCount})`],
        ] as const).map(([key, label]) => (
          <button key={key} className={`chip${taskFilter === key ? ' active' : ''}`} onClick={() => setTaskFilter(key as any)}>{label}</button>
        ))}
        <select value={patientFilter} onChange={e => setPatientFilter(e.target.value)} style={{ marginLeft: 'auto', fontSize: '0.78rem', maxWidth: '190px' }}>
          <option value="">All clients</option>
          {(patients || []).map((p: any) => (
            <option key={p.username} value={p.username}>{p.name}</option>
          ))}
        </select>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '3fr 1fr', gap: '20px', alignItems: 'start' }} className="fu-grid">
        <div>
          <div className="expander" style={{ borderColor: showAssign ? 'var(--accent)' : 'var(--border)' }}>
            <div className="expander-header" onClick={() => setShowAssign(!showAssign)}>
              <span>➕ Assign new task</span><span>{showAssign ? '▲' : '▼'}</span>
            </div>
            {showAssign && (
              <div className="expander-body">
                <div style={{ display: 'flex', gap: '12px', marginBottom: '8px', flexWrap: 'wrap' }}>
                  <div style={{ flex: 1, minWidth: '160px' }}>
                    <label>Client</label>
                    <PatientSelector patients={patients} value={newPatient} onChange={setNewPatient} placeholder="Select…" />
                  </div>
                  <div style={{ flex: 2, minWidth: '200px' }}>
                    <label>Task title</label>
                    <input value={newTitle} onChange={e => setNewTitle(e.target.value)} placeholder="e.g. Breathing exercise" />
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '12px', marginBottom: '8px', flexWrap: 'wrap' }}>
                  <div style={{ flex: 2, minWidth: '200px' }}>
                    <label>Description</label>
                    <textarea value={newDesc} onChange={e => setNewDesc(e.target.value)} placeholder="What should the client do?" rows={3} />
                  </div>
                  <div style={{ flex: 1, minWidth: '150px' }}>
                    <label>Due date (optional)</label>
                    <input type="date" value={newDue} onChange={e => setNewDue(e.target.value)} style={{ width: '100%' }} />
                    <div style={{ marginTop: '8px' }}>
                      <label>Attachment (optional)</label>
                      <input type="file" onChange={e => setNewFile(e.target.files?.[0] || null)} style={{ width: '100%', fontSize: '0.8rem', color: 'var(--muted)' }} />
                    </div>
                  </div>
                </div>
                <button className="btn-primary" onClick={assignTask} style={{ marginTop: '8px', width: '100%' }}>📝 Assign task</button>

                <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
                  <button style={{ flex: 1, fontSize: '0.78rem' }} onClick={() => setShowTemplates(!showTemplates)}>
                    📚 {showTemplates ? 'Hide' : 'Use'} a template {templates.length > 0 ? `(${templates.length})` : ''}
                  </button>
                  {newTitle.trim() && (
                    <button style={{ flex: 1, fontSize: '0.78rem' }} onClick={saveAsTemplate} title="Save this task as a reusable template">
                      💾 Save as template
                    </button>
                  )}
                </div>

                {showTemplates && (
                  <div style={{ marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {!newPatient && (
                      <div style={{ color: 'var(--warn)', fontSize: '0.72rem', fontWeight: 600 }}>Select a client first, then tap a template to assign it.</div>
                    )}
                    {templates.length === 0 && (
                      <div style={{ color: 'var(--muted)', fontSize: '0.75rem', textAlign: 'center', padding: '10px' }}>
                        No templates yet — fill in a task above and tap “Save as template”.
                      </div>
                    )}
                    {templates.map((tpl: any) => (
                      <div key={tpl.id} className="card-sm" style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '9px 12px', opacity: newPatient ? 1 : 0.55 }}>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontWeight: 700, fontSize: '0.82rem', color: 'var(--heading)' }}>{tpl.title}</div>
                          <div style={{ color: 'var(--muted)', fontSize: '0.68rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                            {tpl.category}{tpl.times_used > 0 ? ` · used ${tpl.times_used}×` : ''}{tpl.default_due_days ? ` · due in ${tpl.default_due_days}d` : ''}
                          </div>
                        </div>
                        <button className="btn-primary" style={{ fontSize: '0.72rem', padding: '5px 12px' }} disabled={!newPatient || savingTpl} onClick={() => useTemplate(tpl)}>
                          {savingTpl ? '…' : 'Assign →'}
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          <h3 style={{ marginTop: '16px', marginBottom: '8px' }}>Assigned tasks</h3>
          {myTasks.length === 0 ? (
            <div className="card" style={{ textAlign: 'center', padding: '28px' }}>
              <div style={{ fontWeight: 700 }}>Nothing assigned yet</div>
              <div style={{ color: 'var(--muted)', fontSize: '0.8rem' }}>Use "Assign new task" or let the AI agent draft one.</div>
            </div>
          ) : (
            <div className="space-y-2">
              {filteredTasks.slice().reverse().map((t: any) => {
                const open = expanded[t.id]
                const due = dueInfo(t.due_date)
                return (
                  <div key={t.id} className="expander" style={{ borderColor: t.status === 'completed' && t.grade === 'red' ? 'color-mix(in srgb, var(--danger) 40%, transparent)' : 'var(--border)' }}>
                    <div className="expander-header" onClick={() => setExpanded({ ...expanded, [t.id]: !open })}>
                      <span style={{ display: 'flex', gap: '8px', alignItems: 'center', minWidth: 0 }}>
                        <strong style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{t.title}</strong>
                        <span style={{ color: 'var(--muted)', fontSize: '0.75rem', fontWeight: 500 }}>→ {t.patient_username}</span>
                      </span>
                      <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span className="badge-theme">{STATUS_BADGE[t.status]?.label || t.status}</span>
                        {t.grade && t.grade !== 'none' && <span>{t.grade === 'green' ? '🟢' : t.grade === 'yellow' ? '🟡' : '🔴'}</span>}
                        {open ? '▲' : '▼'}
                      </span>
                    </div>
                    {open && (
                      <div className="expander-body">
                        <div style={{ color: 'var(--soft)', fontSize: '0.82rem', marginBottom: '8px' }}>{t.description}</div>
                        {due && <div style={{ fontSize: '0.6875rem', color: due.color, marginBottom: '8px', fontWeight: 600 }}>{due.text}</div>}

                        {t.file_path && (
                          <div style={{ marginBottom: '8px' }}>
                            <a href={`/api/followups/${t.id}/download`} target="_blank" rel="noreferrer" style={{ fontSize: '0.75rem' }}>
                              {t.status === 'completed' ? '📤 View proof' : '📎 View attachment'}
                            </a>
                          </div>
                        )}

                        {t.status === 'completed' && (
                          <div>
                            <hr style={{ margin: '8px 0' }} />
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', flexWrap: 'wrap' }}>
                              <span style={{ fontWeight: 700, fontSize: '0.82rem' }}>Grade & feedback</span>
                              {t.grade && t.grade !== 'none' && (
                                <span style={{ color: t.grade === 'green' ? 'var(--ok)' : t.grade === 'yellow' ? 'var(--warn)' : 'var(--danger)', fontWeight: 700, fontSize: '0.82rem' }}>
                                  {gradeLabel[t.grade]}
                                </span>
                              )}
                              {!editEval[t.id] && (
                                <button style={{ fontSize: '0.68rem', padding: '4px 10px', marginLeft: 'auto' }}
                                  onClick={() => { setFeedbackBuf({ ...feedbackBuf, [t.id]: t.feedback ?? '' }); setEditEval({ ...editEval, [t.id]: true }) }}>
                                  ✏️ Edit evaluation
                                </button>
                              )}
                            </div>

                            {editEval[t.id] ? (
                              <div>
                                <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '10px', flexWrap: 'wrap' }}>
                                  <button className="btn-primary" style={{ fontSize: '0.75rem', padding: '6px 12px' }} disabled={busy[`grade:${t.id}`]} onClick={() => gradeTask(t.id, 'green')}>🟢 Correct</button>
                                  <button style={{ fontSize: '0.75rem', padding: '6px 12px' }} disabled={busy[`grade:${t.id}`]} onClick={() => gradeTask(t.id, 'yellow')}>🟡 Partial</button>
                                  <button className="btn-danger" style={{ fontSize: '0.75rem', padding: '6px 12px' }} disabled={busy[`grade:${t.id}`]} onClick={() => gradeTask(t.id, 'red')}>🔴 Needs work</button>
                                </div>
                                <label style={{ fontSize: '0.6875rem' }}>Written feedback for {t.patient_username}</label>
                                <textarea
                                  value={feedbackBuf[t.id] ?? t.feedback ?? ''}
                                  onChange={e => { setFeedbackBuf({ ...feedbackBuf, [t.id]: e.target.value }); setFeedbackSaved({ ...feedbackSaved, [t.id]: false }) }}
                                  rows={3}
                                  placeholder="e.g. Nice work on the breathing exercise — notice how calm you felt after. Let's build on this next week."
                                  style={{ width: '100%', fontSize: '0.82rem', resize: 'vertical', marginBottom: '6px' }}
                                />
                                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                                  <button className="btn-primary" style={{ fontSize: '0.72rem', padding: '6px 12px' }}
                                    disabled={busy[`feedback:${t.id}`]}
                                    onClick={() => saveFeedback(t.id, t.grade || 'none')}>
                                    {busy[`feedback:${t.id}`] ? 'Saving…' : '💬 Save feedback'}
                                  </button>
                                  <button style={{ fontSize: '0.72rem', padding: '6px 12px' }}
                                    disabled={busy[`feedback:${t.id}`]}
                                    onClick={() => setEditEval({ ...editEval, [t.id]: false })}>
                                    Cancel
                                  </button>
                                  {feedbackSaved[t.id] && (
                                    <span style={{ color: 'var(--ok)', fontSize: '0.6875rem', fontWeight: 700 }}>✓ Saved — visible to the client</span>
                                  )}
                                </div>
                              </div>
                            ) : (
                              <div>
                                {t.grade && t.grade !== 'none' ? (
                                  <div style={{ fontWeight: 700, fontSize: '0.82rem', marginBottom: '6px' }}>{gradeLabel[t.grade]}</div>
                                ) : (
                                  <div style={{ color: 'var(--muted)', fontSize: '0.75rem', marginBottom: '6px' }}>Not graded yet.</div>
                                )}
                                {t.feedback ? (
                                  <div style={{ marginBottom: '6px', padding: '10px 13px', borderRadius: '12px', background: 'var(--accent-soft)', border: '1px solid color-mix(in srgb, var(--accent) 25%, transparent)' }}>
                                    <div style={{ color: 'var(--accent)', fontSize: '0.65rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '4px' }}>💬 Feedback</div>
                                    <div style={{ color: 'var(--text)', fontSize: '0.82rem', lineHeight: 1.55 }}>{t.feedback}</div>
                                  </div>
                                ) : (
                                  <div style={{ color: 'var(--muted)', fontSize: '0.6875rem', marginBottom: '6px' }}>No written feedback yet.</div>
                                )}
                                {(t.feedback_updated_at || t.grade_updated_at || t.approved_at) && (
                                  <div style={{ color: 'var(--muted)', fontSize: '0.6875rem' }}>
                                    Last evaluated: {fmtTs(t.feedback_updated_at || t.grade_updated_at || t.approved_at)}
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        )}

                        <div style={{ color: 'var(--muted)', fontSize: '0.65rem', marginTop: '8px' }}>Assigned {formatDate(t.assigned_at)}{t.due_date ? ` · Due ${formatDate(t.due_date)}` : ''}</div>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>

        <div className="psych-box">
          <div className="psych-box-title">🤖 Follow-up agent</div>
          <div className="psych-box-desc">AI drafts homework from the client's latest journals</div>
          <PatientSelector patients={patients} value={aiPatient} onChange={setAiPatient} placeholder="Select client…" style={{ marginBottom: '8px', fontSize: '0.8125rem', padding: '8px' }} />
          <button onClick={analyze} disabled={!aiPatient || agentBusy} className="btn-primary" style={{ width: '100%', fontSize: '0.8125rem' }}>
            {agentBusy ? 'Analyzing…' : 'Analyze & draft tasks'}
          </button>

          {agentResult && (
            <div className="ai-box" style={{ marginTop: '10px' }}>
              <div style={{ color: 'var(--muted)', fontSize: '0.6875rem', marginBottom: '6px' }}>{agentResult.reasoning}</div>
              {agentResult.tasks?.map((task: any, i: number) => (
                <div key={i} className="card-sm" style={{ margin: '6px 0', padding: '10px' }}>
                  <div style={{ color: 'var(--accent)', fontSize: '0.8125rem', fontWeight: 700 }}>{task.title}</div>
                  <div style={{ color: 'var(--secondary)', fontSize: '0.75rem', marginTop: '4px' }}>{task.description}</div>
                  {assignedId === i ? (
                    <div style={{ color: 'var(--ok)', fontSize: '0.7rem', fontWeight: 700, marginTop: '6px' }}>✅ Assigned to {aiPatient}</div>
                  ) : (
                    <button className="btn-lime" style={{ fontSize: '0.6875rem', padding: '4px 10px', marginTop: '6px' }}
                      disabled={assigningId !== null || !aiPatient}
                      onClick={() => assignDraft(i, task)}>
                      {assigningId === i ? 'Assigning…' : '📝 Assign now'}
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
      <style>{`@media (max-width: 1100px) { .fu-grid { grid-template-columns: 1fr !important; } }`}</style>
    </div>
  )
}
