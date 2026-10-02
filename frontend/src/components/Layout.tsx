import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom'
import { getUser, logout, subscribe } from '../stores/auth'
import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import { flushOutbox, getOutboxCount, subscribeOutbox } from '../api/outbox'
import { computeCrisisStage, CRISIS_STAGE_MESSAGES, todayStr, formatDateTime, formatDate } from '../constants'
import OnboardingTour from './OnboardingTour'
import { useTheme } from '../hooks/useTheme'

const QUOTES = [
  'The wound is the place where the Light enters you. — Rumi',
  'Out of suffering have emerged the strongest souls. — Kahlil Gibran',
  'Healing takes time, and asking for help is a courageous step.',
  'Rest is not idleness. It is preparation for meaningful work.',
  'You are not your illness. You have an individual story to tell. — Viktor Frankl',
  'There is hope, even when your brain tells you there isn’t. — John Green',
  'Self-care is not selfish. You cannot serve from an empty vessel.',
  'The only journey is the journey within. — Rainer Maria Rilke',
]

/* ── Icon glyphs (inline SVG, lucide-style strokes) ─────────────── */
const I = {
  home: 'M3 10.5 12 3l9 7.5M5 9.5V21h14V9.5',
  journal: 'M15.5 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2V7.5L15.5 3zM14 3v5h6M9 13h7M9 17h5',
  smile: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM9 10h.01M15 10h.01M8.5 14.5s1.2 2 3.5 2 3.5-2 3.5-2',
  calendar: 'M7 3v3M17 3v3M4 8h16M5 5h14a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1z',
  tasks: 'M9 6h11M9 12h11M9 18h11M4 6h.01M4 12h.01M4 18h.01',
  search: 'M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14zM20 20l-4-4',
  alert: 'M12 3 2.5 20h19L12 3zM12 10v4M12 17.5h.01',
  users: 'M16 20v-1.5a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4V20M9.5 10.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7zM21 20v-1.5a4 4 0 0 0-3-3.85M15.5 3.75a4 4 0 0 1 0 7.6',
  note: 'M12 20h9M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z',
  chart: 'M4 20V10M10 20V4M16 20v-7M21 20H3',
  laptop: 'M4 5h16v11H4zM2 19h20',
  box: 'M21 8 12 3 3 8v8l9 5 9-5V8zM3 8l9 5 9-5M12 13v8',
  chat: 'M21 12a8 8 0 0 1-8 8H4l1.5-3.5A8 8 0 1 1 21 12z',
  logout: 'M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9',
  moon: 'M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z',
  sun: 'M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10zM12 1v2M12 21v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M1 12h2M21 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4',
  bell: 'M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.7 21a2 2 0 0 1-3.4 0',
  shield: 'M12 22s8-3.5 8-10V5l-8-3-8 3v7c0 6.5 8 10 8 10z',
  heart: 'M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1-1.1a5.5 5.5 0 0 0-7.8 7.8l1 1L12 21l7.8-7.6 1-1a5.5 5.5 0 0 0 0-7.8z',
  user: 'M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z',
}

function RailIcon({ to, label, d, danger }: { to: string; label: string; d: string; danger?: boolean }) {
  const location = useLocation()
  const navigate = useNavigate()
  const active = location.pathname === to
  return (
    <button
      className={`icon-btn${active ? ' active' : ''}`}
      style={danger ? { color: 'var(--danger)' } : undefined}
      title={label}
      aria-label={label}
      onClick={() => navigate(to)}
    >
      <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d={d} /></svg>
    </button>
  )
}

interface Tab { to: string; label: string; icon: string }
const patientTabs: Tab[] = [
  { to: '/dashboard', label: 'Wellness', icon: I.home },
  { to: '/journal', label: 'Journal', icon: I.journal },
  { to: '/companion', label: 'AI Hub', icon: I.chat },
  { to: '/bookings', label: 'Booking', icon: I.calendar },
  { to: '/followups', label: 'Follow-Up', icon: I.tasks },
  { to: '/timeline', label: 'Timeline', icon: I.search },
  { to: '/crisis', label: 'Emergency', icon: I.alert },
]
const psychTabs: Tab[] = [
  { to: '/open-session', label: 'Open Session', icon: I.laptop },
  { to: '/triage', label: 'Patient Triage', icon: I.users },
  { to: '/clinical-notes', label: 'Clinical Notes', icon: I.note },
  { to: '/patient-insights', label: 'Patient Insights', icon: I.chart },
  { to: '/psych-journal', label: 'Journal & Wellness', icon: I.heart },
  { to: '/bookings', label: 'Bookings', icon: I.calendar },
  { to: '/followups', label: 'Follow-Up', icon: I.tasks },
  { to: '/export', label: 'Export Center', icon: I.box },
]

