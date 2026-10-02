import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'

/* ── Toasts ───────────────────────────────────────────────────────
   Slide-in notifications that replace alert() — auto-dismiss after
   3.5s, stacked bottom-right, colored by kind. */

export type ToastKind = 'success' | 'error' | 'info'

interface Toast {
  id: number
  kind: ToastKind
  text: string
}

const ToastCtx = createContext<(kind: ToastKind, text: string) => void>(() => {})

export function useToast() {
  return useContext(ToastCtx)
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const idRef = useRef(0)

  const push = useCallback((kind: ToastKind, text: string) => {
    const id = ++idRef.current
    setToasts(prev => [...prev, { id, kind, text }])
    window.setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 3500)
  }, [])

  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="toast-stack" role="status" aria-live="polite">
        {toasts.map(t => (
          <div key={t.id} className={`toast toast-${t.kind}`}>
            <span className="toast-icon">{t.kind === 'success' ? '✅' : t.kind === 'error' ? '⚠️' : 'ℹ️'}</span>
            <span>{t.text}</span>
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  )
}

/* ── Confetti ─────────────────────────────────────────────────────
   Bursts N colored particles from a point; each falls with its own
   drift and spin. Auto-cleans after the animation. */

interface Particle {
  id: number
  x: number
  color: string
  delay: number
  drift: number
  size: number
}

export function Confetti({ trigger }: { trigger: unknown }) {
  const [particles, setParticles] = useState<Particle[]>([])
  const idRef = useRef(0)

  useEffect(() => {
    if (trigger === undefined || trigger === null || trigger === false) return
    const colors = ['var(--lime)', 'var(--accent)', 'var(--ok)', 'var(--violet)', '#E8763B']
    const batch: Particle[] = Array.from({ length: 40 }, (_, i) => ({
      id: ++idRef.current,
      x: 20 + Math.random() * 60,
      color: colors[i % colors.length],
      delay: Math.random() * 0.3,
      drift: (Math.random() - 0.5) * 160,
      size: 6 + Math.random() * 7,
    }))
    setParticles(prev => [...prev, ...batch])
    const cleanup = window.setTimeout(() => setParticles(prev => prev.filter(p => !batch.includes(p))), 2200)
    return () => window.clearTimeout(cleanup)
  }, [trigger])

  if (particles.length === 0) return null
  return (
    <div style={{ position: 'fixed', inset: 0, pointerEvents: 'none', zIndex: 2000, overflow: 'hidden' }} aria-hidden>
      {particles.map(p => (
        <span
          key={p.id}
          className="confetti-piece"
          style={{ left: `${p.x}%`, background: p.color, width: p.size, height: p.size * 0.6, animationDelay: `${p.delay}s`, ['--drift' as any]: `${p.drift}px` }}
        />
      ))}
    </div>
  )
}

/* ── Ripple ───────────────────────────────────────────────────────
   useRipple(): attach to any button for a material-style ripple from
   the tap point. Returns handlers to spread onto the element. */

export function useRipple() {
  return {
    onMouseDown: (e: React.MouseEvent<HTMLElement>) => {
      const el = e.currentTarget
      const rect = el.getBoundingClientRect()
      const ripple = document.createElement('span')
      const size = Math.max(rect.width, rect.height) * 2
      ripple.className = 'ripple'
      ripple.style.width = ripple.style.height = `${size}px`
      ripple.style.left = `${e.clientX - rect.left - size / 2}px`
      ripple.style.top = `${e.clientY - rect.top - size / 2}px`
      ripple.addEventListener('animationend', () => ripple.remove())
      el.appendChild(ripple)
    },
  }
}

/* ── Shimmer ──────────────────────────────────────────────────────
   Skeleton placeholder shown while data loads. */

export function Shimmer({ height = 64, width = '100%', radius = 14, count = 1 }: { height?: number; width?: number | string; radius?: number; count?: number }) {
  return (
    <>
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className="shimmer" style={{ height, width, borderRadius: radius, marginBottom: count > 1 ? 10 : 0 }} />
      ))}
    </>
  )
}

/* ── Floating empty state ───────────────────────────────────────── */

export function FloatingEmpty({ emoji, title, sub }: { emoji: string; title: string; sub?: string }) {
  return (
    <div className="card" style={{ textAlign: 'center', padding: '34px' }}>
      <div className="floaty" style={{ fontSize: '2.4rem', marginBottom: '6px' }}>{emoji}</div>
      <div style={{ fontWeight: 700 }}>{title}</div>
      {sub && <div style={{ color: 'var(--muted)', fontSize: '0.8rem', marginTop: '4px' }}>{sub}</div>}
    </div>
  )
}
