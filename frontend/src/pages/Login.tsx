import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { login, getUser } from '../stores/auth'

/* Fixed palette for the auth screen — pinned dark so it looks identical in both app themes */
const LIME = '#D7F65B'
const LIME_BRIGHT = '#CDF23E'
const INK = '#131512'
const PANEL_LIGHT = '#F4F5F0'
const PANEL_DARK = '#171A15'
const FIELD_BG = 'rgba(255,255,255,0.045)'
const FIELD_BORDER = 'rgba(255,255,255,0.12)'
const TEXT_LIGHT = '#F4F6EF'
const TEXT_MUTED_DARK = '#8B9184'
const TEXT_LABEL = '#A6AC9D'

export default function Login() {
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  function redirectAfterLogin() {
    const u = getUser()
    if (!u) { navigate('/dashboard'); return }
    const step = u.onboarding_step ?? 0
    if (step >= 99) {
      navigate(u.role === 'psychologist' ? '/triage' : '/dashboard')
      return
    }
    if (u.role === 'psychologist') { navigate('/psych-onboarding'); return }
    navigate('/onboarding')
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(username, password)
      redirectAfterLogin()
    } catch (err: any) {
      setError(err.message || 'Invalid credentials')
    } finally {
      setLoading(false)
    }
  }

  async function quickLogin(u: string, p: string) {
    setUsername(u)
    setPassword(p)
    setError('')
    setLoading(true)
    try {
      await login(u, p)
      redirectAfterLogin()
    } catch (err: any) {
      setError(err.message || 'Invalid credentials')
    } finally {
      setLoading(false)
    }
  }

  const demoAccounts = [
    { emoji: '🛡', label: 'Admin', creds: 'admin / password123', u: 'admin', p: 'password123' },
    { emoji: '🧑‍⚕️', label: 'Psychologist', creds: 'cel / 1234', u: 'cel', p: '1234' },
    { emoji: '🧑‍⚕️', label: 'Psychologist 2', creds: 'marcus / 4321', u: 'marcus', p: '4321' },
    { emoji: '🧑', label: 'Teen client', creds: 'maya_k / sentinel123', u: 'maya_k', p: 'sentinel123' },
  ]

  return (
    <div className="min-h-screen flex items-center justify-center" style={{ padding: '24px', background: '#0C0E0A' }}>
      {/* decorative lime glow blobs */}
      <div className="login-blob login-blob-1" style={{
        position: 'fixed', top: '-140px', right: '-140px', width: '460px', height: '460px',
        borderRadius: '999px', background: 'radial-gradient(circle, rgba(215,246,91,0.5) 0%, transparent 70%)',
        pointerEvents: 'none',
      }} />
      <div className="login-blob login-blob-2" style={{
        position: 'fixed', bottom: '-180px', left: '-160px', width: '520px', height: '520px',
        borderRadius: '999px', background: 'radial-gradient(circle, rgba(184,224,48,0.28) 0%, transparent 70%)',
        pointerEvents: 'none',
      }} />

      <div className="login-grid" style={{
        width: '100%', maxWidth: '980px', display: 'grid', gridTemplateColumns: '1fr 1fr',
        borderRadius: '28px', overflow: 'hidden', position: 'relative', zIndex: 1,
        boxShadow: '0 30px 80px rgba(0,0,0,0.55)',
      }}>
        {/* ── Left: brand panel (light) ── */}
        <div style={{
          background: PANEL_LIGHT, color: INK, padding: '42px 40px',
          display: 'flex', flexDirection: 'column', justifyContent: 'space-between', minHeight: '560px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              width: 42, height: 42, borderRadius: 999, background: LIME, color: INK,
              display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.25rem', fontWeight: 800,
            }}>✳</div>
            <span style={{ fontWeight: 800, fontSize: '1.12rem', letterSpacing: '-0.02em' }}>Sentinel</span>
          </div>

          <div>
            <h1 className="login-headline" style={{
              margin: 0, fontSize: 'clamp(2rem, 3.4vw, 2.55rem)', fontWeight: 800,
              textTransform: 'uppercase', lineHeight: 1.42, letterSpacing: '-0.01em', color: INK,
              perspective: '600px',
            }}>
              {['CARE THAT', 'NEVER', 'BLINKS.'].map(line => (
                <div key={line}>
                  <span style={{
                    background: LIME, padding: '2px 12px 5px', borderRadius: '2px',
                    boxDecorationBreak: 'clone', WebkitBoxDecorationBreak: 'clone',
                  }}>{line}</span>
                </div>
              ))}
            </h1>
            <p style={{ color: '#6B7067', fontSize: '0.88rem', marginTop: '20px', lineHeight: 1.65, maxWidth: '34ch' }}>
              Continuous psychophysiological triage — journals, ring vitals and crisis escalation in one calm place.
            </p>
          </div>

          <div style={{ display: 'flex', gap: '26px', flexWrap: 'wrap' }}>
            {['Real-time ring vitals', 'AI journal analysis', 'Crisis escalation'].map(t => (
              <span key={t} style={{ fontSize: '0.72rem', fontWeight: 700, color: '#2A2D28' }}>{t}</span>
            ))}
          </div>
        </div>

        {/* ── Right: form panel (dark) ── */}
        <form onSubmit={handleSubmit} style={{
          background: PANEL_DARK, padding: '42px 40px', display: 'flex', flexDirection: 'column',
          gap: '13px', justifyContent: 'center',
        }}>
          <div>
            <h2 style={{ margin: 0, fontSize: '1.65rem', color: TEXT_LIGHT, letterSpacing: '-0.01em' }}>Welcome back</h2>
            <p style={{ color: TEXT_MUTED_DARK, fontSize: '0.83rem', marginTop: '4px' }}>Sign in to your Sentinel workspace</p>
          </div>

          {error && (
            <div style={{
              background: 'rgba(214,69,58,0.14)', border: '1px solid rgba(214,69,58,0.35)',
              color: '#FFB4AD', fontSize: '0.8125rem', padding: '9px 13px', borderRadius: '12px', fontWeight: 600,
            }}>
              {error}
            </div>
          )}

          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: TEXT_LABEL, marginBottom: '6px' }}>Username</label>
            <input className="login-input" placeholder="your username" value={username} onChange={e => setUsername(e.target.value)} autoFocus />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: TEXT_LABEL, marginBottom: '6px' }}>Password</label>
            <div style={{ position: 'relative' }}>
              <input className="login-input" type={showPw ? 'text' : 'password'} placeholder="••••••••" value={password} onChange={e => setPassword(e.target.value)} style={{ paddingRight: '64px' }} />
              <button type="button" onClick={() => setShowPw(!showPw)} className="login-show">
                {showPw ? 'HIDE' : 'SHOW'}
              </button>
            </div>
          </div>

          <button type="submit" disabled={loading} className="login-submit">
            {loading ? 'Signing in…' : 'Sign in'}
          </button>

          <div style={{ textAlign: 'center', fontSize: '0.8rem', color: TEXT_MUTED_DARK }}>
            New here? <Link to="/register" style={{ fontWeight: 700, color: LIME_BRIGHT }}>Create an account</Link>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: '#6B7067', fontSize: '0.65rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.12em', marginTop: '2px' }}>
            <span style={{ flex: 1, height: 1, background: 'rgba(255,255,255,0.09)' }} /> demo accounts <span style={{ flex: 1, height: 1, background: 'rgba(255,255,255,0.09)' }} />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
            {demoAccounts.map(a => (
              <button key={a.u} type="button" className="demo-pill" onClick={() => quickLogin(a.u, a.p)}>
                <span style={{ fontWeight: 800, fontSize: '0.8rem', color: TEXT_LIGHT }}>{a.emoji} {a.label}</span>
                <span style={{ fontSize: '0.64rem', color: TEXT_MUTED_DARK }}>{a.creds}</span>
              </button>
            ))}
          </div>
        </form>
      </div>

      <style>{`
        .login-input {
          width: 100%;
          background: ${FIELD_BG};
          border: 1px solid ${FIELD_BORDER};
          border-radius: 12px;
          padding: 11px 14px;
          color: ${TEXT_LIGHT};
          font-size: 0.9rem;
          outline: none;
          transition: border-color .15s ease, background .15s ease;
        }
        .login-input:focus { border-color: rgba(215,246,91,0.55); background: rgba(255,255,255,0.07); }
        .login-input::placeholder { color: #70766B; }
        .login-show {
          position: absolute; right: 10px; top: 50%; transform: translateY(-50%);
          background: none !important; border: none !important; color: ${TEXT_LABEL};
          cursor: pointer; font-size: 0.7rem; font-weight: 700; padding: 6px; letter-spacing: 0.04em;
          transition: color .15s ease;
        }
        .login-show:hover { color: ${TEXT_LIGHT}; }
        .login-submit {
          width: 100%; background: ${LIME}; color: ${INK}; border: none; border-radius: 999px;
          padding: 13px; font-weight: 800; font-size: 0.95rem; cursor: pointer; margin-top: 4px;
          box-shadow: 0 6px 24px rgba(215,246,91,0.22);
          transition: transform .12s ease, background .15s ease, box-shadow .15s ease;
        }
        .login-submit:hover { background: ${LIME_BRIGHT}; transform: translateY(-1px); box-shadow: 0 8px 28px rgba(215,246,91,0.3); }
        .login-submit:disabled { opacity: 0.6; cursor: default; transform: none; }
        .demo-pill {
          display: flex; flex-direction: column; align-items: center; gap: 2px;
          background: rgba(255,255,255,0.03); border: 1px solid ${FIELD_BORDER}; border-radius: 999px;
          padding: 10px 12px; cursor: pointer; transition: border-color .18s ease, background .18s ease;
        }
        .demo-pill:hover { border-color: rgba(215,246,91,0.5); background: rgba(215,246,91,0.06); }
        @media (max-width: 860px) {
          .login-grid { grid-template-columns: 1fr !important; }
          .login-grid > div:first-child { min-height: auto !important; padding: 32px 28px !important; gap: 22px; }
          .login-grid > form { padding: 32px 28px !important; }
        }
      `}</style>
    </div>
  )
}
