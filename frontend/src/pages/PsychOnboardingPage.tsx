import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getUser, fetchMe } from '../stores/auth'
import { api } from '../api/client'
import { EMAIL_RE } from '../constants'

const STEPS = [
  { emoji: '🏠', label: 'Profile' },
  { emoji: '📞', label: 'Contact' },
  { emoji: '👥', label: 'Trusted' },
  { emoji: '🔮', label: 'Tips' },
  { emoji: '✅', label: 'Done' },
]

export default function PsychOnboardingPage() {
  const navigate = useNavigate()
  const user = getUser()
  const [step, setStep] = useState(0)
  const [contactInfo, setContactInfo] = useState('')
  const [trustedContact, setTrustedContact] = useState('')
  const [contactError, setContactError] = useState('')
  const [tcError, setTcError] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    api.getMe().then((d: any) => {
      if (d.onboarding_step >= 99) navigate('/triage')
      setStep(d.onboarding_step || 0)
      setContactInfo(d.contact_info || '')
      setTrustedContact(d.psych_trusted_contact || '')
    }).catch(() => {})
  }, [])

  async function advance(s: number) {
    try { await api.updateOnboarding(s) } catch {}
    setStep(s)
  }

  async function handleSaveContact() {
    const email = contactInfo.trim()
    if (email && !EMAIL_RE.test(email)) {
      setContactError('Enter a valid email — crisis alerts to you are sent there.')
      return
    }
    setContactError('')
    setSaving(true)
    try {
      await api.updateContact({ contact_info: email, trusted_contact: '' })
    } catch {}
    setSaving(false)
    advance(2)
  }

  async function handleSaveTrusted() {
    const tc = trustedContact.trim()
    if (tc && !EMAIL_RE.test(tc)) {
      setTcError('Enter a valid email address — crisis alerts are sent there.')
      return
    }
    setTcError('')
    setSaving(true)
    try {
      await api.updateContact({ contact_info: contactInfo, trusted_contact: tc })
    } catch {}
    setSaving(false)
    advance(3)
  }

  async function finish() {
    try { await api.updateOnboarding(99) } catch {}
    await fetchMe()
    navigate('/triage')
  }

  return (
    <div className="min-h-screen flex items-center justify-center" style={{ padding: '28px', background: 'var(--bg)' }}>
      <div style={{
        position: 'fixed', top: '-140px', left: '-140px', width: '420px', height: '420px',
        borderRadius: '999px', background: 'radial-gradient(circle, var(--lime) 0%, transparent 70%)',
        opacity: 0.4, pointerEvents: 'none',
      }} />
      <div style={{ width: '100%', maxWidth: '600px', position: 'relative', zIndex: 1 }}>
        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
            <div style={{ width: 36, height: 36, borderRadius: 999, background: 'var(--ink)', color: 'var(--lime)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1rem' }}>✳</div>
            <span style={{ fontWeight: 800, fontSize: '1.1rem' }}>Sentinel</span>
          </div>
          <h1 className="page-title" style={{ fontSize: 'clamp(1.7rem, 4vw, 2.3rem)' }}>Clinician setup</h1>
          <div className="page-sub">Five steps to your workspace</div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '6px', marginBottom: '16px' }}>
          {STEPS.map((s, i) => {
            const done = i < step
            const active = i === step
            return (
              <div key={i} className={done ? 'card-sm step-done' : active ? 'card-sm step-active' : 'card-sm step-pending'}
                style={{ textAlign: 'center', padding: '11px 4px', transition: 'all 0.3s', margin: 0 }}>
                <div style={{ fontSize: '1.15rem' }}>{done ? '✅' : s.emoji}</div>
                <div style={{ color: done ? 'var(--ok)' : active ? 'var(--heading)' : 'var(--faint)', fontSize: '0.58rem', fontWeight: active || done ? 800 : 500, marginTop: '3px' }}>{s.label}</div>
              </div>
            )
          })}
        </div>

        <div className="track" style={{ marginBottom: '18px' }}>
          <div style={{ width: `${((step + 1) / 5) * 100}%`, background: 'linear-gradient(90deg, var(--lime), var(--lime-deep))' }} />
        </div>

        <div className="card" style={{ padding: '30px' }}>
          {step === 0 && (
            <div>
              <h3>🏠 Your profile</h3>
              <div className="card-lime" style={{ padding: '20px', margin: '14px 0', borderRadius: '18px' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  {[
                    { label: 'Name', value: user?.name || user?.username },
                    { label: 'Clinic', value: user?.clinic || 'Not assigned' },
                    { label: 'Professional Code', value: user?.professional_code || '—' },
                    { label: 'Specialisation', value: user?.occupation || '—' },
                    { label: 'Username', value: user?.username },
                    { label: 'Role', value: 'Psychologist' },
                  ].map(f => (
                    <div key={f.label}>
                      <div style={{ fontSize: '0.65rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.06em', opacity: 0.65 }}>{f.label}</div>
                      <div style={{ fontSize: '0.95rem', fontWeight: 700, marginTop: '2px' }}>{f.value}</div>
                    </div>
                  ))}
                </div>
              </div>
              <p style={{ color: 'var(--muted)', fontSize: '0.8rem', marginBottom: '12px' }}>
                Monitor your clients' wellness, review AI-powered journal insights, manage bookings, and receive instant crisis alerts.
              </p>
              <button className="btn-primary btn-full" onClick={() => advance(1)}>Next step →</button>
            </div>
          )}

          {step === 1 && (
            <div>
              <h3>📞 Your contact email</h3>
              <p style={{ color: 'var(--muted)', fontSize: '0.82rem', marginBottom: '12px' }}>
                Crisis alerts are sent to this email. Use the one you check most often.
              </p>
              <input
                type="email"
                value={contactInfo} onChange={e => { setContactInfo(e.target.value); if (contactError) setContactError('') }}
                placeholder="you@example.com"
                style={{ marginBottom: '8px' }}
              />
              {contactError && <div style={{ color: 'var(--danger)', fontSize: '0.75rem', marginBottom: '12px', fontWeight: 600 }}>{contactError}</div>}
              <div style={{ display: 'flex', gap: '8px' }}>
                <button className="btn-primary" onClick={handleSaveContact} disabled={saving} style={{ flex: 1 }}>
                  {saving ? 'Saving…' : 'Save & continue'}
                </button>
                <button onClick={() => advance(2)} style={{ flex: 1 }}>Skip</button>
              </div>
            </div>
          )}

          {step === 2 && (
            <div>
              <h3>👥 Trusted contact (crisis alerts)</h3>
              <p style={{ color: 'var(--muted)', fontSize: '0.82rem', marginBottom: '12px' }}>
                If you trigger a self-crisis alert and cannot be reached, this trusted contact is notified.
              </p>
              <input
                type="email"
                value={trustedContact} onChange={e => { setTrustedContact(e.target.value); if (tcError) setTcError('') }}
                placeholder="trusted-colleague@example.com"
                style={{ marginBottom: '8px' }}
              />
              {tcError && <div style={{ color: 'var(--danger)', fontSize: '0.75rem', marginBottom: '12px', fontWeight: 600 }}>{tcError}</div>}
              <div style={{ display: 'flex', gap: '8px' }}>
                <button className="btn-primary" onClick={handleSaveTrusted} disabled={saving} style={{ flex: 1 }}>
                  {saving ? 'Saving…' : 'Save & continue'}
                </button>
                <button onClick={() => advance(3)} style={{ flex: 1 }}>Skip</button>
              </div>
            </div>
          )}

          {step === 3 && (
            <div>
              <h3>🔮 Quick tips</h3>
              <div className="space-y-3" style={{ margin: '14px 0' }}>
                {[
                  { emoji: '💬', title: 'AI journal summaries', desc: 'Client journals are summarized into clinical notes automatically. Review them in Journal & Wellness.' },
                  { emoji: '⚠️', title: 'Crisis alerts', desc: 'Elevated vitals or high-risk entries trigger instant alerts. Acknowledge and escalate from any screen.' },
                  { emoji: '📅', title: 'Availability & bookings', desc: 'Open dates in the Bookings tab — clients book based on their assigned psychologist.' },
                  { emoji: '🤖', title: 'AI agents', desc: 'Draft follow-ups, suggest slots, and generate pre-session briefs with one click.' },
                ].map((tip, i) => (
                  <div key={i} style={{ display: 'flex', gap: '12px' }}>
                    <span style={{ fontSize: '1.2rem' }}>{tip.emoji}</span>
                    <div>
                      <div style={{ fontWeight: 700, fontSize: '0.85rem' }}>{tip.title}</div>
                      <div style={{ color: 'var(--muted)', fontSize: '0.75rem', lineHeight: 1.5 }}>{tip.desc}</div>
                    </div>
                  </div>
                ))}
              </div>
              <button className="btn-primary btn-full" onClick={() => advance(4)}>Finish →</button>
            </div>
          )}

          {step >= 4 && (
            <div className="card-lime" style={{ borderRadius: '20px', padding: '32px', textAlign: 'center' }}>
              <div style={{ fontSize: '3rem', marginBottom: '8px' }}>✅</div>
              <div style={{ fontSize: '1.5rem', fontWeight: 800 }}>You're all set!</div>
              <div style={{ fontSize: '0.85rem', marginTop: '8px', lineHeight: 1.6, opacity: 0.8 }}>
                Your workspace is ready. Manage clients, review journals, set availability, and respond to alerts.
              </div>
              <ConsentUpload user={user} />
              <button className="btn-primary btn-full" onClick={finish} style={{ marginTop: '20px', padding: '12px', fontSize: '0.95rem' }}>
                🚀 Open triage
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function ConsentUpload({ user }: { user: any }) {
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploaded, setUploaded] = useState('')

  async function handleUpload() {
    if (!file) return
    setUploading(true)
    try {
      const data = await api.uploadConsentForm(file)
      setUploaded(data?.file_path || 'Uploaded')
      setFile(null)
    } catch {}
    setUploading(false)
  }

  return (
    <div style={{ marginTop: '16px', padding: '13px', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '14px', textAlign: 'left' }}>
      <div style={{ color: 'var(--secondary)', fontSize: '0.8rem', fontWeight: 700, marginBottom: '8px' }}>📄 Consent form (optional)</div>
      {uploaded ? (
        <div style={{ color: 'var(--ok)', fontSize: '0.8rem', fontWeight: 600 }}>✅ Consent form uploaded. <button onClick={() => setUploaded('')} className="btn-ghost" style={{ fontSize: '0.72rem', color: 'var(--accent)', textDecoration: 'underline' }}>Re-upload</button></div>
      ) : (
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <input type="file" onChange={e => setFile(e.target.files?.[0] || null)} accept=".pdf,.jpg,.png"
            style={{ fontSize: '0.72rem', color: 'var(--secondary)', flex: 1 }} />
          <button onClick={handleUpload} disabled={!file || uploading} className={file ? 'btn-lime' : ''} style={{ padding: '7px 16px', fontSize: '0.75rem' }}>
            {uploading ? 'Uploading…' : 'Upload'}
          </button>
        </div>
      )}
    </div>
  )
}
