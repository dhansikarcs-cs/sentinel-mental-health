import { useEffect, useRef, useState } from 'react'

export interface SelectOption {
  value: string
  label: string
  disabled?: boolean
  hint?: string
}

interface CustomSelectProps {
  value: string
  onChange: (value: string) => void
  options: SelectOption[]
  placeholder?: string
  disabled?: boolean
  style?: React.CSSProperties
  invalid?: boolean
  searchable?: boolean
}

/**
 * Custom dropdown — replaces the native <select> so dark mode and theming
 * look consistent. Supports keyboard navigation, type-ahead search and
 * disabled/hinted options.
 */
export default function CustomSelect({
  value, onChange, options, placeholder = 'Select…', disabled, style, invalid, searchable = false,
}: CustomSelectProps) {
  const [open, setOpen] = useState(false)
  const [highlight, setHighlight] = useState(-1)
  const [query, setQuery] = useState('')
  const wrapRef = useRef<HTMLDivElement>(null)
  const listRef = useRef<HTMLDivElement>(null)

  const selected = options.find(o => o.value === value)
  const filtered = query
    ? options.filter(o => o.label.toLowerCase().includes(query.toLowerCase()))
    : options

  useEffect(() => {
    if (!open) { setQuery(''); setHighlight(-1); return }
    const onDocClick = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onDocClick)
    return () => document.removeEventListener('mousedown', onDocClick)
  }, [open])

  // Scroll highlighted option into view
  useEffect(() => {
    if (open && highlight >= 0 && listRef.current) {
      const el = listRef.current.querySelector(`[data-idx="${highlight}"]`)
      el?.scrollIntoView({ block: 'nearest' })
    }
  }, [highlight, open])

  function commit(v: string) {
    onChange(v)
    setOpen(false)
  }

  function onKey(e: React.KeyboardEvent) {
    if (disabled) return
    if (!open) {
      if (e.key === 'Enter' || e.key === ' ' || e.key === 'ArrowDown') {
        e.preventDefault(); setOpen(true)
        setHighlight(options.findIndex(o => o.value === value))
      }
      return
    }
    if (e.key === 'Escape') { e.preventDefault(); setOpen(false) }
    else if (e.key === 'ArrowDown') {
      e.preventDefault()
      setHighlight(h => {
        let n = h + 1
        while (n < filtered.length && filtered[n].disabled) n++
        return Math.min(n, filtered.length - 1)
      })
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setHighlight(h => {
        let n = h - 1
        while (n >= 0 && filtered[n].disabled) n--
        return Math.max(n, 0)
      })
    } else if (e.key === 'Enter') {
      e.preventDefault()
      if (filtered[highlight] && !filtered[highlight].disabled) commit(filtered[highlight].value)
    } else if (e.key === 'Tab') { setOpen(false) }
  }

  return (
    <div ref={wrapRef} style={{ position: 'relative', ...style }} data-custom-select>
      <button
        type="button"
        className="custom-select-trigger"
        style={invalid ? { borderColor: 'var(--danger) !important' } : undefined}
        disabled={disabled}
        onClick={() => setOpen(o => !o)}
        onKeyDown={onKey}
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {selected ? selected.label : <span style={{ color: 'var(--faint)' }}>{placeholder}</span>}
        </span>
        <svg
          width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
          strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"
          style={{ flexShrink: 0, transition: 'transform 0.18s ease', transform: open ? 'rotate(180deg)' : 'none', opacity: 0.65 }}
        >
          <path d="M6 9l6 6 6-6" />
        </svg>
      </button>

      {open && (
        <div className="custom-select-menu" role="listbox">
          {searchable && options.length > 8 && (
            <div style={{ padding: '8px 10px 4px' }}>
              <input
                autoFocus
                value={query}
                onChange={e => { setQuery(e.target.value); setHighlight(0) }}
                onKeyDown={onKey}
                placeholder="Search…"
                style={{ width: '100%', padding: '7px 10px', fontSize: '0.8rem' }}
              />
            </div>
          )}
          <div ref={listRef} style={{ maxHeight: '260px', overflowY: 'auto', padding: '6px' }}>
            {filtered.length === 0 && (
              <div style={{ padding: '10px 12px', color: 'var(--faint)', fontSize: '0.8rem' }}>No matches</div>
            )}
            {filtered.map((o, i) => {
              const isSel = o.value === value
              const isHi = i === highlight
              return (
                <div
                  key={o.value}
                  data-idx={i}
                  role="option"
                  aria-selected={isSel}
                  className={`custom-select-option${isSel ? ' selected' : ''}${isHi ? ' highlighted' : ''}`}
                  style={o.disabled ? { opacity: 0.45, cursor: 'not-allowed' } : undefined}
                  onClick={() => { if (!o.disabled) commit(o.value) }}
                  onMouseEnter={() => !o.disabled && setHighlight(i)}
                >
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{o.label}</span>
                  {isSel && (
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
                      <path d="M20 6L9 17l-5-5" />
                    </svg>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
