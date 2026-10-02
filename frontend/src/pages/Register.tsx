import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { api } from '../api/client'
import CustomSelect from '../components/CustomSelect'
import { COUNTRIES } from '../constants'

const CLINIC_CODES = ['SENTINEL-01', 'SENTINEL-02', 'SENTINEL-03', 'SENTINEL-04', 'SENTINEL-05']
const PROFESSIONAL_CODE_CLINICS: Record<string, string> = {
  'PSY-0001': 'SENTINEL-01',
  'PSY-0002': 'SENTINEL-02',
  'PSY-0003': 'SENTINEL-03',
  'PSY-0004': 'SENTINEL-04',
  'PSY-0005': 'SENTINEL-05',
}

const PASSWORD_RULES: { label: string; test: (pw: string) => boolean }[] = [
  { label: 'At least 6 characters', test: pw => pw.length >= 6 },
  { label: 'An uppercase letter', test: pw => /[A-Z]/.test(pw) },
  { label: 'A lowercase letter', test: pw => /[a-z]/.test(pw) },
  { label: 'A number', test: pw => /\d/.test(pw) },
  { label: 'A special character', test: pw => /[!@#$%^&*(),.?":{}|<>]/.test(pw) },
]
const COMMON_PASSWORDS = ['password', '123456', '654321', 'qwerty', 'abc123', 'letmein', 'admin1', 'welcome', 'monkey', 'dragon', 'login1', 'pass123', 'iloveyou']

function todayLocalISO(): string {
  const d = new Date()
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10)
}

export default function Register() {
  const navigate = useNavigate()
  const [form, setForm] = useState({ username: '', password: '', confirmPassword: '', name: '', dob: '', occupation: '', role: 'patient', clinic_code: '', professional_code: '', assigned_psych: '', country: '', email: '', invite_code: '', license_number: '' })
  const [psychologists, setPsychologists] = useState<any[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [showPw, setShowPw] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  useEffect(() => {
    api.getAvailablePsychs().then(d => setPsychologists(d || [])).catch(() => {})
  }, [])

  const psychsForClinic = form.clinic_code
    ? psychologists.filter((p: any) => p.clinic === form.clinic_code)
    : psychologists

  function passwordErrors(pw: string): string[] {
    const errs: string[] = []
    for (const r of PASSWORD_RULES) if (!r.test(pw)) errs.push(r.label.toLowerCase())
    if (COMMON_PASSWORDS.includes(pw.toLowerCase().trim())) errs.push('not a common/easy password')
    if (pw && /^(.)\1+$/.test(pw)) errs.push('not a single repeated character')
    return errs
  }

  function fieldErrors(): Record<string, string> {
    const errs: Record<string, string> = {}
    const u = form.username.trim()
    if (!u) errs.username = 'Username is required'
    else if (u.length < 3) errs.username = 'Username must be at least 3 characters'
    else if (!/^[a-zA-Z0-9_.]+$/.test(u)) errs.username = 'Only letters, numbers, dots and underscores allowed'
    const n = form.name.trim()
    if (!n) errs.name = 'Full name is required'
    else if (n.length < 2) errs.name = 'Name must be at least 2 characters'
    else if (!/[A-Za-z]/.test(n)) errs.name = 'That is not a real name — it contains no letters'
    const dob = form.dob || ''
    if (!dob) errs.dob = 'Date of birth is required'
    else {
      const d = new Date(dob + 'T00:00:00')
      const today = new Date()
      const min = new Date('1900-01-01T00:00:00')
      if (isNaN(d.getTime()) || d.getTime() > today.getTime()) errs.dob = 'Date of birth cannot be in the future'
      else if (d.getTime() < min.getTime()) errs.dob = 'Date of birth seems too far in the past'
    }
    if (!form.occupation.trim()) errs.occupation = form.role === 'psychologist' ? 'Specialisation is required' : 'Occupation is required'
    if (!form.country) errs.country = 'Select your country'
    if (form.email.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) errs.email = 'Enter a valid email address'
    if (form.role === 'psychologist') {
      if (!form.license_number.trim()) errs.license_number = 'Your license / registration number is required'
      else if (form.license_number.trim().length < 4) errs.license_number = 'That license number looks too short'
      if (!form.invite_code.trim()) errs.invite_code = 'Enter the invite code from your clinic admin'
    }
    if (form.role === 'patient' && !form.clinic_code) errs.clinic = 'Select your clinic'
    if (form.role === 'patient' && form.clinic_code && !form.assigned_psych) errs.psych = 'Choose your psychologist'
    return errs
  }

  function InlineError({ msg }: { msg?: string }) {
    if (!msg) return null
    return <div style={{ fontSize: '0.72rem', color: 'var(--danger)', marginTop: '4px', fontWeight: 600 }}>⚠ {msg}</div>
  }

  const errs = fieldErrors()

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSubmitted(true)
    setError('')
    const pwErrs = passwordErrors(form.password)
    if (pwErrs.length) { setError(`Password must contain ${pwErrs.join(', ')}`); return }
    if (form.password !== form.confirmPassword) { setError('Passwords do not match'); return }
    const fe = fieldErrors()
    const firstKey = Object.keys(fe)[0]
    if (firstKey) { setError(`Please fix: ${fe[firstKey]}`); return }
    setLoading(true)
    try {
      const isPsych = form.role === 'psychologist'
      const legacyClinic = isPsych ? PROFESSIONAL_CODE_CLINICS[form.professional_code.toUpperCase()] : undefined
      const derivedClinic = isPsych ? (legacyClinic || '') : form.clinic_code
      await api.register({
        username: form.username,
        password: form.password,
        name: form.name,
        role: form.role,
        clinic_code: derivedClinic,
        dob: form.dob,
        country: form.country,
        occupation: form.occupation,
        email: form.email.trim() || undefined,
        assigned_psych: form.assigned_psych || undefined,
        invite_code: isPsych ? form.invite_code.trim() || undefined : undefined,
        license_number: isPsych ? form.license_number.trim() : undefined,
        // legacy path still supported when no invite code is used
        professional_code: isPsych && !form.invite_code.trim() ? form.professional_code : undefined,
      })
      navigate('/login', { state: { justRegistered: form.username, email: form.email.trim() } })
    } catch (err: any) {
      setError(err.message || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center" style={{ padding: '24px', background: 'var(--bg)' }}>
      <div className="login-blob login-blob-1" style={{
        position: 'fixed', top: '-160px', left: '-160px', width: '460px', height: '460px',
        borderRadius: '999px', background: 'radial-gradient(circle, var(--lime) 0%, transparent 70%)',
        opacity: 0.4, pointerEvents: 'none',
      }} />
      <form onSubmit={handleSubmit} className="card login-grid" style={{ padding: '34px 32px', width: '100%', maxWidth: '560px', display: 'flex', flexDirection: 'column', gap: '12px', position: 'relative', zIndex: 1 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px' }}>
          <div style={{ width: 38, height: 38, borderRadius: 999, background: 'var(--ink)', color: 'var(--lime)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.05rem' }}>✳</div>
          <div>
            <h2 style={{ margin: 0, fontSize: '1.35rem' }}>Join Sentinel</h2>
            <div style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>Continuous care, starting today</div>
          </div>
        </div>

        {error && (
          <div style={{ background: 'var(--danger-soft)', border: '1px solid color-mix(in srgb, var(--danger) 30%, transparent)', color: 'var(--danger-deep)', fontSize: '0.8125rem', padding: '9px 13px', borderRadius: '12px', fontWeight: 600 }}>
            {error}
          </div>
        )}

        {/* Role selector */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
          {(['patient', 'psychologist'] as const).map(r => (
            <button
              key={r} type="button"
              onClick={() => setForm(f => ({ ...f, role: r, assigned_psych: '' }))}
              className={form.role === r ? 'btn-lime' : ''}
              style={{ padding: '12px', fontSize: '0.875rem', justifyContent: 'center', flexDirection: 'column', gap: '2px', borderRadius: '16px' }}
            >
              <span style={{ fontWeight: 800 }}>{r === 'patient' ? '🧑 I\'m a client' : '🧑‍⚕️ I\'m a psychologist'}</span>
              <span style={{ fontSize: '0.62rem', fontWeight: 500, opacity: 0.75 }}>
                {r === 'patient' ? 'Track & journal with care' : 'Manage a caseload'}
              </span>
            </button>
          ))}
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
          <div>
            <label>Full name</label>
            <input placeholder="Jamie Rivera" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} style={{ borderColor: submitted && errs.name ? 'var(--danger)' : undefined }} />
            <InlineError msg={(submitted || form.name.trim().length > 0) ? errs.name : undefined} />
          </div>
          <div>
            <label>Username</label>
            <input placeholder="jamie.r" value={form.username} onChange={e => setForm(f => ({ ...f, username: e.target.value }))} style={{ borderColor: submitted && errs.username ? 'var(--danger)' : undefined }} />
            <InlineError msg={(submitted || form.username.trim().length > 0) ? errs.username : undefined} />
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
          <div>
            <label>Date of birth</label>
            <input type="date" max={todayLocalISO()} min="1900-01-01" value={form.dob} onChange={e => setForm(f => ({ ...f, dob: e.target.value }))} style={{ borderColor: (submitted || form.dob) && errs.dob ? 'var(--danger)' : undefined }} />
            <InlineError msg={(submitted || form.dob) ? errs.dob : undefined} />
          </div>
          <div>
            <label>{form.role === 'psychologist' ? 'Specialisation' : 'Occupation / school'}</label>
            <input placeholder={form.role === 'psychologist' ? 'e.g. Adolescent anxiety' : 'e.g. Student, Lincoln High'} value={form.occupation} onChange={e => setForm(f => ({ ...f, occupation: e.target.value }))} style={{ borderColor: submitted && errs.occupation ? 'var(--danger)' : undefined }} />
            <InlineError msg={(submitted || form.occupation.trim()) ? errs.occupation : undefined} />
          </div>
        </div>

        <div>
          <label>Email <span style={{ color: 'var(--faint)', fontWeight: 500, textTransform: 'none', letterSpacing: 0 }}>(optional — used for verification &amp; alerts)</span></label>
          <input type="email" placeholder="you@example.com" value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))} style={{ borderColor: (submitted || form.email) && errs.email ? 'var(--danger)' : undefined }} />
          <InlineError msg={(submitted || form.email) ? errs.email : undefined} />
        </div>

        <div>
          <label>Country</label>
          <CustomSelect
            value={form.country}
            onChange={v => setForm(f => ({ ...f, country: v }))}
            searchable
            placeholder="Select your country…"
            invalid={!!((submitted || form.country) && errs.country)}
            options={[{ value: '', label: 'Select your country…' }, ...COUNTRIES.map(c => ({ value: c, label: c }))]}
          />
          <InlineError msg={(submitted || form.country) ? errs.country : undefined} />
        </div>

        <div>
          <label>Password</label>
          <div style={{ position: 'relative' }}>
            <input type={showPw ? 'text' : 'password'} placeholder="Create a strong password" value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))} style={{ paddingRight: '64px' }} />
            <button type="button" onClick={() => setShowPw(!showPw)} style={{ position: 'absolute', right: '8px', top: '50%', transform: 'translateY(-50%)', background: 'none !important', border: 'none !important', color: 'var(--muted)', cursor: 'pointer', fontSize: '0.72rem', fontWeight: 700, padding: '6px' }}>
              {showPw ? 'HIDE' : 'SHOW'}
            </button>
          </div>
          {form.password.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '6px' }}>
              {PASSWORD_RULES.map(r => {
                const ok = r.test(form.password)
                return (
                  <span key={r.label} style={{
                    fontSize: '0.62rem', fontWeight: 600, padding: '3px 8px', borderRadius: 999,
                    background: ok ? 'var(--ok-soft)' : 'var(--surface-soft-2)',
                    color: ok ? 'var(--ok)' : 'var(--faint)',
                    border: `1px solid ${ok ? 'color-mix(in srgb, var(--ok) 30%, transparent)' : 'var(--border)'}`,
                  }}>
                    {ok ? '✓' : '○'} {r.label}
                  </span>
                )
              })}
            </div>
          )}
        </div>

        <div>
          <label>Confirm password</label>
          <input type={showPw ? 'text' : 'password'} placeholder="Repeat it" value={form.confirmPassword} onChange={e => setForm(f => ({ ...f, confirmPassword: e.target.value }))} style={{ borderColor: submitted && form.confirmPassword && form.password !== form.confirmPassword ? 'var(--danger)' : undefined }} />
          {form.confirmPassword && form.password !== form.confirmPassword && (
            <InlineError msg="Passwords do not match" />
          )}
        </div>

        {form.role === 'psychologist' && (
          <div className="card-sm" style={{ background: 'var(--accent-soft)', borderColor: 'color-mix(in srgb, var(--accent) 30%, transparent)' }}>
            <label style={{ color: 'var(--accent)' }}>🎟 Invite code</label>
            <input
              placeholder="e.g. INV-XXXXXXXX"
              value={form.invite_code}
              onChange={e => setForm(f => ({ ...f, invite_code: e.target.value.trim().toUpperCase() }))}
            />
            <div style={{ fontSize: '0.7rem', color: 'var(--muted)', marginTop: '4px' }}>
              Ask your clinic administrator for an invite code — each code is tied to one clinic.
            </div>
            <InlineError msg={submitted && errs.invite_code ? errs.invite_code : undefined} />

            <label style={{ color: 'var(--accent)', marginTop: '10px' }}>🪪 Medical license number</label>
            <input
              placeholder="Your official registration / license no."
              value={form.license_number}
              onChange={e => setForm(f => ({ ...f, license_number: e.target.value.trim() }))}
            />
            <InlineError msg={(submitted || form.license_number) ? errs.license_number : undefined} />

            <div style={{ fontSize: '0.68rem', color: 'var(--muted)', marginTop: '10px', fontWeight: 600 }}>Legacy professional code (demo only)</div>
            <input
              placeholder="e.g. PSY-0001 (optional)"
              value={form.professional_code}
              onChange={e => setForm(f => ({ ...f, professional_code: e.target.value.trim().toUpperCase() }))}
            />
            {PROFESSIONAL_CODE_CLINICS[form.professional_code] && (
              <div style={{ fontSize: '0.75rem', color: 'var(--ok)', fontWeight: 700, marginTop: '6px' }}>✓ Clinic: {PROFESSIONAL_CODE_CLINICS[form.professional_code]}</div>
            )}
          </div>
        )}

        {form.role === 'patient' && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
            <div>
              <label>Clinic</label>
              <CustomSelect
                value={form.clinic_code}
                onChange={v => setForm(f => ({ ...f, clinic_code: v, assigned_psych: '' }))}
                placeholder="Select clinic…"
                invalid={submitted && !!errs.clinic}
                options={[{ value: '', label: 'Select clinic…' }, ...CLINIC_CODES.map(code => ({ value: code, label: code }))]}
              />
              <InlineError msg={submitted ? errs.clinic : undefined} />
            </div>
            <div>
              <label>Psychologist</label>
              <CustomSelect
                value={form.assigned_psych}
                onChange={v => setForm(f => ({ ...f, assigned_psych: v }))}
                disabled={!form.clinic_code || psychsForClinic.length === 0}
                placeholder={!form.clinic_code ? 'Pick clinic first…' : psychsForClinic.length === 0 ? 'None available yet' : 'Choose…'}
                invalid={submitted && !!errs.psych}
                options={psychsForClinic.map((p: any) => ({ value: p.username || p, label: `${p.name || p}${p.specialisation ? ` — ${p.specialisation}` : ''}` }))}
              />
              <InlineError msg={submitted ? errs.psych : undefined} />
            </div>
          </div>
        )}

        <button type="submit" disabled={loading} className="btn-primary" style={{ width: '100%', padding: '12px', fontSize: '0.9rem', marginTop: '4px' }}>
          {loading ? 'Creating account…' : 'Create account'}
        </button>

        <div style={{ fontSize: '0.8rem', color: 'var(--muted)', textAlign: 'center' }}>
          Already have an account? <Link to="/login" style={{ fontWeight: 700 }}>Sign in</Link>
        </div>
      </form>
    </div>
  )
}
