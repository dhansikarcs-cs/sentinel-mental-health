import { useEffect, useState } from 'react'
import { getUser, fetchMe } from '../stores/auth'
import { api } from '../api/client'
import { EMAIL_RE, COUNTRIES, TIMEZONES } from '../constants'

const labelStyle: React.CSSProperties = {
  fontSize: '0.75rem', color: 'var(--secondary)', fontWeight: 500,
  marginBottom: '4px', display: 'block',
}
const inputStyle: React.CSSProperties = {
  width: '100%', padding: '10px 12px', fontSize: '0.875rem',
}

/**
 * Profile for BOTH roles. Name, clinic and occupation are editable now (they
 * used to be read-only); username and role stay fixed for safety. Every save
 * goes to the backend for the logged-in account only, then fetchMe() refreshes
 * the shell (avatar, greeting, triage lists) everywhere.
 */
export default function ProfilePage() {
  const user = getUser()
  const [name, setName] = useState(user?.name || '')
  const [clinic, setClinic] = useState(user?.clinic || '')
  const [occupation, setOccupation] = useState(user?.occupation || '')
  const [contact, setContact] = useState(user?.contact_info || '')
  const [trusted, setTrusted] = useState(user?.trusted_contact || '')
  const [country, setCountry] = useState(user?.country || '')
  const [timezone, setTimezone] = useState(user?.timezone || '')
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState('')
  const [ok, setOk] = useState(false)
  const [currentPw, setCurrentPw] = useState('')
  const [newPw, setNewPw] = useState('')
  const [confirmPw, setConfirmPw] = useState('')
  const [pwSaving, setPwSaving] = useState(false)
  const [pwMsg, setPwMsg] = useState('')
  const [pwOk, setPwOk] = useState(false)

  useEffect(() => {
    setName(user?.name || '')
    setClinic(user?.clinic || '')
    setOccupation(user?.occupation || '')
    setContact(user?.contact_info || '')
    setTrusted(user?.trusted_contact || '')
    setCountry(user?.country || '')
    setTimezone(user?.timezone || '')
  }, [user])

  const isPsych = user?.role === 'psychologist'

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    setMsg('')
    setOk(false)
    const tc = trusted.trim()
    const own = contact.trim()
    const trimmedName = name.trim()
    if (trimmedName.length < 2 || !/[A-Za-z]/.test(trimmedName)) {
      setMsg('Name must be at least 2 characters and contain a letter.')
      setSaving(false)
      return
    }
    if (tc && !EMAIL_RE.test(tc)) {
      setMsg('Trusted contact must be a valid email address (crisis alerts are sent there).')
      setSaving(false)
      return
    }
    if (isPsych && own && !EMAIL_RE.test(own)) {
      setMsg('Your contact must be a valid email address (crisis alerts are sent to you there).')
      setSaving(false)
      return
    }
    try {
      await api.updateProfile({ name: trimmedName, clinic: clinic.trim(), occupation: occupation.trim() })
      await api.updateContact({ contact_info: contact, trusted_contact: trusted })
      await api.updatePreferences({ country, timezone })
      await fetchMe()
      setOk(true)
      setMsg('Profile saved successfully.')
    } catch (err: any) {
      setMsg(err.message || 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  async function handlePassword(e: React.FormEvent) {
    e.preventDefault()
    setPwMsg('')
    setPwOk(false)
    if (!currentPw) { setPwMsg('Enter your current password.'); return }
    if (newPw.length < 6) { setPwMsg('New password must be at least 6 characters.'); return }
    if (newPw !== confirmPw) { setPwMsg('New passwords do not match.'); return }
    setPwSaving(true)
    try {
      await api.changePassword({ current_password: currentPw, new_password: newPw })
      setCurrentPw(''); setNewPw(''); setConfirmPw('')
      setPwOk(true)
      setPwMsg('Password updated. Use it the next time you sign in.')
    } catch (err: any) {
      setPwMsg(err.message || 'Failed to change password')
    } finally {
      setPwSaving(false)
    }
  }

  if (!user) return null

  const initials = (name || user.username || '?').split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase()

  return (
    <div className="space-y-6 animate-fade-in">
      <h1>👤 My Profile</h1>

      {/* Identity header — same lime/ink language as the improved shell */}
      <div className="card" style={{ padding: '18px 22px', display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }} data-tour="profile">
        <div className="avatar" style={{ width: 56, height: 56, minWidth: 56, fontSize: '1.2rem', background: 'var(--lime)', color: 'var(--lime-ink)' }}>
          {initials}
        </div>
        <div style={{ flex: 1, minWidth: '200px' }}>
          <div style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--heading)' }}>{name || user.name}</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--muted)', marginTop: '2px' }}>
            @{user.username} · <span className="badge-theme">{isPsych ? '🧑‍⚕️ Psychologist' : '🧑 Client'}</span>
          </div>
        </div>
        <span className="badge-theme">🏥 {clinic || '—'}</span>
      </div>

      <div className="card" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
        <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--heading)' }}>About you</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
            <div>
              <label style={labelStyle}>Display name</label>
              <input value={name} onChange={e => setName(e.target.value)} maxLength={100} placeholder="Your name" style={inputStyle} />
            </div>
            <div>
              <label style={labelStyle}>Clinic / organisation</label>
              <input value={clinic} onChange={e => setClinic(e.target.value)} maxLength={100} placeholder="Clinic or organisation" style={inputStyle} />
            </div>
          </div>
          <div>
            <label style={labelStyle}>Occupation / specialisation</label>
            <input value={occupation} onChange={e => setOccupation(e.target.value)} maxLength={100} placeholder="What you do" style={inputStyle} />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
            <div>
              <div className="metric-label">Username (account ID)</div>
              <div style={{ fontSize: '0.875rem', color: 'var(--heading)', marginTop: '2px' }}>{user.username}</div>
            </div>
            <div>
              <div className="metric-label">Role</div>
              <div style={{ fontSize: '0.875rem', color: 'var(--heading)', marginTop: '2px' }}>{user.role}</div>
            </div>
          </div>
          <div style={{ fontSize: '0.68rem', color: 'var(--muted)', lineHeight: 1.5 }}>
            Your username and role are fixed for safety — everything else on this page you can edit yourself.
          </div>

          <hr />

          <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--heading)' }}>Contact &amp; safety</div>
          <div>
            <label style={labelStyle}>Contact Info</label>
            <input value={contact} onChange={e => setContact(e.target.value)} placeholder={isPsych ? 'Your email (crisis alerts sent here)' : 'Phone or email'} style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>Trusted Contact</label>
            <input value={trusted} onChange={e => setTrusted(e.target.value)} placeholder="Trusted contact email (crisis alerts sent there)" style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>Country &amp; Timezone</label>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
              <select value={country} onChange={e => setCountry(e.target.value)}>
                <option value="">Country…</option>
                {COUNTRIES.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
              <select value={timezone} onChange={e => setTimezone(e.target.value)}>
                <option value="">Auto (based on country)</option>
                {TIMEZONES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>
            <div style={{ fontSize: '0.68rem', color: 'var(--muted)', marginTop: '4px' }}>Birthday wishes &amp; daily check-in cards follow this timezone.</div>
          </div>

          <div className="flex items-center gap-3">
            <button type="submit" disabled={saving} className="btn-primary">{saving ? 'Saving...' : '💾 Save changes'}</button>
            {msg && <span style={{ fontSize: '0.75rem', fontWeight: 600, color: ok ? 'var(--ok)' : 'var(--danger)' }}>{msg}</span>}
          </div>
        </form>
      </div>

      {/* Account security — change your own password after verifying the current one */}
      <div className="card" style={{ padding: '24px' }}>
        <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--heading)', marginBottom: '4px' }}>🔐 Account security</div>
        <div style={{ fontSize: '0.7rem', color: 'var(--muted)', lineHeight: 1.6, marginBottom: '14px' }}>
          Your username <strong>@{user.username}</strong> is the account key used across your journals, moods, bookings and ring readings, so it stays fixed. You can change your password here.
        </div>
        <form onSubmit={handlePassword} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
          <div style={{ gridColumn: '1 / -1' }}>
            <label style={labelStyle}>Current password</label>
            <input type="password" value={currentPw} onChange={e => setCurrentPw(e.target.value)} autoComplete="current-password" placeholder="Current password" style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>New password</label>
            <input type="password" value={newPw} onChange={e => setNewPw(e.target.value)} autoComplete="new-password" placeholder="New password" style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>Confirm new password</label>
            <input type="password" value={confirmPw} onChange={e => setConfirmPw(e.target.value)} autoComplete="new-password" placeholder="Repeat new password" style={inputStyle} />
          </div>
          <div style={{ gridColumn: '1 / -1', fontSize: '0.66rem', color: 'var(--muted)', lineHeight: 1.6 }}>
            At least 6 characters with an uppercase letter, a lowercase letter, a number and a special character.
          </div>
          <div className="flex items-center gap-3" style={{ gridColumn: '1 / -1' }}>
            <button type="submit" disabled={pwSaving} className="btn-primary">{pwSaving ? 'Updating…' : '🔑 Change password'}</button>
            {pwMsg && <span style={{ fontSize: '0.75rem', fontWeight: 600, color: pwOk ? 'var(--ok)' : 'var(--danger)' }}>{pwMsg}</span>}
          </div>
        </form>
      </div>
    </div>
  )
}
