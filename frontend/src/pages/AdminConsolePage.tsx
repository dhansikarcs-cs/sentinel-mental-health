import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { getUser } from '../stores/auth'
import { formatDateTime } from '../constants'

/**
 * Admin Console — NEW FEATURE
 * A read-only oversight cockpit for clinic administrators:
 *  · Clinic-wide stats (users by role, activity, risk mix)
 *  · Directory of every account with role badges
 *  · Live audit log (hash-chained, tamper-evident) viewer
 *  · Crisis history feed
 */
export default function AdminConsolePage() {
  const [tab, setTab] = useState<'overview' | 'directory' | 'invites' | 'audit' | 'crises'>('overview')
  const [psychs, setPsychs] = useState<any[]>([])
  const [clients, setClients] = useState<any[]>([])
  const [events, setEvents] = useState<any[]>([])
  const [crisisLog, setCrisisLog] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [query, setQuery] = useState('')
  const [showCreateClient, setShowCreateClient] = useState(false)
  const user = getUser()

  useEffect(() => {
    Promise.allSettled([
      api.get('/psychologists/directory'),
      api.get('/events?limit=80'),
      api.get('/crisis/log'),
    ]).then(([d, e, c]) => {
      if (d.status === 'fulfilled') {
        setPsychs((d.value as any)?.psychologists || [])
        setClients((d.value as any)?.clients || [])
      }
      if (e.status === 'fulfilled') {
        const evs = (e.value as any)?.events || (e.value as any) || []
        setEvents(Array.isArray(evs) ? evs : [])
      }
      if (c.status === 'fulfilled') setCrisisLog(Array.isArray(c.value) ? c.value : [])
    }).finally(() => setLoading(false))
  }, [])

  const dirQuery = query.toLowerCase()
  const dirRows = clients.filter((u: any) =>
    !dirQuery ||
    (u.name || '').toLowerCase().includes(dirQuery) ||
    (u.username || '').toLowerCase().includes(dirQuery) ||
    (u.clinic || '').toLowerCase().includes(dirQuery) ||
    (u.assigned_psych || '').toLowerCase().includes(dirQuery)
  )

  return (
    <div className="animate-fade-in">
      <div className="segmented-control">
        {[
          { k: 'overview', label: '📊 Overview' },
          { k: 'directory', label: '👥 Directory' },
          ...(user?.role === 'admin' ? [{ k: 'invites', label: '🎟 Invites' }] : []),
          { k: 'audit', label: '🧾 Audit log' },
          { k: 'crises', label: '🚨 Crises' },
        ].map(t => (
          <button key={t.k} className={`segmented-btn${tab === t.k ? ' active' : ''}`} onClick={() => setTab(t.k as any)}>
            {t.label}
          </button>
        ))}
      </div>

      {loading && <div className="card" style={{ color: 'var(--muted)' }}>Loading clinic data…</div>}

      {!loading && tab === 'overview' && (
        <OverviewPanel psychs={psychs} clients={clients} events={events} crisisLog={crisisLog} />
      )}

      {showCreateClient && (
        <CreateClientModal
          onClose={() => setShowCreateClient(false)}
          onCreated={username => {
            setShowCreateClient(false)
            window.alert(`Client @${username} created. Share their username + password securely — they can change it after signing in.`)
            window.location.reload()
          }}
        />
      )}

      {!loading && tab === 'directory' && (
        <div>
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center', marginBottom: '14px', flexWrap: 'wrap' }}>
            <h3 style={{ margin: 0 }}>Client directory ({dirRows.length})</h3>
            {user?.role !== 'patient' && (
              <button className="btn-primary" style={{ fontSize: '0.72rem', padding: '7px 16px' }} onClick={() => setShowCreateClient(true)}>
                ＋ Create client account
              </button>
            )}
            <input placeholder="🔍 Search name, username, clinician…" value={query} onChange={e => setQuery(e.target.value)} style={{ marginLeft: 'auto', width: '240px', borderRadius: 999 }} />
          </div>
          <div className="card" style={{ padding: '8px' }}>
            {dirRows.map((u: any, i: number) => (
              <div key={u.username || i} style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '11px 14px', borderBottom: i < dirRows.length - 1 ? '1px solid var(--border-soft)' : 'none' }}>
                <div className="avatar-sm" style={{ background: 'var(--surface-soft-2)', border: '1px solid var(--border)', color: 'var(--heading)', width: 36, height: 36, minWidth: 36, fontSize: '0.75rem' }}>
                  {(u.name || '?').split(' ').map((w: any) => w[0]).slice(0, 2).join('').toUpperCase()}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 700, fontSize: '0.85rem' }}>{u.name || u.username}</div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--muted)' }}>@{u.username} · {u.age ? `${u.age} yrs · ` : ''}{u.assigned_psych || 'unassigned'} · joined {u.created_at?.slice(0, 10) || '—'}</div>
                </div>
                <span className="badge-theme">{u.clinic || '—'}</span>
              </div>
            ))}
            {dirRows.length === 0 && <div style={{ padding: '20px', textAlign: 'center', color: 'var(--muted)' }}>No accounts match.</div>}
          </div>
        </div>
      )}

      {!loading && tab === 'invites' && user?.role === 'admin' && <InvitesPanel />}

      {!loading && tab === 'audit' && (
        <div>
          <h3 style={{ marginBottom: '4px' }}>🧾 Audit log <span className="badge-theme">hash-chained</span></h3>
          <div style={{ fontSize: '0.72rem', color: 'var(--muted)', marginBottom: '12px' }}>
            Every sensitive action is recorded with a SHA-256 chain — any tamper breaks the chain and is detectable.
          </div>
          <div className="card" style={{ padding: '8px', maxHeight: '560px', overflowY: 'auto' }}>
            {events.map((e: any, i: number) => (
              <div key={e.id || i} style={{ display: 'flex', gap: '10px', alignItems: 'center', padding: '9px 14px', borderBottom: i < events.length - 1 ? '1px solid var(--border-soft)' : 'none', fontSize: '0.75rem' }}>
                <span style={{
                  width: 7, height: 7, borderRadius: 999, flexShrink: 0,
                  background: e.severity === 'ERROR' ? 'var(--danger)' : e.severity === 'WARNING' ? 'var(--warn)' : 'var(--ok)',
                }} />
                <span style={{ color: 'var(--faint)', minWidth: '135px', fontWeight: 600 }}>{formatDateTime(e.timestamp)}</span>
                <span style={{ fontWeight: 700, color: 'var(--heading)', minWidth: '150px' }}>{e.action || e.event_type || 'event'}</span>
                <span style={{ color: 'var(--secondary)', flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {e.user || e.username || ''} {e.details || e.payload ? `· ${String(e.details || JSON.stringify(e.payload)).slice(0, 90)}` : ''}
                </span>
              </div>
            ))}
            {events.length === 0 && <div style={{ padding: '20px', textAlign: 'center', color: 'var(--muted)' }}>No events found.</div>}
          </div>
        </div>
      )}

      {!loading && tab === 'crises' && (
        <div>
          <h3 style={{ marginBottom: '12px' }}>🚨 Crisis history</h3>
          {crisisLog.length === 0 ? (
            <div className="card" style={{ textAlign: 'center', color: 'var(--muted)' }}>No crisis events recorded.</div>
          ) : (
            <div className="space-y-2">
              {[...crisisLog].reverse().slice(0, 40).map((c: any, i: number) => (
                <div key={c.id || i} className="card-sm" style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                  <span style={{
                    fontSize: '0.62rem', fontWeight: 800, padding: '4px 10px', borderRadius: 999,
                    background: c.event === 'resolved' ? 'var(--ok-soft)' : 'var(--danger-soft)',
                    color: c.event === 'resolved' ? 'var(--ok)' : 'var(--danger)',
                  }}>{(c.event || '').toUpperCase()}</span>
                  <strong style={{ fontSize: '0.8rem' }}>{c.patient || '—'}</strong>
                  <span style={{ color: 'var(--muted)', fontSize: '0.68rem', marginLeft: 'auto' }}>{formatDateTime(c.timestamp)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function InvitesPanel() {
  const [invites, setInvites] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [clinic, setClinic] = useState('')
  const [maxUses, setMaxUses] = useState(1)
  const [expiresDays, setExpiresDays] = useState(14)
  const [lastCode, setLastCode] = useState('')
  const [error, setError] = useState('')
  const [copied, setCopied] = useState('')

  async function load() {
    setLoading(true)
    try {
      const d: any = await api.listInvites()
      setInvites(d?.data?.invites || d?.invites || [])
      setError('')
    } catch (e: any) {
      setError(e.message || 'Failed to load invites')
    }
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  async function create() {
    if (!clinic.trim()) { setError('Clinic code is required'); return }
    setBusy(true)
    try {
      const d: any = await api.createInvite({ clinic_code: clinic.trim().toUpperCase(), max_uses: maxUses, expires_in_days: expiresDays })
      setLastCode(d?.data?.code || '')
      setCopied('')
      await load()
    } catch (e: any) {
      setError(e.message || 'Failed to create invite')
    }
    setBusy(false)
  }

  async function revoke(code: string) {
    if (!window.confirm(`Revoke invite ${code}? Doctors won't be able to sign up with it anymore.`)) return
    setBusy(true)
    try { await api.revokeInvite(code); await load() } catch (e: any) { alert(e.message || 'Revoke failed') }
    setBusy(false)
  }

  function copy(code: string) {
    navigator.clipboard?.writeText(code).then(() => {
      setCopied(code)
      setTimeout(() => setCopied(''), 1500)
    }).catch(() => {})
  }

  return (
    <div>
      <h3 style={{ marginBottom: '4px' }}>🎟 Doctor invite codes</h3>
      <div style={{ fontSize: '0.72rem', color: 'var(--muted)', marginBottom: '12px' }}>
        Generate a code and hand it to the clinician — they enter it at sign-up together with their license number.
      </div>

      <div className="card-sm" style={{ display: 'flex', gap: '10px', alignItems: 'flex-end', flexWrap: 'wrap', padding: '14px 16px', marginBottom: '14px' }}>
        <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '0.62rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--muted)' }}>
          Clinic code
          <input value={clinic} onChange={e => setClinic(e.target.value)} placeholder="e.g. SENTINEL-01" style={{ width: '160px', textTransform: 'uppercase' }} />
        </label>
        <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '0.62rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--muted)' }}>
          Max uses
          <input type="number" min={1} max={500} value={maxUses} onChange={e => setMaxUses(Math.max(1, Number(e.target.value) || 1))} style={{ width: '90px' }} />
        </label>
        <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '0.62rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--muted)' }}>
          Expires in (days)
          <input type="number" min={1} max={365} value={expiresDays} onChange={e => setExpiresDays(Math.max(1, Number(e.target.value) || 14))} style={{ width: '90px' }} />
        </label>
        <button className="btn-primary" onClick={create} disabled={busy} style={{ fontSize: '0.75rem', padding: '9px 18px' }}>
          {busy ? '…' : '＋ Generate invite'}
        </button>
        {lastCode && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'var(--ok-soft)', border: '1px solid color-mix(in srgb, var(--ok) 35%, transparent)', borderRadius: 999, padding: '6px 14px' }}>
            <strong style={{ fontSize: '0.8rem', color: 'var(--ok)', letterSpacing: '0.04em' }}>{lastCode}</strong>
            <button onClick={() => copy(lastCode)} style={{ fontSize: '0.65rem', fontWeight: 800 }}>
              {copied === lastCode ? '✓ copied' : '📋 copy'}
            </button>
          </div>
        )}
      </div>
      {error && <div style={{ color: 'var(--danger)', fontSize: '0.75rem', marginBottom: '10px', fontWeight: 600 }}>⚠️ {error}</div>}

      <div className="card" style={{ padding: '8px' }}>
        {loading && <div style={{ padding: '16px', color: 'var(--muted)' }}>Loading invites…</div>}
        {!loading && invites.length === 0 && <div style={{ padding: '16px', textAlign: 'center', color: 'var(--muted)' }}>No invite codes yet — generate the first one above.</div>}
        {!loading && invites.map((inv: any, i: number) => (
          <div key={inv.code} style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '11px 14px', borderBottom: i < invites.length - 1 ? '1px solid var(--border-soft)' : 'none', flexWrap: 'wrap' }}>
            <strong style={{ fontSize: '0.82rem', letterSpacing: '0.04em', color: inv.revoked ? 'var(--faint)' : 'var(--heading)' }}>{inv.code}</strong>
            <span className="badge-theme">{inv.clinic_code || '—'}</span>
            <span style={{ fontSize: '0.66rem', color: 'var(--muted)' }}>
              {inv.use_count}/{inv.max_uses} used · expires {inv.expires_at?.slice(0, 10) || 'never'}
            </span>
            {inv.used_by && <span style={{ fontSize: '0.64rem', color: 'var(--faint)' }}>last: @{inv.used_by}</span>}
            <div style={{ flex: 1 }} />
            {inv.revoked ? (
              <span style={{ fontSize: '0.62rem', fontWeight: 800, color: 'var(--danger)' }}>REVOKED</span>
            ) : inv.expired || inv.exhausted ? (
              <span style={{ fontSize: '0.62rem', fontWeight: 800, color: 'var(--warn)' }}>{inv.expired ? 'EXPIRED' : 'FULL'}</span>
            ) : (
              <>
                <button onClick={() => copy(inv.code)} disabled={busy} style={{ fontSize: '0.65rem', fontWeight: 700 }}>
                  {copied === inv.code ? '✓ copied' : '📋 Copy'}
                </button>
                <button onClick={() => revoke(inv.code)} disabled={busy} style={{ fontSize: '0.65rem', fontWeight: 700, color: 'var(--danger)' }}>
                  🚫 Revoke
                </button>
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

function CreateClientModal({ onClose, onCreated }: { onClose: () => void; onCreated: (username: string) => void }) {
  const [form, setForm] = useState({ username: '', password: '', name: '', dob: '', occupation: '', contact_info: '', country: '' })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (!form.username.trim() || !form.name.trim() || !form.dob || form.password.length < 6) {
      setError('Username, full name, DOB and a 6+ char password are required.')
      return
    }
    setBusy(true)
    setError('')
    try {
      await api.createClientAccount({ ...form, username: form.username.trim(), contact_info: form.contact_info.trim() || undefined })
      onCreated(form.username.trim())
    } catch (e: any) {
      setError(e.message || 'Failed to create client')
    }
    setBusy(false)
  }

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.55)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 60, padding: '20px' }} onClick={onClose}>
      <form className="card" onClick={e => e.stopPropagation()} onSubmit={submit} style={{ width: '100%', maxWidth: '430px', display: 'flex', flexDirection: 'column', gap: '10px', padding: '26px 24px' }}>
        <h3 style={{ margin: 0 }}>🧑 Create client account</h3>
        <div style={{ fontSize: '0.72rem', color: 'var(--muted)', marginBottom: '2px' }}>
          The account joins your clinic and is assigned to you. Share the username + password with the client securely; they can change the password later.
        </div>
        {error && <div style={{ background: 'var(--danger-soft)', color: 'var(--danger-deep, var(--danger))', fontSize: '0.75rem', fontWeight: 600, padding: '8px 12px', borderRadius: '10px' }}>⚠️ {error}</div>}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
          <label style={flbl}>Full name<input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} placeholder="Jamie Rivera" /></label>
          <label style={flbl}>Username<input value={form.username} onChange={e => setForm(f => ({ ...f, username: e.target.value }))} placeholder="jamie.r" /></label>
          <label style={flbl}>Date of birth<input type="date" value={form.dob} onChange={e => setForm(f => ({ ...f, dob: e.target.value }))} /></label>
          <label style={flbl}>Occupation / school<input value={form.occupation} onChange={e => setForm(f => ({ ...f, occupation: e.target.value }))} placeholder="Student, Lincoln High" /></label>
          <label style={flbl}>Contact email (optional)<input type="email" value={form.contact_info} onChange={e => setForm(f => ({ ...f, contact_info: e.target.value }))} placeholder="jamie@example.com" /></label>
          <label style={flbl}>Temp password<input type="text" value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))} placeholder="min 6 chars" /></label>
          <label style={{ ...flbl, gridColumn: '1 / -1' }}>Country (optional)
            <input value={form.country} onChange={e => setForm(f => ({ ...f, country: e.target.value }))} placeholder="Singapore" />
          </label>
        </div>
        <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
          <button type="submit" className="btn-primary" disabled={busy} style={{ flex: 1 }}>{busy ? 'Creating…' : 'Create account'}</button>
          <button type="button" onClick={onClose} disabled={busy}>Cancel</button>
        </div>
      </form>
    </div>
  )
}

