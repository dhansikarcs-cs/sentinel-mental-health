import { useEffect, useMemo, useState } from 'react'
import { api } from '../api/client'

/* ── Stress timeline: rounded hourly curve + day-by-day list ──────
   Patient Insights + Open Session. The curve shows how stress moves
   across the clock (avg per hour, smoothed with big soft beziers);
   the list shows every day with its average, peak and spike count. */

interface HourSlot { hour: number; avg: number | null; max: number | null; n: number }
interface DailyRow { iso_day: string; day: string; avg: number; peak: number; peak_time: string; n: number; spikes: number }
interface Spike {
  stress: number; heart_rate: number; hrv: number; logged_at: string
  day: string; iso_day: string; time: string; hour: number; weekday: string
  severity: 'moderate' | 'high' | 'severe'
}
interface SpikeData {
  patient: string; window_days: number; reading_count: number
  baseline: number | null; threshold: number | null
  spikes: Spike[]
  by_hour: Record<string, number>
  by_weekday: Record<string, number>
  worst: Spike | null
  hourly: HourSlot[]
  daily: DailyRow[]
}

const WEEK = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
const SEV: Record<string, { icon: string; cls: string }> = {
  severe: { icon: '🔴', cls: 'lvl-crit' },
  high: { icon: '🟠', cls: 'lvl-high' },
  moderate: { icon: '🟡', cls: 'lvl-watch' },
}

function pct(v: number, max: number) {
  return max > 0 ? Math.round((v / max) * 100) : 0
}

/* Catmull-Rom → cubic bezier: the "very rounded" curve. */
function smoothPath(pts: { x: number; y: number }[]): string {
  if (pts.length === 0) return ''
  if (pts.length === 1) return `M ${pts[0].x} ${pts[0].y}`
  let d = `M ${pts[0].x} ${pts[0].y}`
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[Math.max(0, i - 1)]
    const p1 = pts[i]
    const p2 = pts[i + 1]
    const p3 = pts[Math.min(pts.length - 1, i + 2)]
    const c1x = p1.x + (p2.x - p0.x) / 6
    const c1y = p1.y + (p2.y - p0.y) / 6
    const c2x = p2.x - (p3.x - p1.x) / 6
    const c2y = p2.y - (p3.y - p1.y) / 6
    d += ` C ${c1x.toFixed(1)} ${c1y.toFixed(1)}, ${c2x.toFixed(1)} ${c2y.toFixed(1)}, ${p2.x.toFixed(1)} ${p2.y.toFixed(1)}`
  }
  return d
}

const W = 640
const H = 190
const PAD = { l: 36, r: 14, t: 16, b: 28 }

