import { useEffect, useState, useRef } from 'react'

const BASE = '/api'

const params = new URLSearchParams(window.location.search)
const LINK_PARAMS = `patient=${encodeURIComponent(params.get('patient') || '')}&exp=${encodeURIComponent(params.get('exp') || '')}&sig=${encodeURIComponent(params.get('sig') || '')}`

async function publicGet(path: string) {
  const sep = path.includes('?') ? '&' : '?'
  const res = await fetch(`${BASE}${path}${sep}${LINK_PARAMS}`)
  if (!res.ok) return null
  return res.json()
}

async function publicPost(path: string) {
  const sep = path.includes('?') ? '&' : '?'
  const res = await fetch(`${BASE}${path}${sep}${LINK_PARAMS}`, { method: 'POST' })
  if (!res.ok) return null
  return res.json()
}

const ADDRESSES: Record<string, string> = {
  'test_patient_1': '42 Lakeview Drive, Apt 7B, Portland, OR 97201',
  'test_patient_2': '815 Maple Street, House #3, Portland, OR 97202',
  'test_patient_3': '1200 Pine Avenue, Unit 12, Portland, OR 97203',
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg)', padding: '28px' }}>
      <div style={{ width: '100%', maxWidth: '540px' }}>{children}</div>
    </div>
  )
}

function CenterState({ icon, title, color, body }: { icon: string; title: string; color: string; body: string }) {
  return (
    <div className="card" style={{ padding: '44px 36px', textAlign: 'center' }}>
      <div style={{ fontSize: '3rem', marginBottom: '12px' }}>{icon}</div>
      <h1 style={{ color: `${color} !important`, fontSize: '1.5rem', marginBottom: '8px' }}>{title}</h1>
      <p style={{ color: 'var(--muted)', fontSize: '0.92rem', lineHeight: 1.6 }}>{body}</p>
      <p style={{ color: 'var(--faint)', fontSize: '0.78rem', marginTop: '18px', fontWeight: 700 }}>Sentinel — Crisis Response System</p>
    </div>
  )
}

export default function TrusteePortalPage() {
  const [state, setState] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [acknowledged, setAcknowledged] = useState(false)
  const [elapsed, setElapsed] = useState(0)
  const clickedRef = useRef(false)

  async function load() {
    const s = await publicGet('/crisis/public-state')
    setState(s)
    setLoading(false)
    if (s?.triggered_at) {
      const secs = Math.floor((Date.now() - new Date(s.triggered_at).getTime()) / 1000)
      setElapsed(secs)
    }
    if (s?.active && !s.trustee_clicked && !s.trustee_acknowledged && !clickedRef.current) {
      clickedRef.current = true
      publicPost('/crisis/public-trustee-clicked').catch(() => {})
    }
    if (s?.trustee_acknowledged) setAcknowledged(true)
  }

  useEffect(() => { load(); const iv = setInterval(load, 5000); return () => clearInterval(iv) }, [])

  useEffect(() => {
    if (!state?.active) return
    const iv = setInterval(() => setElapsed(e => e + 1), 1000)
    return () => clearInterval(iv)
  }, [state?.active])

  async function handleAcknowledge() {
    const res = await publicPost('/crisis/public-trustee-acknowledge')
    if (res) setAcknowledged(true)
  }

  if (loading) return (
    <Shell><CenterState icon="⏳" title="Loading…" color="var(--heading)" body="Checking the current status." /></Shell>
  )

  const linkInvalid = !params.get('sig') || !params.get('patient') || state === null

  if (linkInvalid) return (
    <Shell><CenterState icon="🔒" title="Invalid or expired link" color="var(--heading)" body="This safety link is invalid or has expired. Please request a fresh link from your loved one's care team." /></Shell>
  )

  if (!state?.active) return (
    <Shell><CenterState icon="🟢" title="Trusted Contact Portal" color="var(--ok)" body="No active crisis at this time." /></Shell>
  )

  if (state?.acknowledged) return (
    <Shell><CenterState icon="✅" title="Crisis resolved" color="var(--ok)" body="This crisis has been acknowledged by the clinical team. No further action needed." /></Shell>
  )

  if (state?.trustee_acknowledged) return (
    <Shell><CenterState icon="🚀" title="You've already responded" color="var(--ok)" body="Thank you! Your status has been recorded. Please proceed to check on your loved one." /></Shell>
  )

  const patient = state.patient || 'your loved one'
  const address = ADDRESSES[patient] || 'Address on file'
  const displayTime = elapsed >= 60 ? '60+' : String(elapsed)

  return (
    <Shell>
      <div className="card" style={{ padding: '34px 32px' }}>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', marginBottom: '18px' }}>
          <div style={{ width: 36, height: 36, borderRadius: 999, background: 'var(--ink)', color: 'var(--lime)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1rem' }}>✳</div>
          <span style={{ fontWeight: 800, fontSize: '1rem' }}>Sentinel · Trusted Contact</span>
        </div>

        <div className="card-lime" style={{ padding: '20px 22px', borderRadius: '18px', marginBottom: '16px' }}>
          <div style={{ fontSize: '0.68rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.08em', opacity: 0.7 }}>Active crisis alert</div>
          <div style={{ fontSize: '1.25rem', fontWeight: 800, margin: '4px 0' }}>
            {patient} triggered an alert {displayTime}s ago
          </div>
          <div style={{ fontSize: '0.8rem', opacity: 0.8 }}>Reaching out quickly matters. Thank you for being their person.</div>
        </div>

        <div className="card-sm" style={{ padding: '16px', marginBottom: '16px' }}>
          <div style={{ color: 'var(--muted)', fontSize: '0.72rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: '4px' }}>📍 Last known location</div>
          <div style={{ color: 'var(--heading)', fontSize: '1rem', fontWeight: 700 }}>{address}</div>
        </div>

        {!acknowledged ? (
          <>
            <button
              onClick={handleAcknowledge}
              className="btn-primary pulse-crisis"
              style={{ width: '100%', padding: '18px', fontSize: '1.1rem', fontWeight: 800 }}
            >
              ✅ Yes, I&apos;m on my way
            </button>
            <div style={{ textAlign: 'center', color: 'var(--faint)', fontSize: '0.7rem', marginTop: '10px' }}>
              Confirming marks you as responding — the clinical team sees it instantly.
            </div>
          </>
        ) : (
          <div style={{ background: 'var(--ok-soft)', border: '1px solid color-mix(in srgb, var(--ok) 30%, transparent)', borderRadius: '18px', padding: '24px', textAlign: 'center' }}>
            <div style={{ fontSize: '2.2rem', marginBottom: '8px' }}>🚀</div>
            <div style={{ color: 'var(--ok)', fontSize: '1.25rem', fontWeight: 800, marginBottom: '4px' }}>Thank you!</div>
            <div style={{ color: 'var(--muted)', fontSize: '0.875rem' }}>You are marked as <strong style={{ color: 'var(--ok)' }}>“On the Way”</strong>.</div>
            <div style={{ color: 'var(--faint)', fontSize: '0.75rem', marginTop: '8px' }}>Please proceed to check on {patient} as soon as possible.</div>
          </div>
        )}

        <p style={{ textAlign: 'center', color: 'var(--faint)', fontSize: '0.72rem', marginTop: '22px' }}>
          Sentinel — Crisis Response System
        </p>
      </div>
    </Shell>
  )
}