const flbl: React.CSSProperties = { display: 'flex', flexDirection: 'column', gap: '3px', fontSize: '0.6rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--muted)' }

function OverviewPanel({ psychs, clients, events, crisisLog }: { psychs: any[]; clients: any[]; events: any[]; crisisLog: any[] }) {
  const last24 = events.filter((e: any) => {
    try { return (Date.now() - new Date(e.created_at || e.timestamp).getTime()) < 86400_000 } catch { return false }
  }).length
  const crisisCount = crisisLog.length

  return (
    <div className="space-y-4">
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '10px' }}>
        {[
          { label: 'Clients', value: clients.length, sub: 'registered in clinic', color: 'var(--accent)' },
          { label: 'Clinicians', value: psychs.length, sub: 'on staff', color: 'var(--info)' },
          { label: 'Events · 24h', value: last24, sub: 'audited actions', color: 'var(--info)' },
          { label: 'Crisis events', value: crisisCount, sub: 'all time', color: crisisCount ? 'var(--danger)' : 'var(--ok)' },
        ].map(s => (
          <div key={s.label} className="card-sm">
            <div style={{ fontSize: '0.62rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--muted)' }}>{s.label}</div>
            <div className="statnum" style={{ color: s.color, margin: '4px 0 2px' }}>{s.value}</div>
            <div style={{ fontSize: '0.65rem', color: 'var(--faint)' }}>{s.sub}</div>
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '14px', alignItems: 'start' }} className="admin-grid">
        <div className="card">
          <h3 style={{ marginBottom: '10px' }}>Recent system activity</h3>
          <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
            {events.slice(0, 14).map((e: any, i: number) => (
              <div key={e.id || i} style={{ display: 'flex', gap: '10px', padding: '7px 0', borderBottom: '1px solid var(--border-soft)', fontSize: '0.74rem', alignItems: 'center' }}>
                <span className="dot" style={{ background: e.severity === 'ERROR' ? 'var(--danger)' : e.severity === 'WARNING' ? 'var(--warn)' : 'var(--ok)' }} />
                <span style={{ color: 'var(--faint)', fontSize: '0.65rem', minWidth: '110px' }}>{formatDateTime(e.timestamp)}</span>
                <strong style={{ minWidth: '120px', fontSize: '0.72rem' }}>{e.action || e.event_type || 'event'}</strong>
                <span style={{ color: 'var(--muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{e.user || e.username || ''}</span>
              </div>
            ))}
            {events.length === 0 && <div style={{ color: 'var(--muted)', fontSize: '0.8rem' }}>No events yet.</div>}
          </div>
        </div>

        <div className="card">
          <h3 style={{ marginBottom: '10px' }}>Clinicians on staff</h3>
          <div className="space-y-2">
            {psychs.slice(0, 8).map((p: any) => (
              <div key={p.username} className="card-stage" style={{ justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
                  <div className="avatar-sm" style={{ width: 32, height: 32, minWidth: 32, fontSize: '0.68rem', background: 'var(--surface-soft-2)', border: '1px solid var(--border)' }}>
                    {(p.name || '?').split(' ').map((w: any) => w[0]).slice(0, 2).join('').toUpperCase()}
                  </div>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontWeight: 700, fontSize: '0.78rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{p.name}</div>
                    <div style={{ fontSize: '0.62rem', color: 'var(--muted)' }}>{p.specialisation || p.clinic}</div>
                  </div>
                </div>
                <span className="badge-theme">{p.clinic}</span>
              </div>
            ))}
            {psychs.length === 0 && <div style={{ color: 'var(--muted)', fontSize: '0.8rem' }}>No clinicians registered.</div>}
          </div>
        </div>
      </div>
      <style>{`@media (max-width: 960px) { .admin-grid { grid-template-columns: 1fr !important; } }`}</style>
    </div>
  )
}