function HourlyCurve({ hourly, threshold }: { hourly: HourSlot[]; threshold: number | null }) {
  const [hover, setHover] = useState<number | null>(null)

  const yMax = useMemo(() => {
    const vals = hourly.map((h) => Math.max(h.avg ?? 0, h.max ?? 0))
    return Math.max(100, ...vals) + 8
  }, [hourly])

  const x = (hour: number) => PAD.l + (hour / 23) * (W - PAD.l - PAD.r)
  const y = (v: number) => PAD.t + (1 - v / yMax) * (H - PAD.t - PAD.b)

  const pts = hourly.filter((h) => h.avg != null).map((h) => ({ x: x(h.hour), y: y(h.avg as number), h }))
  const curve = smoothPath(pts)
  const area = pts.length > 1 ? `${curve} L ${pts[pts.length - 1].x} ${H - PAD.b} L ${pts[0].x} ${H - PAD.b} Z` : ''

  const hoverSlot = hover != null ? hourly[hover] : null

  return (
    <div className="hourly-wrap">
      <div className="hourly-title">🕐 Stress across the day — hourly average</div>
      {pts.length === 0 ? (
        <div className="spikes-empty">No readings in this window yet.</div>
      ) : (
        <svg viewBox={`0 0 ${W} ${H}`} className="hourly-svg" role="img" aria-label="Average stress per hour">
          <defs>
            <linearGradient id="stressFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--lime, #c8f169)" stopOpacity="0.45" />
              <stop offset="100%" stopColor="var(--lime, #c8f169)" stopOpacity="0.02" />
            </linearGradient>
          </defs>

          {[0.25, 0.5, 0.75, 1].map((f) => {
            const gy = PAD.t + f * (H - PAD.t - PAD.b)
            return <line key={f} x1={PAD.l} x2={W - PAD.r} y1={gy} y2={gy} className="grid-line" />
          })}

          {threshold != null && threshold <= yMax && (
            <g>
              <line x1={PAD.l} x2={W - PAD.r} y1={y(threshold)} y2={y(threshold)} className="threshold-line" />
              <text x={W - PAD.r} y={y(threshold) - 5} textAnchor="end" className="threshold-label">spike threshold {threshold}</text>
            </g>
          )}

          {area && <path d={area} fill="url(#stressFill)" className="curve-area" />}
          <path d={curve} fill="none" className="curve-stroke" />

          {pts.map((p) => (
            <circle key={p.h.hour} cx={p.x} cy={p.y} r={hover === p.h.hour ? 6 : 3.5} className={`curve-dot${hover === p.h.hour ? ' big' : ''}`}>
              <title>{`${String(p.h.hour).padStart(2, '0')}:00 — avg ${p.h.avg}, peak ${p.h.max} (${p.h.n} readings)`}</title>
            </circle>
          ))}

          {/* transparent hover strips */}
          {hourly.map((h, i) => (
            <rect
              key={i}
              x={x(h.hour) - (W - PAD.l - PAD.r) / 48}
              y={PAD.t}
              width={(W - PAD.l - PAD.r) / 24}
              height={H - PAD.t - PAD.b}
              fill="transparent"
              onMouseEnter={() => setHover(i)}
              onMouseLeave={() => setHover(null)}
            />
          ))}

          {[0, 6, 12, 18, 23].map((h) => (
            <text key={h} x={x(h)} y={H - 8} textAnchor="middle" className="axis-label">
              {String(h).padStart(2, '0')}
            </text>
          ))}
        </svg>
      )}
      {hoverSlot && hoverSlot.avg != null && (
        <div className="hourly-tip">
          <b>{String(hoverSlot.hour).padStart(2, '0')}:00</b> — avg <b>{hoverSlot.avg}</b>, peak <b>{hoverSlot.max}</b> · {hoverSlot.n} readings
        </div>
      )}
    </div>
  )
}

