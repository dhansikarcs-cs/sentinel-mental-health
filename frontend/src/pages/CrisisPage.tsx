import { useEffect, useState, useRef, useCallback } from 'react'
import { api, isNetworkError } from '../api/client'
import { getUser } from '../stores/auth'
import { computeCrisisStage, CRISIS_STAGES, CRISIS_STAGE_MESSAGES } from '../constants'

function mailto(email: string, subject: string, body: string) {
  return `mailto:${encodeURIComponent(email)}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`
}

function BreathPacer() {
  // 4-4-4-4 box breathing: inhale / hold / exhale / hold, 4s each.
  const PHASES = [
    { label: 'Breathe in', seconds: 4 },
    { label: 'Hold', seconds: 4 },
    { label: 'Breathe out', seconds: 4 },
    { label: 'Hold', seconds: 4 },
  ]
  const [phaseIdx, setPhaseIdx] = useState(0)
  const [count, setCount] = useState(4)
  const [cycles, setCycles] = useState(0)
  const [running, setRunning] = useState(false)

  useEffect(() => {
    if (!running) return
    const t = setInterval(() => {
      setCount(c => {
        if (c > 1) return c - 1
        setPhaseIdx(p => {
          const next = (p + 1) % PHASES.length
          if (next === 0) setCycles(x => x + 1)
          return next
        })
        return PHASES[(phaseIdx + 1) % PHASES.length].seconds
      })
    }, 1000)
    return () => clearInterval(t)
  }, [running, phaseIdx])

  const phase = PHASES[phaseIdx]
  const scale = phase.label === 'Breathe in' ? 1.25 : phase.label === 'Breathe out' ? 0.7 : phaseIdx === 1 ? 1.25 : 0.7

  return (
    <div className="card" style={{ padding: '18px', textAlign: 'center' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
        <div style={{ fontWeight: 800, fontSize: '0.8rem' }}>🌬️ Box breathing — 4·4·4·4</div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          {cycles > 0 && <span style={{ fontSize: '0.68rem', color: 'var(--muted)', fontWeight: 700 }}>{cycles} cycle{cycles > 1 ? 's' : ''}</span>}
          <button onClick={() => setRunning(r => !r)} style={{ padding: '4px 12px', fontSize: '0.72rem' }}>
            {running ? 'Pause' : cycles > 0 ? 'Resume' : 'Start'}
          </button>
        </div>
      </div>
      <div style={{ display: 'flex', justifyContent: 'center', padding: '12px 0' }}>
        <div
          style={{
            width: 96, height: 96, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
            background: 'radial-gradient(circle, rgba(87,199,138,0.25), rgba(87,199,138,0.05))',
            border: '1px solid color-mix(in srgb, var(--ok) 40%, transparent)',
            transform: `scale(${running ? scale : 1})`,
            transition: 'transform 3.8s ease-in-out',
          }}
        >
          <div>
            <div style={{ fontSize: '1.05rem', fontWeight: 800, color: 'var(--ok)' }}>{running ? phase.label : 'Ready'}</div>
            <div style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--heading)' }}>{running ? count : '·'}</div>
          </div>
        </div>
      </div>
      <div style={{ fontSize: '0.66rem', color: 'var(--muted)' }}>
        In 4 · hold 4 · out 4 · hold 4 — a few cycles calm the nervous system.
      </div>
    </div>
  )
}

function playAlertAudio() {
  if (localStorage.getItem('sentinel-crisis-muted') === '1') return () => {}
  try {
    const ctx = new (window.AudioContext || (window as any).webkitAudioContext)()
    const d = 1.5
    const sr = ctx.sampleRate
    const len = sr * d
    const buf = ctx.createBuffer(1, len, sr)
    const ch = buf.getChannelData(0)
    for (let i = 0; i < len; i++) {
      const t = i / sr
      const sweep = 440 + 220 * Math.sin(2 * Math.PI * 3 * t)
      const pulse = 0.4 + 0.3 * Math.sin(2 * Math.PI * 2 * t)
      ch[i] = pulse * Math.sin(2 * Math.PI * sweep * t) * 0.5
    }
    const src = ctx.createBufferSource()
    src.buffer = buf
    src.loop = true
    src.connect(ctx.destination)
    src.start()
    return () => { try { src.stop(); ctx.close() } catch {} }
  } catch { return () => {} }
}

export default function CrisisPage() {
  const user = getUser()
  const [cs, setCs] = useState<any>({})
  const [elapsed, setElapsed] = useState(0)
  const [loading, setLoading] = useState(true)
  const [cancelling, setCancelling] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [error, setError] = useState('')
  const [me, setMe] = useState<any>(getUser() || {})
  const [offline, setOffline] = useState(false)
  const [tools, setTools] = useState<any[]>([])
  const [usedTools, setUsedTools] = useState<Record<number, boolean>>({})
  const [muted, setMuted] = useState(localStorage.getItem('sentinel-crisis-muted') === '1')
  const intervalRef = useRef<any>(null)
  const stopAudioRef = useRef<(() => void) | null>(null)
  const prevActiveRef = useRef(false)

  async function load() {
    try {
      const [state, el] = await Promise.all([
        api.getCrisisState(),
        api.getCrisisElapsed()
      ])
      setCs(state || {})
      setElapsed(el?.elapsed || 0)
      setOffline(false)
    } catch (err) {
      if (isNetworkError(err)) setOffline(true)
    }
    setLoading(false)
  }

  useEffect(() => {
    load()
    intervalRef.current = setInterval(load, 3000)
    api.getMe().then((d: any) => setMe(d || {})).catch(() => {})
    api.getCopingTools().then((d: any) => setTools(Array.isArray(d) ? d : [])).catch(() => {})
    return () => clearInterval(intervalRef.current)
  }, [])

  useEffect(() => {
    if (cs.active && !prevActiveRef.current) {
      stopAudioRef.current = playAlertAudio()
    } else if (!cs.active && prevActiveRef.current) {
      if (stopAudioRef.current) { stopAudioRef.current(); stopAudioRef.current = null }
    }
    prevActiveRef.current = cs.active
    return () => {
      if (stopAudioRef.current) { stopAudioRef.current(); stopAudioRef.current = null }
    }
  }, [cs.active])

  useEffect(() => {
    if (cs.active) {
      const tick = setInterval(() => setElapsed(e => e + 1), 1000)
      return () => clearInterval(tick)
    }
  }, [cs.active])

  const isPsych = user?.role === 'psychologist'
  const isAdmin = user?.role === 'admin'
  const active = cs.active
  const triggeredBy = cs.triggered_by || 'patient'
  // Whose crisis is this, and is it mine? Patients only get cancel/notify
  // controls on their OWN crisis — never on one they're viewing as staff.
  const crisisPatient = cs.patient || ''
  const isOwnCrisis = !isPsych && !isAdmin && crisisPatient === user?.username

  const stage = computeCrisisStage(cs, elapsed)
  const terminal = stage === 'acknowledged'

  async function trigger() {
    try { await api.triggerCrisis(); await load() } catch (err: any) { alert(err.message) }
  }

  async function handleCancel() {
    if (!confirming) { setConfirming(true); return }
    setCancelling(true)
    setError('')
    try { await api.resolveCrisis(); await load() } catch (e: any) { setError('Failed to cancel crisis. Please try again.') }
    setCancelling(false)
    setConfirming(false)
  }

  async function handleResolve() {
    setCancelling(true)
    setError('')
    try { await api.resolveCrisis(); await load() } catch (e: any) { setError('Failed to resolve crisis. Please try again.') }
    setCancelling(false)
  }

  async function acknowledge() {
    setError('')
    try { await api.acknowledgeCrisis(); await load() } catch (e: any) { setError('Failed to acknowledge. Please try again.') }
  }

  async function notifyTC() {
    setError('')
    try { await api.notifyTrustedContact(); await load() } catch (e: any) { setError('Failed to notify. Please try again.') }
  }

  if (loading) return <div className="animate-fade-in"><div className="card">Loading…</div></div>

  const displayTime = elapsed >= 60 ? '60+' : String(elapsed)

  function stageStyle(key: string) {
    const isActive = key === stage || (terminal && key === 'helpline_escalated')
    const found = CRISIS_STAGES.find(s => s.key === key)
    const passed = found ? elapsed >= found.sec : false
    if (isActive) return { color: 'var(--danger)', background: 'rgba(214,69,58,0.14)', border: '1px solid rgba(214,69,58,0.45)' }
    if (passed) return { color: 'var(--ok)', background: 'var(--ok-soft)', border: '1px solid color-mix(in srgb, var(--ok) 30%, transparent)' }
    return { color: 'var(--faint)', background: 'var(--surface-soft)', border: '1px solid var(--border-soft)' }
  }

  const helplineNumber = me.helpline_email
    ? `988 (Suicide & Crisis Lifeline) · ${me.helpline_email}`
    : '988 (Suicide & Crisis Lifeline)'

  const directEmailCard = (offline || active) && (me.psych_email || me.helpline_email)

  return (
    <div className="animate-fade-in">
      {/* Pulsing red vignette while a crisis is live (skipped if reduced motion) */}
      {active && !terminal && <div className="crisis-vignette" aria-hidden />}

      {/* Helpline bar */}
      <div style={{ background: 'var(--info-soft)', border: '1px solid color-mix(in srgb, var(--info) 30%, transparent)', borderRadius: '16px', padding: '11px 16px', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
        <span style={{ fontSize: '1.1rem' }}>📞</span>
        <span style={{ color: 'var(--info)', fontSize: '0.875rem', fontWeight: 700 }}>
          24/7 Helpline: {helplineNumber}
        </span>
        <a className="btn-primary" href="tel:988" style={{ textDecoration: 'none', display: 'inline-flex', padding: '7px 16px', fontSize: '0.8rem' }} title="Tap to call the 988 Suicide & Crisis Lifeline from your phone">
          📞 Call 988 now
        </a>
        <button
          onClick={() => {
            const next = !muted
            setMuted(next)
            localStorage.setItem('sentinel-crisis-muted', next ? '1' : '0')
            if (next && stopAudioRef.current) { stopAudioRef.current(); stopAudioRef.current = null }
          }}
          style={{ marginLeft: 'auto', padding: '5px 12px', fontSize: '0.72rem' }}
          title="Mute or unmute the crisis alert tone"
        >
          {muted ? '🔇 Alert tone off' : '🔊 Alert tone on'}
        </button>
        <span style={{ color: 'var(--muted)', fontSize: '0.72rem' }}>Free & confidential · always</span>
      </div>

      {directEmailCard && (
        <div className="card" style={{ marginTop: '0', marginBottom: '14px', borderColor: offline ? 'var(--warn)' : 'var(--border-soft)' }}>
          <div style={{ fontWeight: 700, fontSize: '0.875rem', marginBottom: '10px' }}>
            {offline
              ? '⚠️ You are offline — the server is unreachable. Reach someone directly from your own mail app:'
              : '📧 Also reachable directly (works even if the app/server is unreachable):'}
          </div>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {me.psych_email && (
              <a className="btn-primary" style={{ textDecoration: 'none', display: 'inline-flex' }}
                href={mailto(
                  me.psych_email,
                  `Sentinel Crisis — ${me.name || me.username} needs help`,
                  `Hi, ${me.name || me.username} (${me.username}) triggered a crisis alert in Sentinel and needs your help as soon as possible.\n\nPlease reach out to them now.`
                )}>
                📧 Email your psychologist
              </a>
            )}
            {me.helpline_email && (
              <a className="btn-primary" style={{ textDecoration: 'none', display: 'inline-flex' }}
                href={mailto(
                  me.helpline_email,
                  `Sentinel CRISIS ESCALATION — ${me.name || me.username}`,
                  `Patient ${me.username} is in crisis and has not been acknowledged. Immediate helpline intervention is required.\n\nTime sensitive — please follow your protocol.`
                )}>
                📧 Email helpline
              </a>
            )}
          </div>
        </div>
      )}

      {!active ? (
        <div className="card" style={{ padding: '34px', textAlign: 'center', background: 'var(--surface)' }}>
          <div style={{ fontSize: '2.4rem', marginBottom: '8px' }}>🫂</div>
          <h2 style={{ marginBottom: '6px' }}>You&apos;re not alone</h2>
          <p style={{ color: 'var(--muted)', fontSize: '0.88rem', maxWidth: '420px', margin: '0 auto 22px', lineHeight: 1.6 }}>
            Pressing the button alerts your psychologist and starts the escalation chain —
            trusted contact at 30s, helpline at 60s. There is no wrong time to use it.
          </p>
          <button onClick={trigger} className="btn-danger pulse-crisis" style={{ padding: '18px 44px', fontSize: '1.05rem', fontWeight: 800 }}>
            <span className="heartbeat" style={{ display: 'inline-block' }}>🔥</span> I need help now
          </button>
          <div style={{ fontSize: '0.68rem', color: 'var(--faint)', marginTop: '14px' }}>
            You can cancel within the first seconds if it was a mis-tap.
          </div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {error && (
            <div className="card-sm" style={{ background: 'var(--danger-soft)', border: '1px solid color-mix(in srgb, var(--danger) 30%, transparent)', color: 'var(--danger-deep)', fontSize: '0.82rem', fontWeight: 600 }}>
              {error}
            </div>
          )}
          {triggeredBy === 'psychologist' && (
            <div className="card shake-once" style={{ borderColor: 'var(--danger)', color: 'var(--danger-deep)', background: 'var(--danger-alpha)' }}>
              <strong><span className="heartbeat" style={{ display: 'inline-block' }}>🔴</span> Crisis triggered by your psychologist</strong> — elevated vitals + journal analysis indicated high risk.
            </div>
          )}
          <BreathPacer />

          {tools.length > 0 && (
            <div className="card" style={{ padding: '16px' }}>
              <div style={{ fontWeight: 800, fontSize: '0.8rem', marginBottom: '10px' }}>🧰 Your coping toolbox — tap one when you've tried it</div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '6px' }}>
                {tools.map(t => (
                  <button
                    key={t.id}
                    onClick={() => setUsedTools(prev => ({ ...prev, [t.id]: true }))}
                    style={{
                      textAlign: 'left', padding: '10px 12px', borderRadius: 12, cursor: 'pointer',
                      background: usedTools[t.id] ? 'var(--ok-soft)' : 'var(--surface-soft)',
                      border: usedTools[t.id] ? '1px solid color-mix(in srgb, var(--ok) 40%, transparent)' : '1px solid var(--border-soft)',
                      color: usedTools[t.id] ? 'var(--ok)' : 'var(--heading)',
                    }}
                  >
                    <span style={{ fontWeight: 700, fontSize: '0.76rem' }}>{usedTools[t.id] ? '✓ ' : ''}{t.title}</span>
                    {t.recommended_by && <span style={{ display: 'block', fontSize: '0.6rem', color: 'var(--accent)', fontWeight: 800, marginTop: '2px' }}>🧑‍⚕️ suggested by {t.recommended_by}</span>}
                    {t.description && <span style={{ display: 'block', fontSize: '0.66rem', color: 'var(--muted)', marginTop: '2px' }}>{t.description}</span>}
                  </button>
                ))}
              </div>
            </div>
          )}
          {stage === 'acknowledged' && (
            <div className="card-sm calm-pulse" style={{ background: 'var(--ok-soft)', borderColor: 'color-mix(in srgb, var(--ok) 30%, transparent)' }}>
              <strong style={{ color: 'var(--ok)' }}>{CRISIS_STAGE_MESSAGES.acknowledged.text}</strong>
            </div>
          )}
          {stage === 'helpline_escalated' && (
            <div className="card-sm" style={{ background: 'var(--danger-soft)', borderColor: 'var(--danger)' }}>
              <strong style={{ color: 'var(--danger)' }}>{CRISIS_STAGE_MESSAGES.helpline_escalated.text}</strong>
            </div>
          )}
          {['trustee_coming', 'trustee_clicked'].includes(stage) && (
            <div className="card-sm" style={{ background: 'var(--warn-soft)', borderColor: 'color-mix(in srgb, var(--warn) 30%, transparent)' }}>
              <strong style={{ color: 'var(--warn)' }}>{CRISIS_STAGE_MESSAGES[stage].text}</strong>
            </div>
          )}
          {!terminal && stage !== 'helpline_escalated' && triggeredBy !== 'psychologist' && (
            <div className="card shake-once" style={{ borderColor: 'var(--danger)', background: 'var(--danger-alpha)' }}>
              <strong style={{ color: 'var(--danger-deep)' }}><span className="live-dot" style={{ marginRight: 6 }} />⚠️ Help has been alerted. Stay where you are if you can — support is moving.</strong>
            </div>
          )}

          {/* Timer + stages */}
          <div className="card-dark" style={{ padding: '18px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px', flexWrap: 'wrap' }}>
              <span style={{ color: '#A6AC9D', fontSize: '0.7rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.08em' }}>⏱️ Escalation clock</span>
              <span className="heartbeat" style={{ color: 'var(--on-ink)', fontSize: '1.6rem', fontWeight: 800 }}>{displayTime}s</span>
              <span style={{ color: '#A6AC9D', fontSize: '0.75rem' }}>elapsed</span>
              <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '6px' }}>
                {stage === 'helpline_escalated' && <><span className="live-dot" /><span style={{ color: 'var(--danger)', fontWeight: 700, fontSize: '0.8rem' }}>🏥 Helpline contacted</span></>}
                {stage === 'trustee_coming' && <><span className="live-dot" /><span style={{ color: '#57C78A', fontWeight: 700, fontSize: '0.8rem' }}>🟢 Trusted contact on the way</span></>}
                {stage === 'trustee_clicked' && <><span className="live-dot" /><span style={{ color: '#57C78A', fontWeight: 700, fontSize: '0.8rem' }}>🟢 Trusted contact notified</span></>}
                {stage === 'acknowledged' && <span style={{ color: '#57C78A', fontWeight: 700, fontSize: '0.8rem' }}>✅ Psychologist acknowledged</span>}
              </div>
            </div>
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
              {CRISIS_STAGES.map(s => {
                const ss = stageStyle(s.key)
                return (
                  <div key={s.key} style={{ flex: 1, minWidth: '120px', textAlign: 'center', padding: '10px', borderRadius: '14px', background: ss.background, border: ss.border, color: ss.color, fontSize: '0.8rem', fontWeight: 700 }}>
                    {s.label}<br /><span style={{ fontSize: '0.66rem', fontWeight: 500 }}>{s.sec}s</span>
                  </div>
                )
              })}
            </div>
          </div>

          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {!cs.acknowledged && isPsych && (
              <button onClick={acknowledge} className="btn-primary" style={{ flex: 1, padding: '12px' }}>✓ Acknowledge crisis</button>
            )}
            {isOwnCrisis && triggeredBy === 'patient' && (
              <button onClick={notifyTC} style={{ flex: 1, padding: '12px' }}>👤 Notify trusted contact + psychologist</button>
            )}
          </div>

          {isOwnCrisis && triggeredBy === 'patient' && !terminal && (
            confirming ? (
              <div className="card" style={{ borderColor: 'var(--warn)', background: 'var(--warn-soft)', padding: '14px' }}>
                <div style={{ fontWeight: 700, marginBottom: '8px', color: 'var(--warn)' }}>Cancel this crisis?</div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button className="btn-danger" onClick={handleCancel} disabled={cancelling}>{cancelling ? 'Cancelling…' : 'Yes, I\'m safe — cancel'}</button>
                  <button onClick={() => setConfirming(false)}>Keep it active</button>
                </div>
              </div>
            ) : (
              <button onClick={handleCancel} style={{ padding: '10px' }}>✅ I&apos;m safe — cancel crisis</button>
            )
          )}
          {isPsych && !terminal && (
            <button onClick={handleResolve} disabled={cancelling} className="btn-primary" style={{ padding: '12px', background: 'var(--ok) !important', borderColor: 'var(--ok) !important' }}>
              {cancelling ? 'Resolving…' : '🗑 Resolve crisis'}
            </button>
          )}
          {triggeredBy === 'psychologist' && !isPsych && (
            <div style={{ color: 'var(--muted)', fontSize: '0.8rem' }}>⚠️ This crisis was triggered by your psychologist. Only they can resolve it.</div>
          )}
        </div>
      )}
    </div>
  )
}
