import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getUser } from '../stores/auth'
import { api } from '../api/client'
import { EMAIL_RE } from '../constants'

const STEPS = [
  { emoji: '🏠', label: 'About You' },
  { emoji: '📝', label: 'First Entry' },
  { emoji: '🛡️', label: 'Emergency' },
  { emoji: '📱', label: 'Contact' },
]

export default function OnboardingPage() {
  const navigate = useNavigate()
  const user = getUser()
  const [step, setStep] = useState(0)
  const [journal, setJournal] = useState('')
  const [trustedContact, setTrustedContact] = useState('')
  const [contactInfo, setContactInfo] = useState('')
  const [tcError, setTcError] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    api.getMe().then((d: any) => {
      if (d.onboarding_step >= 99) { navigate('/dashboard'); return }
      setStep(d.onboarding_step || 0)
      setTrustedContact(d.trusted_contact || '')
      setContactInfo(d.contact_info || '')
    }).catch(() => {})
  }, [])

  async function goTo(s: number) {
    if (s < 0 || s > 4) return
    if (s > step) {
      try { await api.updateOnboarding(s) } catch {}
    }
    setStep(s)
  }

  async function handleJournal() {
    if (!journal.trim()) return
    setSaving(true)
    try { await api.createJournal(journal.trim()) } catch {}
    setSaving(false)
    goTo(2)
  }

  async function handleContact() {
    try {
      await api.updateContact({ contact_info: contactInfo, trusted_contact: trustedContact })
    } catch {}
    goTo(4)
  }

  async function saveTrustedAndNext() {
    const tc = trustedContact.trim()
    if (tc && !EMAIL_RE.test(tc)) {
      setTcError('Enter a valid email address — crisis alerts are sent there.')
      return
    }
    setTcError('')
    if (tc) {
      try { await api.updateContact({ contact_info: contactInfo, trusted_contact: tc }) } catch {}
    }
    goTo(3)
  }

  async function finish() {
    try { await api.updateOnboarding(99) } catch {}
    navigate('/dashboard')
  }

  return (
    <div className="min-h-screen flex items-center justify-center" style={{ padding: '28px', background: 'var(--bg)' }}>
      <div style={{
        position: 'fixed', top: '-140px', right: '-140px', width: '420px', height: '420px',
        borderRadius: '999px', background: 'radial-gradient(circle, var(--lime) 0%, transparent 70%)',
        opacity: 0.45, pointerEvents: 'none',
      }} />
      <div style={{ width: '100%', maxWidth: '600px', position: 'relative', zIndex: 1 }}>
        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
            <div style={{ width: 36, height: 36, borderRadius: 999, background: 'var(--ink)', color: 'var(--lime)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1rem' }}>✳</div>
            <span style={{ fontWeight: 800, fontSize: '1.1rem' }}>Sentinel</span>
          </div>
          <h1 className="page-title" style={{ fontSize: 'clamp(1.8rem, 4vw, 2.4rem)' }}>Welcome, {user?.name?.split(' ')[0]}</h1>
          <div className="page-sub">Four quick steps and you're in</div>
        </div>

        {/* Steps */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px', marginBottom: '16px' }}>
          {STEPS.map((s, i) => {
            const done = i < step
            const active = i === step
            return (
              <div
                key={i}
                onClick={() => i <= step && goTo(i)}
                className={done ? 'card-sm step-done' : active ? 'card-sm step-active' : 'card-sm step-pending'}
                style={{
                  textAlign: 'center', padding: '12px 6px', transition: 'all 0.3s',
                  cursor: i <= step ? 'pointer' : 'default',
                  opacity: i > step ? 0.5 : 1, margin: 0,
                }}
              >
                <div style={{ fontSize: '1.3rem' }}>{done ? '✅' : s.emoji}</div>
                <div style={{ color: done ? 'var(--ok)' : active ? 'var(--heading)' : 'var(--faint)', fontSize: '0.64rem', fontWeight: active || done ? 800 : 500, marginTop: '3px' }}>{s.label}</div>
              </div>
            )
          })}
        </div>

        <div className="track" style={{ marginBottom: '18px' }}>
          <div style={{ width: `${((step + 1) / 4) * 100}%`, background: 'linear-gradient(90deg, var(--lime), var(--lime-deep))' }} />
        </div>

        <div className="card" style={{ padding: '30px', minHeight: '300px' }}>
          {step === 0 && (
            <div>
              <h3>🏠 About you</h3>
              <div className="card-lime" style={{ padding: '20px', margin: '14px 0', borderRadius: '18px' }}>
                <div style={{ fontSize: '0.65rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.08em', opacity: 0.7 }}>Your account</div>
                <div style={{ fontSize: '1.15rem', fontWeight: 800, marginTop: '4px' }}>{user?.name || user?.username}</div>
                <div style={{ fontSize: '0.78rem', marginTop: '8px', opacity: 0.8, lineHeight: 1.55 }}>
                  You're registered with Sentinel. Your psychologist will review your journals and vitals to support your well-being.
                </div>
              </div>
              <button className="btn-primary btn-full" onClick={() => goTo(1)}>Next step →</button>
            </div>
          )}

          {step === 1 && (
            <div>
              <h3>📝 Your first journal entry</h3>
              <p style={{ color: 'var(--muted)', fontSize: '0.82rem', marginBottom: '12px' }}>
                Write a few lines about how you're feeling. Your psychologist will see an AI summary.
              </p>
              <textarea
                value={journal} onChange={e => setJournal(e.target.value)}
                placeholder="How are you feeling right now?"
                rows={5}
                style={{ width: '100%', padding: '13px', fontSize: '0.875rem', resize: 'none', marginBottom: '12px', borderRadius: '14px' }}
              />
              <div style={{ display: 'flex', gap: '8px' }}>
                <button className="btn-primary" onClick={handleJournal} disabled={saving || !journal.trim()} style={{ flex: 1 }}>
                  {saving ? 'Saving…' : 'Save & continue'}
                </button>
                <button onClick={() => goTo(2)} style={{ flex: 1 }}>Skip for now</button>
              </div>
              <div style={{ marginTop: '8px' }}>
                <button className="btn-ghost" onClick={() => goTo(0)} style={{ fontSize: '0.75rem' }}>← Back</button>
              </div>
            </div>
          )}

          {step === 2 && (
            <div>
              <h3>🛡️ Emergency contact</h3>
              <p style={{ color: 'var(--muted)', fontSize: '0.82rem', marginBottom: '12px' }}>
                If you trigger a crisis alert, this trusted contact is notified at the 30-second mark. Use the email they check most often.
              </p>
              <input
                type="email"
                value={trustedContact} onChange={e => { setTrustedContact(e.target.value); if (tcError) setTcError('') }}
                placeholder="trusted person's email (e.g. mom@example.com)"
                style={{ marginBottom: '8px' }}
              />
              {tcError && <div style={{ color: 'var(--danger)', fontSize: '0.75rem', marginBottom: '12px', fontWeight: 600 }}>{tcError}</div>}
              <div style={{ display: 'flex', gap: '8px' }}>
                <button className="btn-primary" onClick={saveTrustedAndNext} style={{ flex: 1 }}>Save →</button>
                <button onClick={() => goTo(3)} style={{ flex: 1 }}>Skip</button>
              </div>
              <div style={{ marginTop: '8px' }}>
                <button className="btn-ghost" onClick={() => goTo(1)} style={{ fontSize: '0.75rem' }}>← Back</button>
              </div>
            </div>
          )}

          {step === 3 && (
            <div>
              <h3>📱 Contact preference</h3>
              <p style={{ color: 'var(--muted)', fontSize: '0.82rem', marginBottom: '12px' }}>
                How should your psychologist reach you?
              </p>
              <input
                value={contactInfo} onChange={e => setContactInfo(e.target.value)}
                placeholder="Mobile number or email"
                style={{ marginBottom: '12px' }}
              />
              <div style={{ display: 'flex', gap: '8px' }}>
                <button className="btn-primary" onClick={handleContact} style={{ flex: 1 }}>Save →</button>
                <button onClick={() => goTo(4)} style={{ flex: 1 }}>Skip</button>
              </div>
              <div style={{ marginTop: '8px' }}>
                <button className="btn-ghost" onClick={() => goTo(2)} style={{ fontSize: '0.75rem' }}>← Back</button>
              </div>
            </div>
          )}

          {step >= 4 && (
            <div className="card-lime" style={{ borderRadius: '20px', padding: '34px', textAlign: 'center' }}>
              <div style={{ fontSize: '3rem', marginBottom: '8px' }}>✅</div>
              <div style={{ fontSize: '1.5rem', fontWeight: 800 }}>You're all set!</div>
              <div style={{ fontSize: '0.85rem', marginTop: '8px', lineHeight: 1.6, opacity: 0.8 }}>
                Your dashboard is ready. Track your wellness, write journal entries, manage bookings, and more.
              </div>
              <div style={{ display: 'flex', gap: '8px', marginTop: '20px' }}>
                <button onClick={() => goTo(3)} style={{ flex: 1, padding: '10px', background: 'rgba(0,0,0,0.08) !important', borderColor: 'transparent !important', color: 'var(--lime-ink) !important' }}>← Back</button>
                <button className="btn-primary" onClick={finish} style={{ flex: 2, padding: '12px', fontSize: '0.95rem' }}>🚀 Open dashboard</button>
              </div>
            </div>
          )}
        </div>

        <div style={{ textAlign: 'center', marginTop: '12px', color: 'var(--faint)', fontSize: '0.7rem' }}>
          Click any completed step above to go back
        </div>
      </div>
    </div>
  )
}