export default function StressSpikes({ username, compact = false }: { username: string; compact?: boolean }) {
  const [data, setData] = useState<SpikeData | null>(null)
  const [err, setErr] = useState('')
  const [days, setDays] = useState(30)

  useEffect(() => {
    let live = true
    setData(null)
    setErr('')
    api
      .getStressSpikes(username, days)
      .then((res: any) => {
        if (live) setData(res?.data ?? res)
      })
      .catch(() => {
        if (live) setErr('No stress data available')
      })
    return () => {
      live = false
    }
  }, [username, days])

  const dailyDesc = useMemo(() => (data?.daily ? [...data.daily].reverse() : []), [data])

  if (err) return <div className="spikes-empty">🕯️ {err}</div>
  if (!data) return <div className="spikes-empty">Loading stress timeline…</div>

  const weekdayCounts = WEEK.map((d) => ({ label: d.slice(0, 3), count: data.by_weekday[d] || 0 }))
  const hourEntries = Object.entries(data.by_hour).map(([h, c]) => ({ hour: Number(h), count: c })).sort((a, b) => a.hour - b.hour)
  const maxDay = Math.max(1, ...weekdayCounts.map((d) => d.count))
  const peakDay = [...weekdayCounts].sort((a, b) => b.count - a.count)[0]
  const peakHour = [...hourEntries].sort((a, b) => b.count - a.count)[0]

  return (
    <div className={`spikes-card${compact ? ' compact' : ''}`}>
      <div className="spikes-head">
        <span className="spikes-title">⚡ Stress spikes — when they hit</span>
        <div className="spikes-range">
          {[7, 30, 90].map((d) => (
            <button key={d} className={`spikes-tab${days === d ? ' on' : ''}`} onClick={() => setDays(d)}>
              {d}d
            </button>
          ))}
        </div>
      </div>

      <div className="spikes-meta">
        {data.reading_count > 0 ? (
          <>📊 {data.reading_count} readings · baseline {data.baseline} · spike threshold {data.threshold}</>
        ) : (
          <>No readings in this window</>
        )}
      </div>

      <HourlyCurve hourly={data.hourly} threshold={data.threshold} />

      {dailyDesc.length > 0 && (
        <div className="daily-wrap">
          <div className="pattern-title">Day by day</div>
          <div className="daily-list">
            {dailyDesc.map((d, i) => (
              <div key={d.iso_day} className="daily-row" style={{ animationDelay: `${Math.min(i, 12) * 40}ms` }}>
                <span className="daily-day">{d.day}</span>
                <span className="daily-avg">avg {d.avg}</span>
                <div className="daily-bar">
                  <div className="daily-fill" style={{ width: `${pct(d.avg, 100)}%` }} />
                  <div className={`daily-peak-mark ${d.peak >= (data.threshold ?? 999) ? ' hot' : ''}`} style={{ left: `${pct(d.peak, 100)}%` }} />
                </div>
                <span className="daily-peak">peak <b>{d.peak}</b> @ {d.peak_time}</span>
                <span className={`daily-spikes${d.spikes ? ' has' : ''}`}>{d.spikes ? `⚡ ${d.spikes}` : '·'}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {data.spikes.length === 0 ? (
        <div className="spikes-empty">✨ No stress spikes in the last {data.window_days} days — baseline stayed steady.</div>
      ) : (
        <>
          {data.worst && (
            <div className="spike-worst">
              {SEV[data.worst.severity]?.icon ?? '🟠'} Worst: <b>{data.worst.day} at {data.worst.time}</b> — stress {data.worst.stress}, ❤️ {data.worst.heart_rate} bpm
            </div>
          )}
          <div className="spikes-list">
            {data.spikes.map((s, i) => (
              <div key={s.logged_at + i} className="spike-row" style={{ animationDelay: `${Math.min(i, 10) * 60}ms` }}>
                <span className="spike-icon">{SEV[s.severity]?.icon ?? '🟡'}</span>
                <span className="spike-day">{s.day}</span>
                <span className="spike-time">{s.time}</span>
                <div className="spike-bar">
                  <div className={`spike-fill ${SEV[s.severity]?.cls ?? 'lvl-watch'}`} style={{ width: `${pct(s.stress, 130)}%` }} />
                </div>
                <span className="spike-val">{s.stress}</span>
              </div>
            ))}
          </div>

          {peakDay && peakDay.count > 0 && (
            <div className="spikes-pattern">
              <div className="pattern-title">Pattern — when spikes cluster</div>
              <div className="pattern-week">
                {weekdayCounts.map((d) => (
                  <div key={d.label} className={`pattern-cell${d.count > 0 && d.count === peakDay.count ? ' peak' : ''}`}>
                    <div className="pattern-bar" style={{ height: `${Math.max(6, pct(d.count, maxDay))}%` }} />
                    <span className="pattern-day">{d.label}</span>
                    <span className="pattern-n">{d.count || ''}</span>
                  </div>
                ))}
              </div>
              <div className="pattern-note">
                🕒 Most spikes land on <b>{peakDay.label}</b>
                {peakHour && peakHour.count > 0 ? <> around <b>{String(peakHour.hour).padStart(2, '0')}:00</b></> : null} — worth asking about in session.
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
