import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import AiSourceBadge from '../components/AiSourceBadge'
import PastReports from '../components/PastReports'
import PatientSelector, { usePatientContext } from '../components/PatientSelector'
import PrioritiesPanel from '../components/PrioritiesPanel'
import StressSpikes from '../components/StressSpikes'
import { moodIcon, formatTime, formatDate } from '../constants'

export default function ConsultationPage() {
  const { patients } = usePatientContext()
  const [searchParams, setSearchParams] = useSearchParams()
  const preselect = searchParams.get('patient') || ''
  const [selected, setSelected] = useState(preselect)
  const [overview, setOverview] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  // Arriving from Triage's "Open session" with ?patient= — preselect + clean the URL
  useEffect(() => {
    if (preselect && preselect !== selected) setSelected(preselect)
    if (preselect) setSearchParams({}, { replace: true })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [preselect])

  const [rawNotes, setRawNotes] = useState('')
  const [saving, setSaving] = useState(false)
  const [aiDraft, setAiDraft] = useState<any>(null)
  const [updating, setUpdating] = useState<string | null>(null)

  useEffect(() => {
    if (!selected) { setOverview(null); return }
    setLoading(true)
    api.getPatientOverview(selected)
      .then(d => setOverview(d))
      .catch(() => setOverview(null))
      .finally(() => setLoading(false))
  }, [selected])

  async function saveNote() {
    if (!selected || !rawNotes.trim()) return
    setSaving(true)
    try {
      await api.createPsychNote({ patient_username: selected, raw_notes: rawNotes })
      setRawNotes('')
      setAiDraft(null)
    } catch (err: any) { alert(err.message) }
    setSaving(false)
  }

  async function generateAiDraft() {
    if (!selected || !rawNotes.trim()) return
    try {
      setAiDraft(await api.synthesizeNote(rawNotes))
    } catch {
      try { setAiDraft(await api.journalToNote(selected, rawNotes)) } catch {}
    }
  }

  async function completeFollowup(id: string) {
    setUpdating(id)
    try {
      await api.updateFollowup(id, { status: 'completed' })
      const updated = await api.getPatientOverview(selected)
      setOverview(updated)
    } catch (err: any) { alert(err.message) }
    setUpdating(null)
  }

  const identity = overview?.patient || {}

  return (
    <div className="animate-fade-in">
      <PatientSelector
        patients={patients}
        value={selected}
        onChange={setSelected}
        placeholder="-- Select client to open session --"
        style={{ marginBottom: '16px', maxWidth: '420px' }}
      />

      {!selected && (
        <div className="card" style={{ textAlign: 'center', padding: '44px' }}>
          <div style={{ fontSize: '2.2rem', marginBottom: '8px' }}>🧑‍⚕️</div>
          <div style={{ fontWeight: 800, fontSize: '1.05rem', marginBottom: '4px' }}>Compose the session workspace</div>
          <div style={{ color: 'var(--muted)', fontSize: '0.82rem' }}>Pick a client above — brief, note editor and care actions appear here.</div>
        </div>
      )}

      {selected && loading && (
        <div className="card" style={{ textAlign: 'center', padding: '28px', color: 'var(--muted)' }}>Preparing session…</div>
      )}

      {selected && !loading && !overview && (
        <div className="card" style={{ textAlign: 'center', padding: '28px', color: 'var(--danger)' }}>Failed to load client state.</div>
      )}

      {selected && !loading && overview && (
        <>
          <SessionPrepCard patient={selected} />
          <Workspace overview={overview} selected={selected} rawNotes={rawNotes} setRawNotes={setRawNotes}
            saving={saving} saveNote={saveNote} generateAiDraft={generateAiDraft} aiDraft={aiDraft} setAiDraft={setAiDraft}
            updating={updating} completeFollowup={completeFollowup} />
          <div className="card">
            <StressSpikes username={selected} compact />
          </div>
          <PastReports patient={selected} />
        </>
      )}
    </div>
  )
}

function Workspace({ overview, selected, rawNotes, setRawNotes, saving, saveNote, generateAiDraft, aiDraft, setAiDraft, updating, completeFollowup }: any) {
  const identity = overview.patient || {}
  const changes = overview.changes_since_last_visit || {}
  const followups = overview.followups || {}
  const risk = overview.risk
  const crisis = overview.crisis
  const brief = overview.clinical_brief
  const followupList: any[] = followups.list || []

  return (
    <>
      {/* Session header */}
      <div className="lead-card dark" data-tour="session" style={{ padding: '20px 22px', marginBottom: '16px', flexDirection: 'row', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div className="avatar" style={{ width: 52, height: 52, minWidth: 52, background: 'var(--lime)', color: 'var(--lime-ink)', fontSize: '1.1rem' }}>
          {(identity.name || identity.username || '?').split(' ').map((w: string) => w[0]).slice(0, 2).join('').toUpperCase()}
        </div>
        <div style={{ flex: 1, minWidth: '200px' }}>
          <div style={{ color: '#A6AC9D', fontSize: '0.62rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '2px' }}>Session open for</div>
          <div style={{ fontSize: '1.35rem', fontWeight: 800, color: 'var(--on-ink)' }}>{identity.name || identity.username}</div>
          <div style={{ color: '#A6AC9D', fontSize: '0.72rem', marginTop: '2px' }}>
            @{identity.username} · {identity.age || '?'} yrs · {identity.occupation || identity.clinic || '—'}
          </div>
        </div>
        <div style={{ textAlign: 'right', fontSize: '0.72rem', color: '#A6AC9D' }}>
          {overview.last_appointment ? (
            <>
              <div style={{ color: 'var(--on-ink)', fontWeight: 700, fontSize: '0.85rem' }}>
                {formatDate(overview.last_appointment.date)} · {overview.last_appointment.time}
              </div>
              <div>{overview.last_appointment.session_type || 'Session'} · {overview.last_appointment.status}</div>
            </>
          ) : (
            <div>No appointments yet</div>
          )}
          {crisis && (
            <div style={{ marginTop: '6px', color: 'var(--danger)', fontWeight: 800, fontSize: '0.7rem', background: 'rgba(255,255,255,0.08)', padding: '4px 10px', borderRadius: 999, display: 'inline-block' }}>
              🚨 CRISIS ACTIVE · {crisis.acknowledged ? 'acknowledged' : 'NOT acknowledged'}
            </div>
          )}
        </div>
      </div>

      {(overview.alerts || []).length > 0 && (
        <div style={{ marginBottom: '16px' }}>
          {overview.alerts.map((a: string, i: number) => (
            <div key={i} style={{ background: 'var(--danger-soft)', border: '1px solid color-mix(in srgb, var(--danger) 33%, transparent)', color: 'var(--danger-deep)', borderRadius: '14px', padding: '9px 14px', fontSize: '0.78rem', fontWeight: 600, marginBottom: '6px' }}>
              ⚠️ {a}
            </div>
          ))}
        </div>
      )}

      <PrioritiesPanel priorities={overview.priorities} />

      {/* Snapshots */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '10px', marginBottom: '16px' }}>
        <div className="card-sm">
          <div style={{ color: 'var(--muted)', fontSize: '0.6rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.07em' }}>Mood trend</div>
          <div style={{ fontSize: '1.15rem', fontWeight: 800, color: changes.mood_trend === 'declining' ? 'var(--danger)' : changes.mood_trend === 'improving' ? 'var(--ok)' : 'var(--warn)' }}>
            {changes.mood_trend === 'declining' ? '↘ declining' : changes.mood_trend === 'improving' ? '↗ improving' : changes.mood_trend === 'stable' ? '→ stable' : '—'}
          </div>
          <div style={{ fontSize: '0.62rem', color: 'var(--muted)' }}>
            Now {changes.current_mood_avg ? Number(changes.current_mood_avg).toFixed(1) : '—'} / prev {changes.previous_mood_avg ? Number(changes.previous_mood_avg).toFixed(1) : '—'}
          </div>
        </div>
        <div className="card-sm">
          <div style={{ color: 'var(--muted)', fontSize: '0.6rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.07em' }}>Engagement</div>
          <div style={{ fontSize: '1.15rem', fontWeight: 800 }}>{changes.journal_count_7 || 0} <span style={{ fontSize: '0.65rem', color: 'var(--muted)' }}>journals / 7d</span></div>
          <div style={{ fontSize: '0.62rem', color: changes.engagement_trend === 'declining' ? 'var(--danger)' : 'var(--ok)', fontWeight: 700 }}>{changes.journal_count_14 || 0} in 14d</div>
        </div>
        <div className="card-sm">
          <div style={{ color: 'var(--muted)', fontSize: '0.6rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.07em' }}>Risk</div>
          <div style={{ fontSize: '1.15rem', fontWeight: 800, color: risk?.triggered ? 'var(--danger)' : risk && risk.risk_score >= 7 ? 'var(--warn)' : 'var(--ok)' }}>
            {risk ? `${risk.risk_score}/10` : 'N/A'}
          </div>
          <div style={{ fontSize: '0.62rem', color: 'var(--muted)' }}>{risk ? `${formatDate(risk.created_at)} · v${risk.algorithm_version || '?'}` : 'no assessments'}</div>
        </div>
        <div className="card-sm">
          <div style={{ color: 'var(--muted)', fontSize: '0.6rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.07em' }}>Follow-ups</div>
          <div style={{ fontSize: '1.15rem', fontWeight: 800, color: followups.pending > 0 ? 'var(--warn)' : 'var(--ok)' }}>{followups.pending || 0} open</div>
          <div style={{ fontSize: '0.62rem', color: 'var(--muted)' }}>{followups.completed || 0} completed</div>
        </div>
      </div>

      {/* Brief + note editor */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }} className="ws-grid">
        <div className="card">
          <div style={{ color: 'var(--accent)', fontWeight: 800, fontSize: '0.68rem', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '8px' }}>Clinical brief</div>
          {brief ? (
            <>
              <div style={{ color: 'var(--muted)', fontSize: '0.62rem', marginBottom: '6px' }}>{formatTime(brief.timestamp)}</div>
              <div style={{ color: 'var(--soft)', fontSize: '0.78rem', lineHeight: 1.65 }}>
                {(brief.clinical_summary || brief.summary || '').slice(0, 360)}
              </div>
              {(brief.emotions || '').length > 0 && (
                <div style={{ color: 'var(--muted)', fontSize: '0.65rem', marginTop: '8px' }}>Emotions: {brief.emotions}</div>
              )}
            </>
          ) : (
            <div style={{ color: 'var(--muted)', fontSize: '0.75rem' }}>No recent journals.</div>
          )}
        </div>

        <div className="card">
          <div style={{ color: 'var(--accent)', fontWeight: 800, fontSize: '0.68rem', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '8px' }}>AI analysis trace</div>
          {brief?.ai_analysis?.explanation ? (
            <div style={{ color: 'var(--soft)', fontSize: '0.78rem', lineHeight: 1.65 }}>{brief.ai_analysis.explanation.slice(0, 320)}</div>
          ) : (
            <div style={{ color: 'var(--muted)', fontSize: '0.75rem' }}>No summary available.</div>
          )}
          {brief?.ai_analysis && (
            <div style={{ color: 'var(--faint)', fontSize: '0.6rem', marginTop: '10px', lineHeight: 1.7 }}>
              <AiSourceBadge source={brief.ai_analysis.provider} detailed />
              <span style={{ marginLeft: '6px' }}>
                {brief.ai_analysis.provider || 'rule'} · prompt {brief.ai_analysis.prompt_version || 'rule'}
                {brief.ai_analysis.model_version ? ` · model v${brief.ai_analysis.model_version}` : ''}
                {brief.ai_analysis.confidence ? ` · confidence ${(brief.ai_analysis.confidence * 100).toFixed(0)}%` : ''}
              </span>
            </div>
          )}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }} className="ws-grid">
        <div className="card">
          <div style={{ color: 'var(--accent)', fontWeight: 800, fontSize: '0.68rem', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '10px' }}>✍️ Session note</div>
          <textarea
            value={rawNotes}
            onChange={e => setRawNotes(e.target.value)}
            placeholder="Enter session observations…"
            rows={7}
            style={{ width: '100%', padding: '13px', fontSize: '0.85rem', resize: 'none', marginBottom: '10px', lineHeight: 1.6, borderRadius: '14px' }}
          />
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            <button onClick={saveNote} disabled={saving || !selected || !rawNotes.trim()} className="btn-primary">
              {saving ? 'Saving…' : '💾 Save note'}
            </button>
            <button onClick={generateAiDraft} disabled={!selected || !rawNotes.trim()}>
              🤖 AI draft
            </button>
          </div>
          {aiDraft && (
            <div className="ai-box" style={{ marginTop: '10px' }}>
              <div className="ai-header">🤖 AI clinical draft</div>
              <div className="ai-body" style={{ whiteSpace: 'pre-wrap' }}>{aiDraft.note || aiDraft.suggestion}</div>
              <div style={{ display: 'flex', gap: '8px', marginTop: '10px' }}>
                <button className="btn-primary" style={{ fontSize: '0.72rem', padding: '5px 12px' }} onClick={() => setRawNotes(aiDraft.note || aiDraft.suggestion)}>✓ Use draft</button>
                <button style={{ fontSize: '0.72rem', padding: '5px 12px' }} onClick={() => setAiDraft(null)}>✕ Dismiss</button>
              </div>
            </div>
          )}
        </div>

        <div className="card">
          <div style={{ color: 'var(--accent)', fontWeight: 800, fontSize: '0.68rem', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '10px' }}>✅ Follow-up actions</div>
          {followupList.filter((f: any) => f.status === 'pending').length === 0 ? (
            <div style={{ color: 'var(--muted)', fontSize: '0.75rem' }}>No pending follow-ups. All caught up! 🎉</div>
          ) : (
            followupList.filter((f: any) => f.status === 'pending').map((f: any) => (
              <div key={f.id} style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ color: 'var(--heading)', fontSize: '0.78rem', fontWeight: 700 }}>{f.title}</div>
                  <div style={{ color: 'var(--muted)', fontSize: '0.62rem' }}>
                    assigned {f.assigned_at ? formatDate(f.assigned_at) : '—'}{f.grade && f.grade !== 'none' ? ` · ${f.grade}` : ''}
                  </div>
                </div>
                <button
                  onClick={() => completeFollowup(f.id)}
                  disabled={updating === f.id}
                  style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--ok)', padding: '5px 11px', borderRadius: 999, fontSize: '0.65rem', cursor: 'pointer', fontWeight: 700, whiteSpace: 'nowrap' }}
                >
                  {updating === f.id ? '…' : '✓ Complete'}
                </button>
              </div>
            ))
          )}
          {followupList.filter((f: any) => f.status === 'completed').length > 0 && (
            <div style={{ marginTop: '10px', fontSize: '0.62rem', color: 'var(--muted)' }}>
              {followupList.filter((f: any) => f.status === 'completed').length} completed all-time
            </div>
          )}
        </div>
      </div>

      {(overview.mood_trend || []).length > 0 && (
        <div className="card" style={{ padding: '14px', marginTop: '16px' }}>
          <div style={{ color: 'var(--muted)', fontSize: '0.62rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: '8px' }}>Mood strip (14d)</div>
          <div style={{ display: 'flex', gap: '4px', fontSize: '1.1rem', flexWrap: 'wrap' }}>
            {(overview.mood_trend || []).map((m: any, i: number) => (
              <span key={i} style={{ opacity: i === 0 ? 1 : 0.55 }} title={`${m.label} ${formatDate(m.timestamp)}`}>{moodIcon(m.label)}</span>
            ))}
          </div>
        </div>
      )}
      <style>{`@media (max-width: 1000px) { .ws-grid { grid-template-columns: 1fr !important; } }`}</style>
    </>
  )
}

