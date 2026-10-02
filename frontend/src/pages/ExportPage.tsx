import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { getUser } from '../stores/auth'
import { formatDate } from '../constants'

export default function ExportPage() {
  const user = getUser()
  const isPsych = user?.role === 'psychologist'
  const [mode, setMode] = useState<'patients' | 'myself'>('patients')
  const [patients, setPatients] = useState<any[]>([])
  const [selectedPatient, setSelectedPatient] = useState('')
  const [entries, setEntries] = useState<any[]>([])
  const [notes, setNotes] = useState<any[]>([])
  const [ownJournals, setOwnJournals] = useState<any[]>([])
  const [expandedEntries, setExpandedEntries] = useState<Record<string, boolean>>({})
  const [expandedNotes, setExpandedNotes] = useState<Record<string, boolean>>({})
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  useEffect(() => {
    if (isPsych) {
      api.getPsychPatients().then(setPatients).catch(() => {})
    }
  }, [isPsych])

  useEffect(() => {
    if (mode === 'myself') {
      api.getPsychJournals().then(setOwnJournals).catch(() => setOwnJournals([]))
    }
  }, [mode])

  useEffect(() => {
    if (!selectedPatient) { setEntries([]); setNotes([]); return }
    api.getPatientSummaries(selectedPatient).then((d: any) => setEntries(Array.isArray(d) ? d : [])).catch(() => setEntries([]))
    api.get(`/psychologists/notes?patient=${selectedPatient}`).then((d: any) => setNotes(Array.isArray(d) ? d : [])).catch(() => setNotes([]))
  }, [selectedPatient])

  function downloadCsv(filename: string, rows: string[][]) {
    const csv = rows.map(r => r.map(c => `"${c.replace(/"/g, '""')}"`).join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = filename; a.click()
    URL.revokeObjectURL(url)
  }

  function filterByDate(items: any[]): any[] {
    if (!dateFrom && !dateTo) return items
    return items.filter((e: any) => {
      const ts = (e.timestamp || '').slice(0, 10)
      if (!ts) return true
      if (dateFrom && ts < dateFrom) return false
      if (dateTo && ts > dateTo) return false
      return true
    })
  }

  const filteredEntries = filterByDate(entries)
  const filteredNotes = filterByDate(notes)
  const filteredOwn = filterByDate(ownJournals)

  function toggleExpand(setter: any, key: string) {
    setter((prev: any) => ({ ...prev, [key]: !prev[key] }))
  }

  return (
    <div className="space-y-4 animate-fade-in">
      <div className="segmented-control" data-tour="export">
        <button className={`segmented-btn${mode === 'patients' ? ' active' : ''}`} onClick={() => setMode('patients')}>👥 Clients</button>
        <button className={`segmented-btn${mode === 'myself' ? ' active' : ''}`} onClick={() => setMode('myself')}>🧑 Me</button>
      </div>

      <div className="card-sm" style={{ display: 'flex', gap: '12px', alignItems: 'center', padding: '14px 18px', flexWrap: 'wrap' }}>
        <span style={{ color: 'var(--muted)', fontSize: '0.8rem', fontWeight: 700 }}>📅 Filter:</span>
        <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} style={{ width: '160px' }} />
        <span style={{ color: 'var(--faint)', fontSize: '0.75rem' }}>to</span>
        <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} style={{ width: '160px' }} />
        {(dateFrom || dateTo) && (
          <button className="btn-ghost" onClick={() => { setDateFrom(''); setDateTo('') }} style={{ fontSize: '0.75rem' }}>Clear</button>
        )}
        <span style={{ marginLeft: 'auto', fontSize: '0.7rem', color: 'var(--faint)', fontWeight: 600 }}>
          {mode === 'patients' ? `${filteredEntries.length} entries · ${filteredNotes.length} notes` : `${filteredOwn.length} entries`}
        </span>
      </div>

      {mode === 'patients' ? (
        <>
          {patients.length === 0 ? (
            <div className="card" style={{ textAlign: 'center', color: 'var(--muted)' }}>No clients assigned.</div>
          ) : (
            <>
              <div className="chip-row" style={{ marginBottom: '16px' }}>
                {patients.map((p: any) => {
                  const key = p.username || p
                  const sel = selectedPatient === key
                  return (
                    <button key={key} className={`chip${sel ? ' active' : ''}`} onClick={() => setSelectedPatient(key)}>
                      {p.name || key}
                    </button>
                  )
                })}
              </div>

              {selectedPatient && (
                <>
                  <h3 style={{ marginBottom: '4px' }}>
                    {patients.find((p: any) => (p.username || p) === selectedPatient)?.name || selectedPatient}
                  </h3>
                  <div style={{ fontSize: '0.72rem', color: 'var(--faint)', marginBottom: '12px' }}>Data shown reflects your access scope · journal raw text stays encrypted</div>

                  <div style={{ fontWeight: 800, fontSize: '0.8rem', color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: '8px' }}>
                    Journal entries {dateFrom || dateTo ? `(${filteredEntries.length} shown)` : ''}
                  </div>
                  {filteredEntries.length === 0 ? (
                    <div className="card-sm" style={{ color: 'var(--muted)' }}>No journal entries in this range.</div>
                  ) : (
                    filteredEntries.map((e: any, i: number) => {
                      const key = `j_${selectedPatient}_${e.id ?? i}`
                      const open = expandedEntries[key]
                      const ts = e.timestamp ? new Date(e.timestamp).toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : ''
                      return (
                        <div key={key} style={{ marginBottom: '6px' }}>
                          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                            <button onClick={() => toggleExpand(setExpandedEntries, key)}
                              style={{
                                flex: 1, padding: '9px 13px', background: open ? 'var(--accent-soft)' : 'var(--surface)',
                                border: `1px solid ${open ? 'var(--accent)' : 'var(--border)'}`, borderRadius: '12px',
                                color: 'var(--text)', fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer', textAlign: 'left',
                                display: 'flex', alignItems: 'center', gap: '8px', justifyContent: 'space-between',
                              }}>
                              <span>📄 {ts}</span>
                              <span style={{ color: 'var(--muted)', fontSize: '0.65rem' }}>{open ? '▲' : '▼'}</span>
                            </button>
                            <button onClick={() => downloadCsv(`${selectedPatient}_journal_${i}.csv`, [['Timestamp', 'Summary', 'Emotions'], [ts, e.summary || '', e.emotions || '']])}
                              className="icon-btn" title="Download CSV" style={{ width: '38px !important', height: '38px !important', minWidth: '38px', minHeight: '38px' }}>
                              ⬇
                            </button>
                          </div>
                          {open && (
                            <div style={{ background: 'var(--surface-soft)', border: '1px solid var(--border)', borderRadius: '14px', padding: '13px 15px', margin: '4px 0 0' }}>
                              <div style={{ color: 'var(--text)', fontSize: '0.82rem', lineHeight: 1.6 }}>{e.clinical_summary || e.summary}</div>
                              {e.patient_summary && (
                                <details style={{ marginTop: '8px' }}>
                                  <summary style={{ fontSize: '0.7rem', color: 'var(--accent)', cursor: 'pointer', fontWeight: 700 }}>Patient-facing summary</summary>
                                  <div style={{ color: 'var(--secondary)', fontSize: '0.75rem', lineHeight: 1.6, marginTop: '6px' }}>{e.patient_summary}</div>
                                </details>
                              )}
                              {e.emotions && <div style={{ color: 'var(--muted)', fontSize: '0.68rem', marginTop: '6px' }}>Emotions: {e.emotions}</div>}
                            </div>
                          )}
                        </div>
                      )
                    })
                  )}

                  {filteredNotes.length > 0 && (
                    <>
                      <div style={{ fontWeight: 800, fontSize: '0.8rem', color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.07em', margin: '16px 0 8px' }}>
                        Clinical notes {dateFrom || dateTo ? `(${filteredNotes.length} shown)` : ''}
                      </div>
                      {filteredNotes.map((n: any, i: number) => {
                        const key = `c_${selectedPatient}_${n.id ?? i}`
                        const open = expandedNotes[key]
                        const ts = n.timestamp ? new Date(n.timestamp).toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : ''
                        return (
                          <div key={key} style={{ marginBottom: '6px' }}>
                            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                              <button onClick={() => toggleExpand(setExpandedNotes, key)}
                                style={{
                                  flex: 1, padding: '9px 13px', background: open ? 'var(--accent-soft)' : 'var(--surface)',
                                  border: `1px solid ${open ? 'var(--accent)' : 'var(--border)'}`, borderRadius: '12px',
                                  color: 'var(--text)', fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer', textAlign: 'left',
                                  display: 'flex', alignItems: 'center', gap: '8px', justifyContent: 'space-between',
                                }}>
                                <span>📋 {ts}</span>
                                <span style={{ color: 'var(--muted)', fontSize: '0.65rem' }}>{open ? '▲' : '▼'}</span>
                              </button>
                              <button onClick={() => downloadCsv(`${selectedPatient}_clinical_${i}.csv`, [['Timestamp', 'Note'], [ts, n.ai_synthesis || n.raw_notes || '']])}
                                className="icon-btn" title="Download CSV" style={{ width: '38px !important', height: '38px !important', minWidth: '38px', minHeight: '38px' }}>
                                ⬇
                              </button>
                            </div>
                            {open && (
                              <div style={{ background: 'var(--surface-soft)', border: '1px solid var(--border)', borderRadius: '14px', padding: '13px 15px', margin: '4px 0 0' }}>
                                <div style={{ color: 'var(--text)', fontSize: '0.82rem', lineHeight: 1.6 }}>{n.ai_synthesis || n.raw_notes}</div>
                              </div>
                            )}
                          </div>
                        )
                      })}
                    </>
                  )}
                </>
              )}
            </>
          )}
        </>
      ) : (
        <div>
          <div style={{ fontWeight: 800, fontSize: '0.8rem', color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: '12px' }}>
            My journal entries {dateFrom || dateTo ? `(${filteredOwn.length} shown)` : ''}
          </div>
          {filteredOwn.length === 0 ? (
            <div className="card-sm" style={{ color: 'var(--muted)' }}>No journal entries yet.</div>
          ) : (
            filteredOwn.map((e: any, i: number) => {
              const key = `j_self_${e.id ?? i}`
              const open = expandedEntries[key]
              const ts = e.timestamp ? new Date(e.timestamp).toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : ''
              return (
                <div key={key} style={{ marginBottom: '6px' }}>
                  <button onClick={() => toggleExpand(setExpandedEntries, key)}
                    style={{
                      width: '100%', padding: '9px 13px', background: open ? 'var(--accent-soft)' : 'var(--surface)',
                      border: `1px solid ${open ? 'var(--accent)' : 'var(--border)'}`, borderRadius: '12px',
                      color: 'var(--text)', fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer', textAlign: 'left',
                      display: 'flex', alignItems: 'center', gap: '8px', justifyContent: 'space-between',
                    }}>
                    <span>📄 {ts}</span>
                    <span style={{ color: 'var(--muted)', fontSize: '0.65rem' }}>{open ? '▲' : '▼'}</span>
                  </button>
                  {open && (
                    <div style={{ background: 'var(--surface-soft)', border: '1px solid var(--border)', borderRadius: '14px', padding: '13px 15px', margin: '4px 0 0' }}>
                      <div style={{ color: 'var(--text)', fontSize: '0.82rem', lineHeight: 1.6 }}>{e.summary}</div>
                      {e.emotions && <div style={{ color: 'var(--muted)', fontSize: '0.68rem', marginTop: '6px' }}>Emotions: {e.emotions}</div>}
                    </div>
                  )}
                </div>
              )
            })
          )}
        </div>
      )}
    </div>
  )
}
