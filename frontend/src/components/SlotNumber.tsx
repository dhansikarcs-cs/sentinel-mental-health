import { useEffect, useRef, useState } from 'react'

/**
 * SlotNumber — odometer/slot-machine number reveal.
 *
 * Shows fast-changing random digits, then "settles" digit-by-digit into the
 * real value. Non-numeric characters (letters, 🔥, /, —) are shown as-is.
 * Re-scrambles when `value` changes or when `replayKey` changes, so callers
 * can replay the animation when fresh data arrives.
 *
 * Conventions: matches existing keyframes style in index.css (selectPop,
 * barGrow), duration ~0.9s total so the page settles quickly.
 */

interface SlotNumberProps {
  value: number | string
  /** ms between scramble ticks (lower = more frantic) */
  tickMs?: number
  /** how long each digit keeps scrambling after the previous settles */
  settleStaggerMs?: number
  /** change this to replay the animation (e.g. pass a data timestamp) */
  replayKey?: string | number
  className?: string
  style?: React.CSSProperties
}

export default function SlotNumber({
  value,
  tickMs = 55,
  settleStaggerMs = 90,
  replayKey,
  className,
  style,
}: SlotNumberProps) {
  const str = String(value)
  const digits = str.split('')

  const [display, setDisplay] = useState<string[]>(() => digits.map(d => (/\d/.test(d) ? randomDigit() : d)))
  const settledRef = useRef<string>('')

  useEffect(() => {
    const target = str
    if (settledRef.current === target && replayKey === undefined) return

    const numericIdx = digits.map((d, i) => (/\d/.test(d) ? i : -1)).filter(i => i >= 0)
    if (numericIdx.length === 0) {
      setDisplay(digits)
      settledRef.current = target
      return
    }

    let frame = 0
    const timer = window.setInterval(() => {
      frame++
      // digits settle left-to-right: digit i settles after i * stagger ticks
      const settledCount = Math.floor((frame * tickMs) / settleStaggerMs)
      const next = digits.map((d, i) => {
        if (!/\d/.test(d)) return d
        const order = numericIdx.indexOf(i)
        return order < settledCount ? d : randomDigit()
      })
      setDisplay(next)
      if (settledCount >= numericIdx.length) {
        setDisplay(digits)
        settledRef.current = target
        window.clearInterval(timer)
      }
    }, tickMs)

    return () => window.clearInterval(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [str, replayKey])

  return (
    <span className={`slotnum ${className || ''}`} style={style} aria-label={str}>
      {display.map((d, i) => (
        <span key={i} className={d === digits[i] ? 'slot-digit settled' : 'slot-digit spinning'}>
          {d}
        </span>
      ))}
    </span>
  )
}

function randomDigit(): string {
  return String(Math.floor(Math.random() * 10))
}
