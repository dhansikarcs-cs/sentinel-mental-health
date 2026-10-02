import { useEffect, useState } from 'react'
import { getUser, fetchMe } from '../stores/auth'
import { api } from '../api/client'
import CustomSelect from '../components/CustomSelect'
import { EMAIL_RE, COUNTRIES, TIMEZONES } from '../constants'
import { useAdvancedPanels, setAdvancedPanels } from '../hooks/useAdvanced'

export default function ProfilePage() {
  const user = getUser()
  const [contact, setContact] = useState(user?.contact_info || '')
  const [trusted, setTrusted] = useState(user?.trusted_contact || '')
  const [country, setCountry] = useState(user?.country || '')
  const [timezone, setTimezone] = useState(user?.timezone || '')
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState('')
  const [ok, setOk] = useState(false)
  const [tools, setTools] = useState<any[]>([])
  const [newTool, setNewTool] = useState({ title: '', description: '', category: 'calming' })
  const [toolBusy, setToolBusy] = useState(false)
  const [toolErr, setToolErr] = useState('')
  const isPatient = user?.role === 'patient'
  const advanced = useAdvancedPanels()

  useEffect(() => {
    setContact(user?.contact_info || '')
    setTrusted(user?.trusted_contact || '')
    setCountry(user?.country || '')
    setTimezone(user?.timezone || '')
  }, [user])

  useEffect(() => {
    if (isPatient) api.getCopingTools().then((d: any) => setTools(Array.isArray(d) ? d : [])).catch(() => {})
  }, [isPatient])

  async function addTool(e: React.FormEvent) {
    e.preventDefault()
    if (!newTool.title.trim()) { setToolErr('Give the strategy a name.'); return }
    setToolBusy(true); setToolErr('')
    try {
      const t = await api.createCopingTool(newTool)
      setTools(prev => [...prev, t])
      setNewTool({ title: '', description: '', category: 'calming' })
    } catch (err: any) { setToolErr(err.message || 'Failed to add') }
    setToolBusy(false)
  }

  async function removeTool(id: number) {
    try { await api.deleteCopingTool(id); setTools(prev => prev.filter(t => t.id !== id)) } catch {}
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    setMsg('')
    const isPsych = user?.role === 'psychologist'
    const tc = trusted.trim()
    const own = contact.trim()
    if (tc && !EMAIL_RE.test(tc)) {
      setMsg('Trusted contact must be a valid email address (crisis alerts are sent there).')
      setOk(false)
      setSaving(false)
      return
    }
    if (isPsych && own && !EMAIL_RE.test(own)) {
      setMsg('Your contact must be a valid email address (crisis alerts are sent to you there).')
      setOk(false)
      setSaving(false)
      return
    }
    try {
      await api.updateContact({ contact_info: contact, trusted_contact: trusted })
      await api.updatePreferences({ country, timezone })
      await fetchMe()
      setMsg('Saved successfully.')
      setOk(true)
    } catch (err: any) {
      setMsg(err.message || 'Failed to save')
      setOk(false)
    } finally {
      setSaving(false)
    }
  }

  if (!user) return null

  const initials = (user.name || user.username || '?').split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase()

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Identity card */}
      <div className="lead-card dark" style={{ padding: '22px 24px', flexDirection: 'row', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }} data-tour="profile">
        <div className="avatar" style={{ width: 56, height: 56, minWidth: 56, fontSize: '1.2rem', background: 'var(--lime)', color: 'var(--lime-ink)' }}>
          {initials}
        </div>
        <div style={{ flex: 1, minWidth: '200px' }}>
          <div style={{ fontSize: '1.3rem', fontWeight: 800, color: 'var(--on-ink)' }}>{user.name}</div>
          <div style={{ color: '#A6AC9D', fontSize: '0.75rem', marginTop: '2px' }}>
            @{user.username} · <span className="badge-psych">{user.role === 'psychologist' ? '🧑‍⚕️ Psychologist' : '🧑 Client'}</span>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          <span style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.14)', borderRadius: 999, padding: '6px 13px', fontSize: '0.68rem', fontWeight: 700, color: 'var(--on-ink)' }}>
            🏥 {user.clinic || '—'}
          </span>
          {user.assigned_psych && (
            <span style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.14)', borderRadius: 999, padding: '6px 13px', fontSize: '0.68rem', fontWeight: 700, color: 'var(--on-ink)' }}>
              🧑‍⚕️ {user.assigned_psych}
            </span>
          )}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px', alignItems: 'start' }} className="profile-grid">
        <form onSubmit={handleSave} className="card" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <h3 style={{ margin: 0 }}>Contact & safety</h3>
          <div>
            <label>Contact info</label>
            <input value={contact} onChange={e => setContact(e.target.value)} placeholder={user?.role === 'psychologist' ? 'Your email (crisis alerts sent here)' : 'Phone or email'} />
          </div>
          <div>
            <label>Trusted contact</label>
            <input value={trusted} onChange={e => setTrusted(e.target.value)} placeholder="Trusted contact email (crisis alerts sent there)" />
            <div style={{ fontSize: '0.66rem', color: 'var(--faint)', marginTop: '4px' }}>Used by the 30-second escalation step in an active crisis.</div>
          </div>
          <div>
            <label>Country & timezone</label>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
              <CustomSelect
                value={country}
                onChange={setCountry}
                searchable
                placeholder="Country…"
                options={[{ value: '', label: 'Country…' }, ...COUNTRIES.map(c => ({ value: c, label: c }))]}
              />
              <CustomSelect
                value={timezone}
                onChange={setTimezone}
                searchable
                placeholder="Auto (based on country)"
                options={[{ value: '', label: 'Auto (based on country)' }, ...TIMEZONES.map(t => ({ value: t.value, label: t.label }))]}
              />
            </div>
            <div style={{ fontSize: '0.66rem', color: 'var(--faint)', marginTop: '4px' }}>Birthday wishes & daily check-in cards follow this timezone.</div>
          </div>
          <div className="flex items-center gap-3">
            <button type="submit" disabled={saving} className="btn-primary">{saving ? 'Saving…' : '💾 Save changes'}</button>
            {msg && <span style={{ fontSize: '0.75rem', fontWeight: 600, color: ok ? 'var(--ok)' : 'var(--danger)' }}>{msg}</span>}
          </div>
        </form>

        <div className="card" style={{ padding: '24px' }}>
          <h3 style={{ marginBottom: '12px' }}>How your data is protected</h3>
          <div className="space-y-3">
            {[
              { icon: '🔐', title: 'Encrypted at rest', desc: 'Journal text and contacts are encrypted (Fernet) before they touch the database.' },
              { icon: '⏱️', title: 'Sessions expire', desc: 'Login tokens last 8 hours and refresh silently while you work.' },
              { icon: '🧾', title: 'Audit trail', desc: 'Every sensitive read is hash-chained into a tamper-evident audit log.' },
              { icon: '🫥', title: 'AI never sees raw text unchecked', desc: 'Summaries are derived on-device/on-cloud per policy; raw journals are never exposed to other clients.' },
            ].map(item => (
              <div key={item.title} style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                <span style={{ fontSize: '1.2rem' }}>{item.icon}</span>
                <div>
                  <div style={{ fontWeight: 700, fontSize: '0.82rem' }}>{item.title}</div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--muted)', lineHeight: 1.5 }}>{item.desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Advanced settings ── */}
      <div className="card" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '14px', flexWrap: 'wrap' }}>
          <div style={{ flex: 1, minWidth: '240px' }}>
            <h3 style={{ margin: 0 }}>⚙️ Advanced settings</h3>
            <div style={{ fontSize: '0.75rem', color: 'var(--muted)', marginTop: '4px', lineHeight: 1.5 }}>
              Advanced clinical panels — weekly activity digest and caseload health summary on Patient Triage.
            </div>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={advanced}
            aria-label="Advanced clinical panels"
            onClick={() => setAdvancedPanels(!advanced)}
            style={{
              width: 52, height: 30, borderRadius: 999, border: 'none', cursor: 'pointer', flexShrink: 0,
              background: advanced ? 'var(--lime)' : 'var(--border-strong)',
              position: 'relative', transition: 'background 0.18s ease',
            }}
          >
            <span style={{
              position: 'absolute', top: 3, left: advanced ? 25 : 3, width: 24, height: 24, borderRadius: 999,
              background: advanced ? 'var(--lime-ink)' : 'var(--surface)',
              boxShadow: '0 1px 4px rgba(0,0,0,0.25)', transition: 'left 0.18s ease',
            }} />
          </button>
        </div>
        {advanced && (
          <div style={{ marginTop: '12px', fontSize: '0.72rem', color: 'var(--accent)', fontWeight: 700 }}>
            ✅ Advanced panels are ON — see them at the top of Patient Triage.
          </div>
        )}
      </div>

      {isPatient && (
        <div className="card" style={{ padding: '24px' }}>
          <h3 style={{ marginBottom: '4px' }}>🧰 My coping toolbox</h3>
          <div style={{ fontSize: '0.72rem', color: 'var(--muted)', marginBottom: '14px' }}>
            Strategies that help <em>you</em>. During a crisis these appear right on the crisis screen, one tap away.
          </div>
          <form onSubmit={addTool} style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr 1.6fr auto', gap: '8px', alignItems: 'start', marginBottom: '12px' }} className="toolbox-form">
            <div>
              <input value={newTool.title} onChange={e => setNewTool(t => ({ ...t, title: e.target.value }))} placeholder="Strategy name…" maxLength={80} />
            </div>
            <CustomSelect
              value={newTool.category}
              onChange={v => setNewTool(t => ({ ...t, category: v }))}
              options={[
                { value: 'calming', label: '😌 Calming' },
                { value: 'distraction', label: '🎧 Distraction' },
                { value: 'physical', label: '🏃 Physical' },
                { value: 'social', label: '💬 Social' },
                { value: 'professional', label: '🧑‍⚕️ Professional' },
              ]}
            />
            <div>
              <input value={newTool.description} onChange={e => setNewTool(t => ({ ...t, description: e.target.value }))} placeholder="Optional note (e.g. the exact steps)" maxLength={500} />
            </div>
            <button type="submit" className="btn-primary" disabled={toolBusy}>{toolBusy ? '…' : '+ Add'}</button>
          </form>
          {toolErr && <div style={{ color: 'var(--danger)', fontSize: '0.75rem', fontWeight: 600, marginBottom: '8px' }}>{toolErr}</div>}
          {tools.length === 0 ? (
            <div style={{ color: 'var(--faint)', fontSize: '0.78rem' }}>Nothing here yet — add the first strategy above.</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {tools.map(t => (
                <div key={t.id} style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '9px 12px', borderRadius: 12, background: 'var(--surface-soft)', border: '1px solid var(--border-soft)' }}>
                  <span style={{ fontSize: '0.8rem', fontWeight: 700, flex: 1 }}>
                    {t.title}
                    {t.recommended_by && <span style={{ display: 'block', fontSize: '0.64rem', color: 'var(--accent)', fontWeight: 800 }}>🧑‍⚕️ suggested by {t.recommended_by}</span>}
                    {t.description && <span style={{ display: 'block', fontSize: '0.68rem', color: 'var(--muted)', fontWeight: 500 }}>{t.description}</span>}
                  </span>
                  <span style={{ fontSize: '0.62rem', fontWeight: 700, color: 'var(--faint)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{t.category}</span>
                  <button onClick={() => removeTool(t.id)} style={{ padding: '2px 9px', fontSize: '0.7rem' }} title="Remove">✕</button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
      <style>{`
        @media (max-width: 900px) { .profile-grid { grid-template-columns: 1fr !important; } }
        @media (max-width: 760px) { .toolbox-form { grid-template-columns: 1fr 1fr !important; } }
      `}</style>
    </div>
  )
}
