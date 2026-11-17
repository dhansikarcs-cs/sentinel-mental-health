import { useEffect, useState } from 'react'

import { isWebBluetoothSupported } from '../ring/webBluetooth'
import {
  startLiveSync,
  stopLiveSync,
  subscribeLiveSync,
  getLiveSyncState,
  type LiveSyncState,
} from '../ring/syncRing'
import { flushRingQueue, getRingQueueCount, subscribeRingQueue } from '../ring/ringQueue'
import { getUser } from '../stores/auth'

/**
 * Compact "Connect ring" control for the side panel.
 *
 * This ring does NOT store history, so collection is a LIVE Web Bluetooth
 * session that keeps running while this browser tab stays open. The session is
 * a module-level singleton in ring/syncRing.ts, so collapsing the panel does
 * not stop it. Every reading is queued in IndexedDB before any network call.
 *
 * It ALWAYS states its state instead of failing silently: not connected,
 * unsupported browser / insecure context, ring not worn, picker cancelled,
 * GATT link dropped, or server unreachable with records saved locally.
 * No value is ever invented.
 */

export default function RingConnectButton() {
  const supported = isWebBluetoothSupported()
  const [pending, setPending] = useState(0)
  const [live, setLive] = useState<LiveSyncState>(getLiveSyncState())
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    void getRingQueueCount().then(setPending)
    const unsubQ = subscribeRingQueue(() => { void getRingQueueCount().then(setPending) })
    const unsubLive = subscribeLiveSync(setLive)
    // A closed tab must not lose readings: retry whatever is still queued.
    void flushRingQueue()
    const onOnline = () => { void flushRingQueue() }
    window.addEventListener('online', onOnline)
    return () => {
      unsubQ()
      unsubLive()
      window.removeEventListener('online', onOnline)
    }
  }, [])

  async function toggle() {
    if (busy || !supported) return
    setBusy(true)
    try {
      if (live.running) await stopLiveSync()
      else await startLiveSync()
    } catch {
      /* the singleton publishes the friendly error into `live.error` */
    } finally {
      setBusy(false)
    }
  }

  const buttonLabel = busy ? '⏳ Working…' : live.running ? '■ Stop collecting' : '💍 Start collecting'

  // The panel must always SAY why it is not connected.
  const stateLine: { text: string; color: string } = (() => {
    if (!supported) {
      return { text: '⚠️ Bluetooth unavailable — open in Chrome/Edge over HTTPS (or localhost).', color: 'var(--warn)' }
    }
    if (busy) return { text: '🔵 Opening the ring picker…', color: 'var(--accent)' }
    if (live.error) return { text: `🔴 ${live.error} — tap to retry.`, color: 'var(--danger)' }
    if (live.running) {
      const diag = `${live.frames} frame${live.frames === 1 ? '' : 's'}${live.opcodes.length ? ` (${live.opcodes.join(', ')})` : ''}`
      return live.count > 0
        ? { text: `🟢 Collecting — ${live.count} real reading${live.count === 1 ? '' : 's'}${live.lastBpm !== null ? ` · last bpm ${live.lastBpm}` : ''}.`, color: 'var(--ok)' }
        : { text: `🔵 Connected — ${diag} seen, 0 readings yet. Wear the ring (sensors flat against skin) and keep this tab open.`, color: 'var(--accent)' }
    }
    if (live.frames > 0) {
      return { text: `🟡 Last session: ${live.frames} frames (${live.opcodes.join(', ') || 'none'}) but ${live.count} readings.`, color: 'var(--warn)' }
    }
    return { text: '🔴 Not collecting — tap to start live capture.', color: 'var(--muted)' }
  })()

  return (
    <div style={{ padding: '0 4px' }}>
      <button
        type="button"
        onClick={toggle}
        disabled={!supported || busy}
        title={supported ? 'Start a live Web Bluetooth session with your Viaking R30 PRO' : 'Web Bluetooth needs Chrome/Edge over HTTPS'}
        style={{
          width: '100%', padding: '7px 8px', fontSize: '0.7rem',
          background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '6px',
          color: 'var(--secondary)', cursor: supported && !busy ? 'pointer' : 'not-allowed',
          opacity: !supported || busy ? 0.6 : 1, transition: 'all 0.2s', boxShadow: 'none',
        }}
      >
        {buttonLabel}
      </button>
      <div style={{ fontSize: '0.625rem', lineHeight: 1.5, marginTop: '6px', color: stateLine.color }}>
        {stateLine.text}
      </div>
      {live.diag && (
        <div style={{ fontSize: '0.575rem', lineHeight: 1.5, marginTop: '6px', color: 'var(--faint)', wordBreak: 'break-word' }}>
          🔎 {live.diag}
        </div>
      )}
      <div style={{ fontSize: '0.6rem', lineHeight: 1.5, marginTop: '6px', color: 'var(--faint)' }}>
        Saving to <strong>@{getUser()?.username || 'this account'}</strong>. This ring doesn't store history, so readings are captured live while this tab stays open. Chrome/Edge over HTTPS with the ring nearby — the server has no Bluetooth. Safari/Firefox/iOS can't use Web Bluetooth. Android needs Location ON + "Nearby devices" permission for Chrome. In the picker choose the "R30 PRO" entry.
      </div>
      {pending > 0 && (
        <div style={{ fontSize: '0.625rem', lineHeight: 1.5, marginTop: '4px', color: 'var(--warn)' }}>
          📡 {pending} reading{pending === 1 ? '' : 's'} waiting to upload — retrying automatically.
        </div>
      )}
    </div>
  )
}
