import { useEffect, useState } from 'react'

import { isWebBluetoothSupported, bluetoothDiagnostics } from '../ring/webBluetooth'
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
 * Full-width "Connect ring" card for the patient Dashboard.
 *
 * This ring does NOT keep stored history, so the only way to capture readings
 * is a LIVE Web Bluetooth session: keep this browser tab open while the ring
 * is worn. Every 06 01 measurement is written to the durable IndexedDB queue
 * BEFORE the network call, so a closed tab never loses a captured reading.
 *
 * The session is a module-level singleton in ring/syncRing.ts — collapsing a
 * panel or navigating between pages does NOT stop collection.
 *
 * Only genuinely measured fields are sent. Nothing is estimated or simulated.
 */

export default function RingConnect({ onSynced }: { onSynced?: () => void }) {
  const [pending, setPending] = useState(0)
  const [live, setLive] = useState<LiveSyncState>(getLiveSyncState())
  const [busy, setBusy] = useState(false)
  const [bootDiag] = useState(() => bluetoothDiagnostics().line)
  const supported = isWebBluetoothSupported()

  useEffect(() => {
    getRingQueueCount().then(setPending)
    const unsubQ = subscribeRingQueue(() => { void getRingQueueCount().then(setPending) })
    const unsubLive = subscribeLiveSync((s) => {
      setLive(s)
      if (s.count > 0) onSynced?.()
    })
    // Flush anything left from a previous session / closed tab.
    void flushRingQueue().then((r) => { if (r.sent > 0) onSynced?.() })
    const onOnline = () => { void flushRingQueue() }
    window.addEventListener('online', onOnline)
    const timer = window.setInterval(() => { void flushRingQueue() }, 60000)
    return () => {
      unsubQ()
      unsubLive()
      window.removeEventListener('online', onOnline)
      window.clearInterval(timer)
    }
  }, [onSynced])

  async function toggle() {
    if (busy) return
    setBusy(true)
    try {
      if (live.running) await stopLiveSync()
      else await startLiveSync()
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="card" style={{ padding: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
        <div>
          <div style={{ fontSize: '0.8125rem', color: 'var(--secondary)', fontWeight: 600 }}>💍 Live ring collection</div>
          <div style={{ fontSize: '0.7rem', color: 'var(--muted)', marginTop: '4px', lineHeight: 1.5 }}>
            This ring does not store history — readings are captured live while this tab stays open and the ring is worn. Nothing is estimated or simulated.
          </div>
          <div style={{ fontSize: '0.66rem', color: 'var(--secondary)', marginTop: '4px' }}>
            Readings will be saved to <strong>@{getUser()?.username || 'this account'}</strong>.
          </div>
        </div>
        <button
          type="button"
          className="btn-primary"
          onClick={toggle}
          disabled={!supported || busy}
          style={{ padding: '9px 16px', fontSize: '0.8125rem' }}
        >
          {busy ? 'Working…' : live.running ? '■ Stop collecting' : '▶ Start collecting'}
        </button>
      </div>

      {live.running && (
        <div style={{ marginTop: '10px', fontSize: '0.72rem', lineHeight: 1.6, color: 'var(--ok)' }}>
          🔴 Collecting live — {live.count} real reading{live.count === 1 ? '' : 's'} captured
          {live.lastBpm !== null ? ` · last bpm ${live.lastBpm}` : ' · waiting for a measurement (wear the ring, sensors against skin)'}.
          {' '}{live.frames} BLE frame{live.frames === 1 ? '' : 's'} seen{live.opcodes.length ? ` (${live.opcodes.join(', ')})` : ''}.
          Keep this tab open. Each reading is saved locally and uploaded immediately.
        </div>
      )}
      {!live.running && live.frames > 0 && (
        <div style={{ marginTop: '10px', fontSize: '0.72rem', lineHeight: 1.6, color: 'var(--warn)' }}>
          Last session: {live.frames} BLE frames ({live.opcodes.join(', ') || 'none'}) → {live.count} real readings.
          {live.count === 0 ? ' The ring sent no 06 01 HR frames — check it is worn, charged, and out of its case.' : ''}
        </div>
      )}
      {live.error && !live.running && (
        <div style={{ marginTop: '10px', fontSize: '0.72rem', lineHeight: 1.5, color: 'var(--danger)' }}>{live.error}</div>
      )}
      <div style={{ marginTop: '10px', fontSize: '0.66rem', lineHeight: 1.5, color: 'var(--faint)', wordBreak: 'break-word' }}>
        🔎 {live.diag || bootDiag}
      </div>
      {pending > 0 && (
        <div style={{ marginTop: '10px', fontSize: '0.7rem', color: 'var(--warn)' }}>
          📡 {pending} measurement{pending === 1 ? '' : 's'} waiting to upload — retrying automatically.
        </div>
      )}
      {!supported && (
        <div style={{ marginTop: '10px', fontSize: '0.7rem', color: 'var(--warn)', lineHeight: 1.5 }}>
          This browser can't use Bluetooth. Open Sentinel in Chrome or Edge over HTTPS (or localhost), with the ring nearby. Safari, Firefox and iOS have no Web Bluetooth. Android needs Location ON + "Nearby devices" permission for Chrome. In the picker choose the "R30 PRO" entry.
        </div>
      )}
      <div style={{ marginTop: '10px', fontSize: '0.66rem', color: 'var(--faint)', lineHeight: 1.5 }}>
        A hosted server has no Bluetooth: collection cannot run in the background or with the tab closed. For unattended 24/7 capture, a dedicated always-on gateway device near the ring is required.
      </div>
    </div>
  )
}
