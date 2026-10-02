import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { getUser } from '../stores/auth'
import PatientSelector from '../components/PatientSelector'
import CustomSelect from '../components/CustomSelect'
import { useToast, useRipple } from '../components/fx'
import { formatDate, todayStr } from '../constants'

const STATUS_COLORS: Record<string, string> = { Approved: 'var(--ok)', Rejected: 'var(--danger)', Cancelled: 'var(--muted)', Pending: 'var(--accent)', Proposed: 'var(--warn)', Completed: 'var(--ok)' }
const STATUS_ICONS: Record<string, string> = { Approved: '✅', Rejected: '❌', Cancelled: '⚪', Pending: '⏳', Proposed: '💡', Completed: '🏁' }

export default function BookingsPage() {
  const user = getUser()
  const isPsych = user?.role === 'psychologist'

  if (isPsych) return <PsychBookings />
  return <PatientBookings />
}

function PatientBookings() {
  const toast = useToast()
  const [bookings, setBookings] = useState<any[]>([])
  const [tab, setTab] = useState(0)

  useEffect(() => { api.getBookings().then(d => setBookings(d || [])).catch(() => {}) }, [])

  const aiBookings = (bookings || []).filter((b: any) => b.explanation?.includes('AI-suggested'))
  const proposed = aiBookings.filter((b: any) => b.status === 'Proposed')
  const pastAi = aiBookings.filter((b: any) => b.status !== 'Proposed')

  async function handleAction(booking: any, action: string) {
    try {
      await api.updateBookingStatus(booking.id, action)
      const updated = await api.getBookings()
      setBookings(updated || [])
    } catch (err: any) { toast('error', err.message) }
  }

  return (
    <div className="animate-fade-in">
      {bookings.length > 0 && (() => {
        const latest = bookings[bookings.length - 1]
        if (latest.status === 'Approved') return <div className="card-sm" style={{ background: 'var(--ok-soft)', borderColor: 'color-mix(in srgb, var(--ok) 30%, transparent)', marginBottom: '12px' }}><span style={{ color: 'var(--ok)', fontWeight: 700, fontSize: '0.82rem' }}>✅ Your last request was approved. Details in your confirmation.</span></div>
        if (latest.status === 'Rejected') return <div className="card-sm" style={{ background: 'var(--danger-soft)', borderColor: 'color-mix(in srgb, var(--danger) 30%, transparent)', marginBottom: '12px' }}><span style={{ color: 'var(--danger)', fontWeight: 700, fontSize: '0.82rem' }}>❌ Your last request was declined — pick another slot below.</span></div>
        if (latest.status === 'Pending') return <div className="card-sm" style={{ background: 'var(--warn-soft)', borderColor: 'color-mix(in srgb, var(--warn) 30%, transparent)', marginBottom: '12px' }}><span style={{ color: 'var(--warn)', fontWeight: 700, fontSize: '0.82rem' }}>⏳ Your request is pending review by your clinician.</span></div>
        return null
      })()}

      <div className="segmented-control" data-tour="bookings">
        <button className={`segmented-btn${tab === 0 ? ' active' : ''}`} onClick={() => setTab(0)}>💡 Suggestions</button>
        <button className={`segmented-btn${tab === 1 ? ' active' : ''}`} onClick={() => setTab(1)}>📅 Book appointment</button>
        <button className={`segmented-btn${tab === 2 ? ' active' : ''}`} onClick={() => setTab(2)}>🗓️ My sessions</button>
      </div>

      {tab === 0 && (
        <div>
          {proposed.length > 0 ? (
            <>
              {proposed.map((b: any, i: number) => (
                <div key={i} className="lead-card lime" style={{ marginBottom: '10px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <div className="avatar-sm" style={{ background: 'rgba(0,0,0,0.12)' }}>💡</div>
                    <div>
                      <div style={{ fontWeight: 800, fontSize: '1.05rem' }}>{formatDate(b.date)} @ {b.time}</div>
                      <div style={{ fontSize: '0.72rem', opacity: 0.75 }}>Your psychologist recommended this slot</div>
                    </div>
                  </div>
                  <div style={{ fontSize: '0.78rem', opacity: 0.85 }}>{b.explanation}</div>
                  <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
                    <button className="btn-primary" onClick={() => handleAction(b, 'Approved')}>✅ Accept</button>
                    <button onClick={() => handleAction(b, 'Rejected')}>❌ Decline</button>
                  </div>
                </div>
              ))}
            </>
          ) : (
            <div className="card" style={{ textAlign: 'center', padding: '28px' }}>
              <div style={{ fontSize: '1.8rem', marginBottom: '6px' }}>📭</div>
              <div style={{ fontWeight: 700, marginBottom: '4px' }}>No suggestions right now</div>
              <div style={{ color: 'var(--muted)', fontSize: '0.8rem' }}>Your psychologist can propose sessions based on your journal and vitals.</div>
            </div>
          )}
          {pastAi.length > 0 && (
            <div style={{ marginTop: '16px' }}>
              <h3>History</h3>
              <div className="space-y-2">
                {pastAi.slice(-5).reverse().map((b: any, i: number) => (
                  <div key={i} className="card-stage" style={{ justifyContent: 'space-between' }}>
                    <span style={{ fontSize: '0.78rem', fontWeight: 600 }}>{STATUS_ICONS[b.status] || '⚪'} {formatDate(b.date)} @ {b.time}</span>
                    <span style={{ fontSize: '0.6875rem', color: STATUS_COLORS[b.status] || 'var(--muted)', fontWeight: 700 }}>{b.status}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {tab === 1 && <PatientBookingForm />}
      {tab === 2 && <PatientSessions onAction={handleAction} />}
    </div>
  )
}

function PatientSessions({ onAction }: { onAction: (booking: any, action: string) => void }) {
  const toast = useToast()
  const [bookings, setBookings] = useState<any[]>([])
  const [rescheduling, setRescheduling] = useState<number | null>(null)
  const [rsDate, setRsDate] = useState('')
  const [rsTime, setRsTime] = useState('10:00')

  useEffect(() => { api.getBookings().then(d => setBookings(d || [])).catch(() => {}) }, [])

  const mine = (bookings || []).filter((b: any) => b.status !== 'Proposed')
  const upcoming = mine.filter((b: any) => b.date >= todayStr() && ['Pending', 'Approved'].includes(b.status))
  const history = mine.filter((b: any) => !(b.date >= todayStr() && ['Pending', 'Approved'].includes(b.status)))

  async function reschedule(id: number) {
    try {
      await api.rescheduleBooking(id, rsDate, rsTime)
      setRescheduling(null)
      setBookings((await api.getBookings()) || [])
    } catch (err: any) { toast('error', err.message) }
  }

  function row(b: any) {
    return (
      <div key={b.id} className="card-stage" style={{ flexDirection: 'column', alignItems: 'stretch', gap: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.85rem', fontWeight: 700 }}>{STATUS_ICONS[b.status] || '○'} {formatDate(b.date)} @ {b.time}</span>
          <span className="badge-theme" style={{ color: STATUS_COLORS[b.status], fontWeight: 700 }}>{b.status}</span>
          {b.session_type && <span style={{ fontSize: '0.68rem', color: 'var(--muted)' }}>{b.session_type}</span>}
        </div>
        {b.explanation && !b.explanation.includes('AI-suggested') && (
          <div style={{ fontSize: '0.74rem', color: 'var(--muted)', lineHeight: 1.5 }}>{b.explanation}</div>
        )}
        {['Pending', 'Approved'].includes(b.status) && (
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {b.status === 'Approved' && (
              <button style={{ fontSize: '0.72rem', padding: '4px 12px' }} onClick={() => window.open(`/api/bookings/${b.id}/ics`, '_blank')} title="Add to your calendar app">
                📥 Add to calendar
              </button>
            )}
            <button className="btn-danger" style={{ fontSize: '0.72rem', padding: '4px 12px' }} onClick={() => onAction(b, 'Cancelled')}>Cancel session</button>
            <button style={{ fontSize: '0.72rem', padding: '4px 12px' }} onClick={() => { setRescheduling(rescheduling === b.id ? null : b.id); setRsDate(b.date); setRsTime(b.time) }}>🔁 Reschedule</button>
          </div>
        )}
        {rescheduling === b.id && (
          <div className="card-sm" style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap', background: 'var(--accent-soft)' }}>
            <strong style={{ fontSize: '0.75rem' }}>Move to:</strong>
            <input type="date" value={rsDate} onChange={e => setRsDate(e.target.value)} style={{ width: '150px' }} />
            <input type="time" value={rsTime} onChange={e => setRsTime(e.target.value)} style={{ width: '110px' }} />
            <button className="btn-primary" style={{ fontSize: '0.75rem', padding: '4px 12px' }} onClick={() => reschedule(b.id)}>Confirm</button>
            <button style={{ fontSize: '0.75rem', padding: '4px 12px' }} onClick={() => setRescheduling(null)}>Cancel</button>
          </div>
        )}
      </div>
    )
  }

  return (
    <div>
      {upcoming.length > 0 ? (
        <>
          <h3 style={{ marginBottom: '8px' }}>⏭️ Upcoming ({upcoming.length})</h3>
          <div className="space-y-2">{upcoming.map(row)}</div>
        </>
      ) : (
        <div className="card" style={{ textAlign: 'center', padding: '24px' }}>
          <div style={{ fontSize: '1.6rem', marginBottom: '4px' }}>🗓️</div>
          <div style={{ fontWeight: 700 }}>No upcoming sessions</div>
          <div style={{ color: 'var(--muted)', fontSize: '0.8rem' }}>Request one from the “Book appointment” tab.</div>
        </div>
      )}
      {history.length > 0 && (
        <>
          <h3 style={{ margin: '16px 0 8px' }}>🗃️ History</h3>
          <div className="space-y-2">{history.slice(-8).reverse().map(row)}</div>
        </>
      )}
    </div>
  )
}

function PatientBookingForm() {
  const toast = useToast()
  const [psychs, setPsychs] = useState<any[]>([])
  const [selectedPsych, setSelectedPsych] = useState('')
  const [availableDates, setAvailableDates] = useState<{ date: string; start: string; end: string }[]>([])
  const [selectedDate, setSelectedDate] = useState('')
  const [time, setTime] = useState('10:00')
  const [sessionType, setSessionType] = useState('Therapy')
  const [memberCount, setMemberCount] = useState(1)
  const [members, setMembers] = useState<{ name: string; age: number }[]>([{ name: '', age: 16 }])
  const [contact, setContact] = useState('')
  const [context, setContext] = useState('')
  const [saving, setSaving] = useState(false)
  const [done, setDone] = useState(false)
  const [submitError, setSubmitError] = useState('')
  const [freeSlots, setFreeSlots] = useState<{ date: string; time: string }[]>([])

  useEffect(() => {
    api.getAvailablePsychs().then(d => setPsychs(d || [])).catch(() => {})
  }, [])

  useEffect(() => {
    if (!selectedPsych) { setAvailableDates([]); return }
    api.get(`/psychologists/${selectedPsych}/availability`).then((dates: any[]) => {
      setAvailableDates((dates || []).map((d: any) => ({ date: d.date, start: d.start || '09:00', end: d.end || '17:00' })))
    }).catch(() => {})
  }, [selectedPsych])

  const activeWindow = availableDates.find(d => d.date === selectedDate)

  useEffect(() => {
    setMembers(Array.from({ length: memberCount }, (_, i) => members[i] || { name: '', age: 16 }))
  }, [memberCount])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!selectedPsych || !selectedDate || !contact.trim() || !context.trim() || members.some(m => !m.name.trim())) {
      toast('error', 'Please fill all required fields.')
      return
    }
    if (activeWindow && (time < activeWindow.start || time > activeWindow.end)) {
      toast('error', `Please pick a time within your clinician's hours that day (${activeWindow.start}–${activeWindow.end}).`)
      return
    }
    setSaving(true)
    try {
      await api.createBooking({
        patient: getUser()?.username,
        psychologist_username: selectedPsych,
        date: selectedDate,
        time,
        session_type: sessionType,
        members: members.map(m => `${m.name.trim()} (${m.age})`).join('; '),
        contact: contact.trim(),
        explanation: context.trim(),
      })
      setDone(true)
    } catch (err: any) {
      // Conflict (409) or outside-hours (400): show it and offer free slots
      setSubmitError(err.message || 'Could not submit request')
      if (selectedPsych) {
        api.getNextFreeSlots(selectedPsych, 4)
          .then((d: any) => setFreeSlots(d?.free_slots || []))
          .catch(() => setFreeSlots([]))
      }
    }
    setSaving(false)
  }

  if (done) {
    return (
      <div className="card-lime" style={{ padding: '36px', textAlign: 'center' }}>
        <div style={{ fontSize: '2.4rem' }}>🎉</div>
        <h2 style={{ color: 'var(--lime-ink) !important', margin: '8px 0 4px' }}>Request sent!</h2>
        <p style={{ opacity: 0.8, fontSize: '0.85rem' }}>Your clinician will review and confirm shortly. You'll get a notification here.</p>
        <button className="btn-primary" style={{ marginTop: '14px' }} onClick={() => { setDone(false) }}>Book another</button>
      </div>
    )
  }

  return (
    <div className="card" style={{ padding: '24px', maxWidth: '640px' }}>
      <h3 style={{ marginBottom: '16px' }}>📅 Request a session</h3>

      <div className="space-y-4">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
          <div>
            <label>Psychologist</label>
            <CustomSelect
              value={selectedPsych}
              onChange={setSelectedPsych}
              placeholder="Select psychologist…"
              options={psychs.map((p: any) => ({ value: p.username || p, label: p.name || p }))}
            />
          </div>
          <div>
            <label>Available dates</label>
            {availableDates.length > 0 ? (
              <CustomSelect
                value={selectedDate}
                onChange={v => { setSelectedDate(v); setTime('') }}
                placeholder="Select a date…"
                options={availableDates.map(d => ({
                  value: d.date,
                  label: `${new Date(d.date + 'T00:00:00').toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })} · ${d.start}–${d.end}`,
                }))}
              />
            ) : (
              <div style={{ color: 'var(--muted)', fontSize: '0.8rem', padding: '12px 0' }}>Pick a psychologist to see their open dates.</div>
            )}
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
          <div>
            <label>Time {activeWindow && <span style={{ fontWeight: 500, color: 'var(--muted)', fontSize: '0.68rem' }}>({activeWindow.start}–{activeWindow.end})</span>}</label>
            <input
              type="time"
              value={time}
              min={activeWindow?.start || undefined}
              max={activeWindow?.end || undefined}
              onChange={e => setTime(e.target.value)}
            />
            {activeWindow && time && (time < activeWindow.start || time > activeWindow.end) && (
              <div style={{ color: 'var(--danger)', fontSize: '0.68rem', fontWeight: 600, marginTop: '4px' }}>
                Outside their hours ({activeWindow.start}–{activeWindow.end})
              </div>
            )}
          </div>
          <div>
            <label>Type</label>
            <CustomSelect
              value={sessionType}
              onChange={setSessionType}
              options={['Therapy', 'Follow-up', 'Crisis Check-in', 'Mindfulness'].map(t => ({ value: t, label: t }))}
            />
          </div>
          <div>
            <label>Attendees</label>
            <input type="number" min={1} max={6} value={memberCount} onChange={e => setMemberCount(Number(e.target.value))} />
          </div>
        </div>

        <div>
          <label>Member details</label>
          {members.map((m, i) => (
            <div key={i} style={{ display: 'flex', gap: '10px', marginBottom: '8px' }}>
              <div style={{ flex: 3 }}>
                <input value={m.name} onChange={e => {
                  const next = [...members]; next[i] = { ...next[i], name: e.target.value }; setMembers(next)
                }} placeholder={`Member ${i + 1} full name`} />
              </div>
              <div style={{ flex: 1 }}>
                <input type="number" min={0} max={120} value={m.age} onChange={e => {
                  const next = [...members]; next[i] = { ...next[i], age: Number(e.target.value) }; setMembers(next)
                }} placeholder="Age" />
              </div>
            </div>
          ))}
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '12px' }}>
          <div>
            <label>Contact (phone / email)</label>
            <input value={contact} onChange={e => setContact(e.target.value)} placeholder="You or guardian" />
          </div>
          <div>
            <label>Goal for this session</label>
            <textarea value={context} onChange={e => setContext(e.target.value)} placeholder="Briefly describe what you'd like to work on." rows={3} />
          </div>
        </div>

        {submitError && (
          <div style={{ background: 'var(--danger-soft)', border: '1px solid color-mix(in srgb, var(--danger) 30%, transparent)', borderRadius: 12, padding: '10px 14px', color: 'var(--danger)', fontWeight: 700, fontSize: '0.8rem' }}>
            ⚠️ {submitError}
          </div>
        )}

        {submitError && freeSlots.length > 0 && (
          <div className="card-sm" style={{ background: 'var(--accent-soft)', borderColor: 'color-mix(in srgb, var(--accent) 25%, transparent)' }}>
            <div style={{ fontSize: '0.75rem', fontWeight: 800, color: 'var(--accent)', marginBottom: '6px' }}>🤖 Next free times with this clinician:</div>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              {freeSlots.map(s => (
                <button
                  key={`${s.date}T${s.time}`}
                  className="chip"
                  onClick={() => { setSelectedDate(s.date); setTime(s.time); setSubmitError(''); setFreeSlots([]) }}
                >
                  {new Date(s.date + 'T00:00:00').toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })} · {s.time}
                </button>
              ))}
            </div>
            <div style={{ fontSize: '0.66rem', color: 'var(--muted)', marginTop: '6px' }}>Tap one to fill the form, then submit again.</div>
          </div>
        )}

        <button className="btn-primary" onClick={handleSubmit} disabled={saving} style={{ width: '100%', padding: '12px' }}>
          {saving ? 'Submitting…' : 'Submit request'}
        </button>
      </div>
    </div>
  )
}

/* ──── Psychologist Bookings ──── */

function PsychBookings() {
  const [tab, setTab] = useState(0)

  return (
    <div className="animate-fade-in">
      <div style={{ display: 'grid', gridTemplateColumns: '3fr 1fr', gap: '20px', alignItems: 'start' }} className="psych-bookings-grid">
        <div>
          <div className="segmented-control" data-tour="psych-bookings">
            <button className={`segmented-btn${tab === 0 ? ' active' : ''}`} onClick={() => setTab(0)}>📅 Availability</button>
            <button className={`segmented-btn${tab === 1 ? ' active' : ''}`} onClick={() => setTab(1)}>📋 Request queue</button>
          </div>
          {tab === 0 && <PsychCalendar />}
          {tab === 1 && <PsychQueue />}
        </div>
        <div>
          <PsychBookingAgent />
        </div>
      </div>
      <style>{`@media (max-width: 1100px) { .psych-bookings-grid { grid-template-columns: 1fr !important; } }`}</style>
    </div>
  )
}

function PsychCalendar() {
  const toast = useToast()
  const today = new Date()
  const [year, setYear] = useState(today.getFullYear())
  const [month, setMonth] = useState(today.getMonth() + 1)
  const [slots, setSlots] = useState<Record<string, { start_time: string; end_time: string }>>({})
  const [sessions, setSessions] = useState<Record<string, any[]>>({})
  const [editing, setEditing] = useState<string>('')
  const [winStart, setWinStart] = useState('09:00')
  const [winEnd, setWinEnd] = useState('17:00')
  const [removing, setRemoving] = useState(false)
  const [bulkOpen, setBulkOpen] = useState(false)
  const [bulkDays, setBulkDays] = useState<string[]>(['1', '3', '5'])
  const [bulkWeeks, setBulkWeeks] = useState(4)
  const [bulkStart, setBulkStart] = useState('09:00')
  const [bulkEnd, setBulkEnd] = useState('17:00')

  async function loadSlots() {
    try {
      const d = await api.getMyAvailability(true)
      const map: Record<string, { start_time: string; end_time: string }> = {}
      ;(d || []).forEach((s: any) => { map[s.date] = { start_time: s.start_time, end_time: s.end_time } })
      setSlots(map)
    } catch {}
    try {
      const cal = await api.getBookingCalendar(year, month)
      const map: Record<string, any[]> = {}
      ;(cal?.sessions || []).forEach((s: any) => { map[s.date] = s.bookings })
      setSessions(map)
    } catch {}
  }

  useEffect(() => { loadSlots() }, [year, month])

  const daysInMonth = new Date(year, month, 0).getDate()
  const firstDay = new Date(year, month - 1, 1).getDay()
  const weekday = firstDay === 0 ? 6 : firstDay - 1

  const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
  const avail = Object.keys(slots)

  async function toggleDate(d: number) {
    const ds = `${year}-${String(month).padStart(2, '0')}-${String(d).padStart(2, '0')}`
    try {
      if (slots[ds]) {
        await api.delete(`/bookings/availability/date/${ds}`)
        setSlots(prev => { const n = { ...prev }; delete n[ds]; return n })
        toast('info', `Availability removed for ${ds}`)
      } else {
        await api.post('/bookings/availability', { date: ds, start_time: winStart, end_time: winEnd })
        setSlots(prev => ({ ...prev, [ds]: { start_time: winStart, end_time: winEnd } }))
        toast('success', `Opened ${ds} ${winStart}–${winEnd}`)
      }
    } catch (err: any) { toast('error', err.message || 'Could not update availability') }
  }

  async function saveWindow(ds: string) {
    try {
      await api.post('/bookings/availability', { date: ds, start_time: winStart, end_time: winEnd })
      setSlots(prev => ({ ...prev, [ds]: { start_time: winStart, end_time: winEnd } }))
      setEditing('')
      toast('success', `Hours updated for ${ds}`)
    } catch (err: any) { toast('error', err.message || 'Could not save hours') }
  }

  async function removeDay(ds: string) {
    if (removing) return
    setRemoving(true)
    try {
      await api.delete(`/bookings/availability/date/${ds}`)
      setSlots(prev => { const n = { ...prev }; delete n[ds]; return n })
      setEditing('')
      toast('success', `Availability removed for ${ds}`)
    } catch (err: any) {
      toast('error', err.message || 'Could not remove availability')
    } finally {
      setRemoving(false)
    }
  }

  async function bulkAdd() {
    try {
      const start = new Date(today.getFullYear(), today.getMonth(), today.getDate())
      const added: Record<string, { start_time: string; end_time: string }> = {}
      for (let w = 0; w < bulkWeeks; w++) {
        for (const day of bulkDays) {
          const d = new Date(start)
          d.setDate(start.getDate() + w * 7 + (Number(day) - start.getDay() + 7) % 7 || (Number(day) === start.getDay() ? 0 : 7))
          // simpler: find next occurrence of weekday within w weeks
          const target = new Date(start)
          const delta = (Number(day) - start.getDay() + 7) % 7 || 7
          target.setDate(start.getDate() + delta + w * 7)
          const ds = `${target.getFullYear()}-${String(target.getMonth() + 1).padStart(2, '0')}-${String(target.getDate()).padStart(2, '0')}`
          if (!slots[ds]) {
            await api.post('/bookings/availability', { date: ds, start_time: bulkStart, end_time: bulkEnd })
            added[ds] = { start_time: bulkStart, end_time: bulkEnd }
          }
        }
      }
      setSlots(prev => ({ ...prev, ...added }))
      setBulkOpen(false)
    } catch {}
  }

  const weekdayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

  return (
    <div className="card" style={{ padding: '22px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px', flexWrap: 'wrap', gap: '10px' }}>
        <h3 style={{ margin: 0 }}>Open dates ({avail.length})</h3>
        <div style={{ display: 'flex', gap: '8px' }}>
          <CustomSelect
            value={String(month)}
            onChange={v => setMonth(Number(v))}
            style={{ width: '140px' }}
            options={months.map((m, i) => ({ value: String(i + 1), label: m }))}
          />
          <CustomSelect
            value={String(year)}
            onChange={v => setYear(Number(v))}
            style={{ width: '100px' }}
            options={[today.getFullYear() - 1, today.getFullYear(), today.getFullYear() + 1, today.getFullYear() + 2].map(y => ({ value: String(y), label: String(y) }))}
          />
        </div>
      </div>

      <div className="cal-wrap">
        {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map(d => (
          <div key={d} className="cal-hdr">{d}</div>
        ))}
        {Array.from({ length: weekday }).map((_, i) => <div key={`e${i}`}></div>)}
        {Array.from({ length: daysInMonth }, (_, i) => i + 1).map(d => {
          const ds = `${year}-${String(month).padStart(2, '0')}-${String(d).padStart(2, '0')}`
          const slot = slots[ds]
          const isAvail = !!slot
          const isPast = new Date(year, month - 1, d) < new Date(today.getFullYear(), today.getMonth(), today.getDate())
          const isToday = year === today.getFullYear() && month === today.getMonth() + 1 && d === today.getDate()
          let cls = 'cal-cell'
          if (isPast) cls += ' cal-past'
          else if (isAvail) cls += ' cal-avail'
          else if (isToday) cls += ' cal-today'
          else cls += ' cal-day'
          return (
            <div
              key={d}
              className={cls}
              title={slot ? `${slot.start_time}–${slot.end_time}` : undefined}
              style={{ cursor: isPast ? 'default' : 'pointer', position: 'relative', fontSize: '0.72rem', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '1px' }}
              onClick={() => {
                if (isPast) return
                if (slot) { setEditing(editing === ds ? '' : ds); setWinStart(slot.start_time); setWinEnd(slot.end_time) }
                else toggleDate(d)
              }}
            >
              <span>{d}</span>
              {slot && <span style={{ fontSize: '0.5rem', fontWeight: 700, opacity: 0.85 }}>{slot.start_time}</span>}
              {(sessions[ds] || []).length > 0 && (
                <span
                  title={(sessions[ds] || []).map((b: any) => `${b.time} ${b.patient} (${b.status})`).join('\n')}
                  style={{ fontSize: '0.48rem', fontWeight: 800, background: 'var(--danger)', color: 'white', borderRadius: 999, padding: '0 4px', minWidth: 12 }}
                >
                  {sessions[ds].length}
                </span>
              )}
            </div>
          )
        })}
      </div>

      {editing && slots[editing] && (
        <div className="card-sm" style={{ marginTop: '10px', display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap', background: 'var(--accent-soft)' }}>
          <strong style={{ fontSize: '0.78rem' }}>🕐 {editing}</strong>
          <input type="time" value={winStart} onChange={e => setWinStart(e.target.value)} style={{ width: '110px' }} />
          <span style={{ color: 'var(--muted)' }}>→</span>
          <input type="time" value={winEnd} onChange={e => setWinEnd(e.target.value)} style={{ width: '110px' }} />
          <button className="btn-primary" style={{ fontSize: '0.75rem', padding: '5px 12px' }} onClick={() => saveWindow(editing)}>Save window</button>
          <button
            className="btn-danger"
            style={{ fontSize: '0.75rem', padding: '5px 12px' }}
            disabled={removing}
            title="Close this date — clients can no longer book it"
            onClick={() => removeDay(editing)}
          >
            {removing ? 'Removing…' : '✕ Remove availability'}
          </button>
          <button style={{ fontSize: '0.75rem' }} onClick={() => setEditing('')}>Cancel</button>
        </div>
      )}

      <div style={{ display: 'flex', gap: '12px', fontSize: '0.75rem', marginTop: '12px', color: 'var(--muted)', flexWrap: 'wrap', alignItems: 'center' }}>
        <span><span className="dot tier-stable" style={{ display: 'inline-block', marginRight: '5px', verticalAlign: 'middle', background: 'var(--lime)', border: '1px solid var(--lime-deep)' }}></span> Open ({avail.length})</span>
        <span>Tap an open date to edit its hours or remove it · tap a closed date to open it</span>
        <span><span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: 999, background: 'var(--danger)', marginRight: 4, verticalAlign: 'middle' }} />booked sessions (hover for detail)</span>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginLeft: 'auto' }}>
          <span>Default for new dates:</span>
          <input type="time" value={winStart} onChange={e => setWinStart(e.target.value)} style={{ width: '100px', fontSize: '0.72rem' }} />
          <span>→</span>
          <input type="time" value={winEnd} onChange={e => setWinEnd(e.target.value)} style={{ width: '100px', fontSize: '0.72rem' }} />
        </div>
      </div>

      <button style={{ fontSize: '0.78rem', marginTop: '12px' }} onClick={() => setBulkOpen(!bulkOpen)}>
        ⚡ Bulk-open repeating weekdays
      </button>
      {bulkOpen && (
        <div className="card-sm" style={{ marginTop: '8px', display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
            {weekdayNames.map((wn, i) => (
              <button key={wn} className={`chip${bulkDays.includes(String(i)) ? ' active' : ''}`} onClick={() => setBulkDays(prev => prev.includes(String(i)) ? prev.filter(x => x !== String(i)) : [...prev, String(i)])}>{wn}</button>
            ))}
          </div>
          <label style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>
            for
            <input type="number" min={1} max={12} value={bulkWeeks} onChange={e => setBulkWeeks(Number(e.target.value))} style={{ width: '56px', margin: '0 6px' }} />
            weeks
          </label>
          <input type="time" value={bulkStart} onChange={e => setBulkStart(e.target.value)} style={{ width: '100px' }} />
          <span style={{ color: 'var(--muted)' }}>→</span>
          <input type="time" value={bulkEnd} onChange={e => setBulkEnd(e.target.value)} style={{ width: '100px' }} />
          <button className="btn-primary" style={{ fontSize: '0.75rem', padding: '6px 14px' }} onClick={bulkAdd} disabled={bulkDays.length === 0}>
            Add {bulkDays.length * bulkWeeks} dates
          </button>
        </div>
      )}
    </div>
  )
}

function PsychQueue() {
  const toast = useToast()
  const [bookings, setBookings] = useState<any[]>([])
  const [expanded, setExpanded] = useState<Record<number, boolean>>({})
  const [statusFilter, setStatusFilter] = useState('All')
  const [query, setQuery] = useState('')
  const [rescheduling, setRescheduling] = useState<number | null>(null)
  const [rsDate, setRsDate] = useState('')
  const [rsTime, setRsTime] = useState('10:00')

  useEffect(() => { api.getBookings().then(d => setBookings(d || [])).catch(() => {}) }, [])

  const shown = (bookings || [])
    .filter((b: any) => statusFilter === 'All' || b.status === statusFilter)
    .filter((b: any) => !query || (b.patient_username || '').toLowerCase().includes(query.toLowerCase()))

  async function updateStatus(id: number, status: string) {
    try {
      await api.updateBookingStatus(id, status)
      const updated = await api.getBookings()
      setBookings(updated || [])
    } catch {}
  }

  if (bookings.length === 0) {
    return (
      <div className="card" style={{ textAlign: 'center', padding: '30px' }}>
        <div style={{ fontSize: '1.8rem', marginBottom: '6px' }}>🧘</div>
        <div style={{ fontWeight: 700 }}>Queue is clear</div>
        <div style={{ color: 'var(--muted)', fontSize: '0.8rem' }}>No pending requests right now.</div>
      </div>
    )
  }

  return (
    <div>
      {/* Filters */}
      <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '12px', flexWrap: 'wrap' }}>
        {['All', 'Pending', 'Approved', 'Proposed', 'Rejected', 'Cancelled'].map(s => (
          <button key={s} className={`chip${statusFilter === s ? ' active' : ''}`} onClick={() => setStatusFilter(s)}>
            {s}{s !== 'All' ? ` (${bookings.filter((b: any) => b.status === s).length})` : ` (${bookings.length})`}
          </button>
        ))}
        <input placeholder="🔍 Client…" value={query} onChange={e => setQuery(e.target.value)} style={{ marginLeft: 'auto', width: '140px', borderRadius: 999, fontSize: '0.8rem' }} />
      </div>

      <div className="space-y-2">
      {shown.map((item: any, idx: number) => {
        const s = item.status
        const icon = STATUS_ICONS[s] || '○'
        const open = expanded[idx]
        return (
          <div key={item.id} className="expander" style={{ borderColor: s === 'Pending' ? 'color-mix(in srgb, var(--warn) 45%, transparent)' : 'var(--border)' }}>
            <div className="expander-header" onClick={() => setExpanded({ ...expanded, [idx]: !open })}>
              <span style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
                <span>{icon}</span>
                <strong>{item.patient_username}</strong>
                <span style={{ color: 'var(--muted)', fontSize: '0.75rem', fontWeight: 500 }}>{formatDate(item.date)} @ {item.time}</span>
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span className="badge-theme" style={{ color: STATUS_COLORS[s], borderColor: STATUS_COLORS[s] }}>{s}</span>
                {open ? '▲' : '▼'}
              </span>
            </div>
            {open && (
              <div className="expander-body">
                <div className="space-y-2" style={{ fontSize: '0.82rem' }}>
                  <div><strong>Session:</strong> {item.session_type || 'Therapy'}</div>
                  <div><strong>Members:</strong> {item.members || 'N/A'}</div>
                  <div><strong>Contact:</strong> {item.contact || 'N/A'}</div>
                  <div className="card-sm" style={{ padding: '10px 12px' }}><strong>Reason:</strong> {item.explanation || 'N/A'}</div>

                  {s === 'Cancelled' && (
                    <div className="card-sm" style={{ background: 'var(--danger-soft)', borderColor: 'color-mix(in srgb, var(--danger) 30%, transparent)' }}>
                      <span style={{ color: 'var(--danger)', fontWeight: 600 }}>❌ The client cancelled this slot.</span>
                    </div>
                  )}
                  {s === 'Pending' && (
                    <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
                      <button className="btn-primary" onClick={() => updateStatus(item.id, 'Approved')}>✅ Approve</button>
                      <button className="btn-danger" onClick={() => updateStatus(item.id, 'Rejected')}>❌ Reject</button>
                      <button onClick={() => { setRescheduling(rescheduling === item.id ? null : item.id); setRsDate(item.date); setRsTime(item.time) }}>🔁 Reschedule</button>
                    </div>
                  )}
                  {s === 'Approved' && item.date >= todayStr() && (
                    <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
                      <button onClick={() => updateStatus(item.id, 'Completed')}>🏁 Mark completed</button>
                      <button onClick={() => updateStatus(item.id, 'Cancelled')}>Cancel</button>
                      <button onClick={() => { setRescheduling(rescheduling === item.id ? null : item.id); setRsDate(item.date); setRsTime(item.time) }}>🔁 Reschedule</button>
                    </div>
                  )}
                  {rescheduling === item.id && (
                    <div className="card-sm" style={{ marginTop: '8px', display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap', background: 'var(--accent-soft)' }}>
                      <strong style={{ fontSize: '0.75rem' }}>Move to:</strong>
                      <input type="date" value={rsDate} onChange={e => setRsDate(e.target.value)} style={{ width: '150px' }} />
                      <input type="time" value={rsTime} onChange={e => setRsTime(e.target.value)} style={{ width: '110px' }} />
                      <button
                        className="btn-primary"
                        style={{ fontSize: '0.75rem', padding: '5px 12px' }}
                        onClick={async () => {
                          try {
                            await api.rescheduleBooking(item.id, rsDate, rsTime)
                            setRescheduling(null)
                            setBookings((await api.getBookings()) || [])
                          } catch (err: any) { toast('error', err.message) }
                        }}
                      >Confirm move</button>
                      <button style={{ fontSize: '0.75rem' }} onClick={() => setRescheduling(null)}>Cancel</button>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )
      })}
      </div>
      {shown.length === 0 && (
        <div className="card-sm" style={{ textAlign: 'center', padding: '18px', color: 'var(--muted)' }}>No bookings match these filters.</div>
      )}
    </div>
  )
}

function PsychBookingAgent() {
  const toast = useToast()
  const [patients, setPatients] = useState<any[]>([])
  const [selected, setSelected] = useState('')
  const [agentResult, setAgentResult] = useState<any>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => { api.getPsychPatients().then(d => setPatients(d || [])).catch(() => {}) }, [])

  async function analyze() {
    if (!selected) return
    setBusy(true)
    try {
      const result = await api.suggestSlots(selected)
      setAgentResult(result)
    } catch {} finally { setBusy(false) }
  }

  async function proposeSlot(slot: any) {
    try {
      await api.createBooking({
        psychologist_username: getUser()?.username,
        patient_username: selected,
        date: slot.date,
        time: slot.time || '10:00',
        session_type: 'Therapy',
        members: '1',
        contact: '',
        explanation: 'AI-suggested booking',
      })
      toast('success', 'Booking proposed — waiting for client to confirm.')
      setAgentResult(null)
    } catch (err: any) { toast('error', err.message) }
  }

  return (
    <div className="psych-box">
      <div className="psych-box-title">🤖 Booking agent</div>
      <div className="psych-box-desc">AI ranks slots by client urgency and workload</div>
      <PatientSelector patients={patients} value={selected} onChange={setSelected} placeholder="Select client…" style={{ marginBottom: '8px' }} />
      <button onClick={analyze} disabled={!selected || busy} className="btn-primary" style={{ width: '100%', fontSize: '0.8125rem' }}>
        {busy ? 'Analyzing…' : '🤖 Analyze & suggest slots'}
      </button>

      {agentResult && (
        <div className="ai-box" style={{ marginTop: '10px' }}>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', fontSize: '0.75rem', marginBottom: '6px' }}>
            <span className="badge-theme">Priority: <strong>{agentResult.priority}</strong></span>
            <span className="badge-theme">Urgency: <strong>{agentResult.urgency_score}/10</strong></span>
          </div>
          <div style={{ color: 'var(--muted)', fontSize: '0.6875rem', marginBottom: '8px' }}>{agentResult.reasoning}</div>
          {agentResult.suggested_slots?.map((s: any, i: number) => (
            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '7px 0', borderTop: '1px solid var(--border)' }}>
              <span style={{ color: 'var(--accent)', fontSize: '0.8125rem', fontWeight: 700 }}>{s.label}</span>
              <button className="btn-lime" style={{ fontSize: '0.6875rem', padding: '4px 12px' }} onClick={() => proposeSlot(s)}>Propose</button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