/** AI-drafted session agenda, shown at the top of the workspace. */
function SessionPrepCard({ patient }: { patient: string }) {
  const [prep, setPrep] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!patient) return
    setLoading(true)
    api.getNextSessionPrep(patient)
      .then(setPrep)
      .catch(() => setPrep(null))
      .finally(() => setLoading(false))
  }, [patient])

  if (!patient || loading) return null
  if (!prep?.agenda?.length) return null

  const ctx = prep.context || {}
  return (
    <div className="card" style={{ padding: '18px 22px', marginBottom: '14px', background: 'var(--accent-soft)', borderColor: 'color-mix(in srgb, var(--accent) 25%, transparent)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px', flexWrap: 'wrap' }}>
        <span style={{ color: 'var(--accent)', fontWeight: 800, fontSize: '0.66rem', textTransform: 'uppercase', letterSpacing: '0.08em' }}>🤖 AI session prep</span>
        {prep.source === 'ai' ? <span className="badge-theme" style={{ fontSize: '0.6rem' }}>AI draft</span> : <span className="badge-theme" style={{ fontSize: '0.6rem' }}>Rule-based</span>}
        <span style={{ marginLeft: 'auto', display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
          {ctx.mood_trend && ctx.mood_trend !== 'unknown' && <span className="badge-theme">mood {ctx.mood_trend}</span>}
          {ctx.journals_7d !== undefined && <span className="badge-theme">{ctx.journals_7d} journals 7d</span>}
          {ctx.pending_followups > 0 && <span className="badge-theme">{ctx.pending_followups} pending tasks</span>}
          {ctx.crisis && <span className="badge-theme" style={{ color: 'var(--danger)', fontWeight: 800 }}>🚨 recent crisis</span>}
        </span>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '5px', marginBottom: '10px' }}>
        {prep.agenda.map((a: string, i: number) => (
          <div key={i} style={{ display: 'flex', gap: '8px', fontSize: '0.8rem', color: 'var(--text)', lineHeight: 1.5 }}>
            <span style={{ color: 'var(--accent)', fontWeight: 800 }}>{i + 1}.</span>
            <span>{a}</span>
          </div>
        ))}
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }} className="prep-grid">
        <div className="card-sm" style={{ padding: '10px 12px' }}>
          <div style={{ fontSize: '0.62rem', fontWeight: 800, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: '3px' }}>Opening question</div>
          <div style={{ fontSize: '0.78rem', color: 'var(--heading)', fontWeight: 600, lineHeight: 1.5 }}>“{prep.opening_question}”</div>
        </div>
        <div className="card-sm" style={{ padding: '10px 12px' }}>
          <div style={{ fontSize: '0.62rem', fontWeight: 800, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: '3px' }}>Watch for</div>
          <div style={{ fontSize: '0.78rem', color: 'var(--heading)', fontWeight: 600, lineHeight: 1.5 }}>{prep.watch_for}</div>
        </div>
      </div>
      <style>{`@media (max-width: 700px) { .prep-grid { grid-template-columns: 1fr !important; } }`}</style>
    </div>
  )
}