const TIER_DOT: Record<string, string> = { crisis: 'var(--danger)', high: '#E8763B', attention: 'var(--warn)', stable: 'var(--ok)' }

export default function Layout() {
  const navigate = useNavigate()
  const location = useLocation()
  const [user, setUser] = useState(getUser())
  const [crisisState, setCrisisState] = useState<any>(null)
  const [crisisLog, setCrisisLog] = useState<any[]>([])
  const [quoteIdx] = useState(() => Math.floor(Math.random() * QUOTES.length))
  const [crisisElapsed, setCrisisElapsed] = useState(0)
  const [theme, setTheme] = useTheme()
  const [pendingSync, setPendingSync] = useState(0)

  const [patients, setPatients] = useState<any[]>([])
  const [bookings, setBookings] = useState<any[]>([])
  const [journals, setJournals] = useState<any[]>([])
  const [moods, setMoods] = useState<any[]>([])
  const [notifications, setNotifications] = useState<any[]>([])
  const unreadCount = notifications.filter((n: any) => !n.read).length
  const [notifOpen, setNotifOpen] = useState(false)
  const [toasts, setToasts] = useState<any[]>([])
  const seenToastIds = useRef<Set<number>>(new Set())
  const toastInit = useRef(false)

  function syncToasts(list: any[]) {
    const all = Array.isArray(list) ? list : []
    const unread = all.filter((n: any) => !n.read)
    if (!toastInit.current) {
      unread.forEach((n: any) => seenToastIds.current.add(n.id))
      toastInit.current = true
      return
    }
    const fresh = unread.filter((n: any) => !seenToastIds.current.has(n.id))
    fresh.forEach((n: any) => {
      seenToastIds.current.add(n.id)
      const key = `${n.id}-${Date.now()}`
      setToasts(prev => [...prev, { key, ...n }].slice(-4))
      window.setTimeout(() => setToasts(prev => prev.filter(t => t.key !== key)), 7000)
    })
  }

  function dismissToast(t: any) {
    setToasts(prev => prev.filter(x => x.key !== t.key))
    api.markNotificationRead(t.id)
      .then(() => setNotifications(prev => prev.map(p => p.id === t.id ? { ...p, read: true } : p)))
      .catch(() => {})
  }
  const [triagePriorities, setTriagePriorities] = useState<any[]>([])
  const [aiInsights, setAiInsights] = useState<Record<string, any>>({})
  const [aiStatus, setAiStatus] = useState<any>(null)

  useEffect(() => {
    const unsub = subscribe(() => setUser(getUser()))
    return unsub
  }, [])

  useEffect(() => {
    api.getCrisisState().then(setCrisisState).catch(() => {})
    api.get('/crisis/log').then((d: any) => setCrisisLog(Array.isArray(d) ? d : [])).catch(() => setCrisisLog([]))
    api.get('/ai/health').then(setAiStatus).catch(() => setAiStatus(null))
  }, [])

  useEffect(() => {
    const refresh = () => { getOutboxCount().then(setPendingSync).catch(() => setPendingSync(0)) }
    refresh()
    const unsub = subscribeOutbox(refresh)
    const onOnline = () => {
      refresh()
      flushOutbox(api).then(() => refresh()).catch(() => refresh())
    }
    window.addEventListener('online', onOnline)
    const flushTimer = setInterval(() => {
      getOutboxCount().then((n) => {
        if (n > 0 && !('onLine' in navigator && !navigator.onLine)) {
          flushOutbox(api).then(() => refresh()).catch(() => refresh())
        }
      }).catch(() => {})
    }, 45000)
    return () => { unsub(); window.removeEventListener('online', onOnline); clearInterval(flushTimer) }
  }, [])

  useEffect(() => {
    const interval = setInterval(() => {
      api.getCrisisState().then((state) => {
        setCrisisState(state)
        if (state?.active) {
          api.getCrisisElapsed().then((e: any) => setCrisisElapsed(e?.elapsed || 0)).catch(() => {})
        }
      }).catch(() => {})
      api.get('/crisis/log').then((d: any) => setCrisisLog(Array.isArray(d) ? d : [])).catch(() => {})
      api.getNotifications().then((d: any) => { setNotifications(Array.isArray(d) ? d : []); syncToasts(d) }).catch(() => {})
    }, 5000)
    return () => clearInterval(interval)
  }, [])

  const role = user?.role === 'psychologist' ? 'Psychologist' : user?.role === 'admin' ? 'Admin' : 'Patient'

  useEffect(() => {
    if (role === 'Psychologist') {
      api.getPsychPatients().then(async (d: any) => {
        const pts = Array.isArray(d) ? d : []
        setPatients(pts)
        if (pts.length > 0) {
          const results = await Promise.allSettled(
            pts.map((p: any) => api.triageSummary(p.username || p).catch(() => null))
          )
          const computed = pts.map((p: any, i: any) => {
            const result = results[i]?.status === 'fulfilled' ? results[i].value : null
            const tier: string = result?.tier || 'stable'
            const crisis: boolean = result?.crisis ?? false
            const score: number = result?.priority_score ?? 0
            return { patient: p.username || p, name: p.name || p, score, tier, crisis, ...(result || {}) }
          })
          computed.sort((a: any, b: any) => b.score - a.score)
          setTriagePriorities(computed)
          const insights: Record<string, any> = {}
          await Promise.allSettled(
            pts.slice(0, 6).map(async (p: any) => {
              try {
                const res = await api.get(`/journal/${p.username || p}/summaries`)
                if (res && (res as any).summary) insights[p.username || p] = res
              } catch {}
            })
          )
          setAiInsights(insights)
        }
      }).catch(() => {})
    } else {
      api.getWellness().then((d: any) => {}).catch(() => {})
      api.getNotifications().then((d: any) => { setNotifications(Array.isArray(d) ? d : []); syncToasts(d) }).catch(() => {})
    }
    api.getBookings().then((d: any) => setBookings(Array.isArray(d) ? d : [])).catch(() => {})
  }, [role])

  useEffect(() => {
    if (role === 'Patient') {
      api.getJournals().then((d: any) => setJournals(Array.isArray(d) ? d : [])).catch(() => {})
      api.getMoods().then((d: any) => setMoods(Array.isArray(d) ? d : [])).catch(() => {})
    }
  }, [role])

  const baseTabs = role === 'Psychologist' ? psychTabs : patientTabs
  const tabs: Tab[] = role === 'Admin' ? [...patientTabs, { to: '/admin', label: 'Admin Console', icon: I.shield }] : baseTabs
  const activeTab = tabs.find(t => location.pathname === t.to) || tabs[0]

  const journalOk = journals.some((j: any) => {
    const d = (j.created_at || j.timestamp || '').slice(0, 10)
    return d === todayStr()
  }) ? 'Logged' : 'Not yet'
  const nextSession = (() => {
    const approved = bookings.filter((b: any) => b.status === 'Approved').sort((a: any, b: any) => (a.date || '').localeCompare(b.date || ''))
    if (approved.length === 0) return '—'
    return `${approved[0].date || ''} · ${approved[0].time || ''}`
  })()
  const todayMood = (() => {
    const m = moods.find((m: any) => (m.date || '').slice(0, 10) === todayStr())
    return m ? m.emoji || m.label || 'Logged' : '—'
  })()

  const patientCount = patients.length
  const pendingBookings = bookings.filter((b: any) => b.status === 'Pending').length
  const silentPatients = patients.filter((p: any) => {
    const lastActive = p.last_active ? new Date(p.last_active) : null
    if (!lastActive) return true
    const diff = (Date.now() - lastActive.getTime()) / (1000 * 60 * 60)
    return diff > 48
  }).length
  const highRiskCount = triagePriorities.filter((p: any) => p.tier === 'crisis' || p.tier === 'high').length

  const isPsychRole = role === 'Psychologist'

  async function triggerSelfCrisis() {
    try { await api.triggerCrisis() } catch {}
  }

  const showCrisisBanner = crisisState?.active
  const cs = crisisState || {}
  const crisisStage = computeCrisisStage(cs, crisisElapsed)

  const lastBooking = bookings.length > 0 ? bookings[bookings.length - 1] : null
  const bookingMsg = lastBooking ? ({
    Approved: { text: '✅ Booking Accepted! Your session has been confirmed.', color: 'var(--ok)' },
    Rejected: { text: '❌ Booking Declined.', color: 'var(--danger)' },
    Cancelled: { text: '🔴 Booking Cancelled.', color: 'var(--muted)' },
  } as Record<string, { text: string; color: string } | undefined>)[lastBooking.status] : null

  const initials = (user?.name || user?.username || '?').split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase()
  const firstName = (user?.name || user?.username || '').split(' ')[0]

  const patientNames: Record<string, string> = {}
  patients.forEach((p: any) => { patientNames[p.username || p] = p.name || p.username || p })

  // Next confirmed sessions (today onward) — shown as chips in the top bar
  const upcomingSessions = bookings
    .filter((b: any) => b.status === 'Approved' && (b.date || '') >= todayStr())
    .sort((a: any, b: any) => `${a.date} ${a.time}`.localeCompare(`${b.date} ${b.time}`))
    .slice(0, 3)

  const notifPanel = notifOpen && (
    <div className="notif-panel-pop" style={{
      position: 'absolute', top: '64px', right: 0, width: '340px', maxHeight: '420px', overflowY: 'auto',
      background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '20px',
      boxShadow: 'var(--shadow-lg)', padding: '12px', zIndex: 100,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '4px 8px 10px' }}>
        <strong style={{ fontSize: '0.875rem' }}>Notifications</strong>
        {unreadCount > 0 && (
          <button className="btn-ghost" style={{ fontSize: '0.7rem', padding: '4px 10px' }}
            onClick={() => api.markAllNotificationsRead().then(() => setNotifications((prev: any[]) => prev.map(p => ({ ...p, read: 1 })))).catch(() => {})}>
            Mark all read
          </button>
        )}
      </div>
      {notifications.length === 0 && <div style={{ color: 'var(--muted)', fontSize: '0.8rem', padding: '10px' }}>All caught up ✨</div>}
      {notifications.slice(0, 12).map((n: any) => (
        <div key={n.id}
          onClick={() => { if (!n.read) api.markNotificationRead(n.id).then(() => setNotifications(prev => prev.map(p => p.id === n.id ? { ...p, read: 1 } : p))).catch(() => {}) }}
          style={{
            padding: '10px 12px', borderRadius: '12px', cursor: 'pointer', marginBottom: '4px',
            background: n.read ? 'transparent' : 'var(--accent-soft)',
            border: `1px solid ${n.read ? 'transparent' : 'color-mix(in srgb, var(--accent) 25%, transparent)'}`,
          }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '8px' }}>
            <strong style={{ fontSize: '0.78rem', color: n.notification_type === 'crisis' ? 'var(--danger)' : 'var(--heading)' }}>{n.title}</strong>
            <span style={{ fontSize: '0.62rem', color: 'var(--faint)', whiteSpace: 'nowrap' }}>{(n.sent_at || '').slice(5, 16).replace('T', ' ')}</span>
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--secondary)', marginTop: '2px' }}>{n.message}</div>
        </div>
      ))}
    </div>
  )

  return (
    <div style={{ minHeight: '100vh', padding: '14px 18px 14px 96px', position: 'relative', zIndex: 1 }}>
      {/* ══ Aurora background — landing glow blobs drifting behind the app ══ */}
      <div className="aurora" aria-hidden>
        <span className="a1" />
        <span className="a2" />
        <span className="a3" />
      </div>
      {/* ══ Floating icon rail ══ */}
      <nav className="rail" aria-label="Primary">
        <Link to={isPsychRole ? '/triage' : '/dashboard'} title="Sentinel">
          <div className="rail-logo">✳</div>
        </Link>
        <div className="rail-sep" />
        {tabs.map(t => <RailIcon key={t.to} to={t.to} label={t.label} d={t.icon} danger={t.to === '/crisis'} />)}
        <div className="rail-sep" />
        <button className="icon-btn" title={theme === 'dark' ? 'Light mode' : 'Dark mode'} onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d={theme === 'dark' ? I.sun : I.moon} /></svg>
        </button>
        <button className="icon-btn" title="My Profile" onClick={() => navigate('/profile')}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d={I.user} /></svg>
        </button>
        <button className="icon-btn" title="Log out" onClick={() => { logout(); navigate('/login') }}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d={I.logout} /></svg>
        </button>
        {!isPsychRole && (
          <>
            <div className="rail-sep" />
            <button className="icon-btn lime pulse-crisis" title="Emergency SOS" onClick={triggerSelfCrisis}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d={I.alert} /></svg>
            </button>
          </>
        )}
      </nav>

      {/* ══ Top bar: schedule pill + bell + avatar ══ */}
      <div className="topbar">
        <div className="topbar-schedule">
          <span className="sched-label">{isPsychRole ? 'Your Caseload' : 'Your Schedule'}</span>
          <span className="sched-date">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d={I.calendar} /></svg>
            {new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'long' })}
          </span>
          {upcomingSessions.length > 0 ? upcomingSessions.map((b: any, i: number) => {
            const who = role === 'Psychologist'
              ? (patientNames[b.patient_username] || b.patient_username || 'Client')
              : (b.psychologist_username || 'your clinician')
            const when = b.date === todayStr() ? 'Today' : formatDate(b.date)
            return (
              <span key={i} className="sched-item" title={`${b.session_type || 'Session'} · ${when} at ${b.time} · ${who} · 60 min (${b.status})`}>
                🕒 {when} {b.time} · {who} · 60 min
              </span>
            )
          }) : (
            <span style={{ fontSize: '0.75rem', color: '#A6AC9D', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>            {isPsychRole
              ? `${patientCount} clients · ${pendingBookings} pending approvals`
              : role === 'Admin'
                ? `Clinic oversight · ${patientCount} clients`
                : 'No sessions booked today — breathe easy ✨'}
            </span>
          )}
          <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '8px', paddingRight: '6px' }}>
            {pendingSync > 0 && (
              <button className="chip" style={{ background: 'var(--lime)', border: 'none', color: 'var(--lime-ink)', fontWeight: 700 }}
                onClick={() => flushOutbox(api).then(() => getOutboxCount().then(setPendingSync)).catch(() => {})}>
                📡 {pendingSync} to sync
              </button>
            )}
          </div>
        </div>

        <div style={{ position: 'relative' }}>
          <button className="icon-btn" title="Notifications" onClick={() => setNotifOpen(o => !o)} style={{ background: 'var(--ink) !important', color: 'var(--on-ink) !important', borderColor: 'var(--ink) !important', position: 'relative' }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d={I.bell} /></svg>
            {unreadCount > 0 && <span className="notif-dot" />}
          </button>
          {notifPanel}
        </div>

        <div style={{ position: 'relative' }}>
          <button className="avatar" title={`${user?.name} · Profile`} onClick={() => navigate('/profile')}>{initials}</button>
        </div>
      </div>

      {/* ══ Crisis banner ══ */}
      {showCrisisBanner && (
        <div className="card" style={{ borderColor: 'var(--danger)', background: 'var(--danger-alpha)', marginBottom: '14px', padding: '14px 16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '6px', flexWrap: 'wrap' }}>
            <span style={{ color: 'var(--danger)', fontSize: '1.1rem', fontWeight: 800 }}>⏱️ {crisisElapsed >= 60 ? '60+' : crisisElapsed}s</span>
            <span style={{ color: CRISIS_STAGE_MESSAGES[crisisStage]?.color || 'var(--danger)', fontWeight: 700, fontSize: '0.85rem' }}>
              {CRISIS_STAGE_MESSAGES[crisisStage]?.text || '🔴 Crisis Active'}
            </span>
            <button className="btn-danger" style={{ marginLeft: 'auto', padding: '7px 14px', fontSize: '0.78rem' }} onClick={() => navigate('/crisis')}>
              Open Emergency Center
            </button>
          </div>
          <div style={{ display: 'flex', gap: '4px', marginTop: '8px', flexWrap: 'wrap' }}>
            {[
              { key: 'triggered', label: '🚨 Triggered', sec: 0 },
              { key: 'trustee_notified', label: '👤 Trusted Contact', sec: 30 },
              { key: 'helpline_escalated', label: '🏥 Helpline', sec: 60 },
            ].map(s => {
              const isActive = s.key === crisisStage || (crisisElapsed >= s.sec && crisisElapsed < (s.sec === 0 ? 30 : 999))
              const passed = crisisElapsed >= s.sec
              return (
                <div key={s.key} style={{
                  flex: 1, minWidth: '110px', textAlign: 'center', padding: '7px', borderRadius: '12px',
                  background: isActive ? 'rgba(214,69,58,0.15)' : passed ? 'var(--ok-alpha)' : 'var(--surface-soft)',
                  border: `1px solid ${isActive ? 'rgba(214,69,58,0.4)' : passed ? 'rgba(46,139,87,0.3)' : 'var(--border-soft)'}`,
                  color: isActive ? 'var(--danger)' : passed ? 'var(--ok)' : 'var(--faint)',
                  fontSize: '0.75rem', fontWeight: 700,
                }}>
                  {s.label}<br /><span style={{ fontSize: '0.625rem', fontWeight: 500 }}>{s.sec}s</span>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {bookingMsg && (
        <div className="card" style={{ borderColor: 'var(--warn)', marginBottom: '12px', padding: '10px 16px' }}>
          <span style={{ color: bookingMsg.color, fontSize: '0.8125rem', fontWeight: 600 }}>{bookingMsg.text}</span>
        </div>
      )}

      {/* ══ Page header ══ */}
      <div className="page-head" style={{ maxWidth: '1500px' }}>
        <div>
          <h1 className="page-title"><span className="title-dot" />{activeTab.label}</h1>
          <div className="page-sub">
            {isPsychRole
              ? <>Welcome back, {firstName} — {patientCount} clients in your care</>
              : <>Welcome back, {firstName}{user?.assigned_psych ? <> · cared for by <strong>{user.assigned_psych}</strong></> : null}</>}
          </div>
        </div>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
          {isPsychRole ? (
            <>
              <span className="badge-theme">🟢 {aiStatus?.any_available ? 'AI connected' : 'AI offline · rule mode'}</span>
              <span className="badge-theme">🚨 {crisisState?.active ? 'Crisis active' : 'No active crisis'}</span>
              <span className="badge-theme">⚠️ {highRiskCount} high-risk</span>
            </>
          ) : (
            <>
              <span className="badge-theme">📝 Journal: {journalOk}</span>
              <span className="badge-theme">😊 Mood: {todayMood}</span>
              <span className="badge-theme">📅 Next: {nextSession}</span>
            </>
          )}
        </div>
      </div>

      {/* ══ Sub-nav (segmented) ══ */}
      <div className="segmented-control" style={{ marginBottom: '22px', maxWidth: '100%' }}>
        {tabs.map(tab => (
          <button
            key={tab.to}
            className={`segmented-btn${activeTab.to === tab.to ? ' active' : ''}`}
            onClick={() => navigate(tab.to)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div style={{ maxWidth: '1500px' }}>
        {/* Keyed by pathname so the page-enter animation replays on every route change */}
        <div key={location.pathname} className="page-enter">
          <Outlet />
        </div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px', margin: '34px 0 8px', color: 'var(--faint)', fontSize: '0.72rem', flexWrap: 'wrap' }}>
          <span style={{ fontStyle: 'italic' }}>"{QUOTES[quoteIdx]}"</span>
        </div>
        {isPsychRole && crisisLog.length > 0 && (
          <div style={{ textAlign: 'center', color: 'var(--faint)', fontSize: '0.68rem', marginBottom: '8px' }}>
            Last crisis event: {crisisLog[crisisLog.length - 1]?.event} · {formatDateTime(crisisLog[crisisLog.length - 1]?.timestamp)}
          </div>
        )}
      </div>

      <OnboardingTour role={role} />
      <div style={{ position: 'fixed', top: '18px', right: '18px', zIndex: 9999, display: 'flex', flexDirection: 'column', gap: '8px', maxWidth: '340px' }}>
        {toasts.map(t => (
          <div key={t.key} onClick={() => dismissToast(t)} title="Click to dismiss"
            style={{
              background: 'var(--surface)', border: '1px solid var(--border)',
              borderLeft: `3px solid ${t.notification_type === 'crisis' ? 'var(--danger)' : 'var(--accent)'}`,
              borderRadius: '14px', padding: '11px 14px', cursor: 'pointer',
              boxShadow: 'var(--shadow-lg)', animation: 'slideIn 0.25s ease',
            }}>
            <div style={{ fontWeight: 700, fontSize: '0.8125rem', color: t.notification_type === 'crisis' ? 'var(--danger)' : 'var(--accent)' }}>{t.title}</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--secondary)', marginTop: '2px' }}>{t.message}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
