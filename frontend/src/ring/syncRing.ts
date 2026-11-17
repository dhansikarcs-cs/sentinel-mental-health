/**
 * One place that turns a Web Bluetooth session into durable, real readings.
 *
 * This ring does NOT retain stored history, so the only data source is the
 * LIVE 06 01 HR stream. Both the Dashboard card and the side-panel button go
 * through here, so device id, seq derivation and the "measured fields only"
 * rule can never diverge. Nothing is invented: a signal the ring did not
 * measure is left out of the payload entirely and stays NULL in the database.
 */

import { connectAndSync, startLiveHrStream, type ConnectResult } from './webBluetooth'
import { enqueueRing, flushRingQueue, type RingQueueKind } from './ringQueue'

export const DEVICE_ID = 'viaking_web_r30pro'
const SEQ_MAX = 2147483647

/** Deterministic seq from record identity -> replay-safe, no duplicates. */
export function seqFor(kind: string, id: string, value: string): number {
  const s = `${kind}:${id}:${value}`
  let h = 2166136261
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i)
    h = Math.imul(h, 16777619)
  }
  return (h >>> 0) % (SEQ_MAX - 1) + 1
}

export type RingSyncPhase = 'connecting' | 'measuring' | 'queued' | 'uploading'

export interface RingSyncOutcome {
  deviceName: string
  records: number // real measurements captured from the ring this session
  sent: number // delivered now (may include older queued items)
  remaining: number // still queued for automatic retry
  frameCount: number // raw frames received (diagnostic)
  opcodes: string[] // opcodes seen (diagnostic)
}

type QueueEntry = { kind: RingQueueKind; payload: Record<string, unknown>; seq: number; device: string }

function buildEntries(result: ConnectResult): QueueEntry[] {
  const entries: QueueEntry[] = []
  // LIVE HR only. No spo2 / hrv / temperature / stress / sleep is derived —
  // those stay absent (NULL) unless the ring actually measures them.
  for (const r of result.hr) {
    const seq = seqFor('hr', r.id, String(r.bpm))
    entries.push({
      kind: 'ring',
      seq,
      device: DEVICE_ID,
      payload: { device_id: DEVICE_ID, seq, bpm: r.bpm, timestamp: new Date().toISOString() },
    })
  }
  return entries
}

/**
 * Bounded sync: connect, persist locally FIRST, then try to deliver. Never
 * throws away data: a failing server only leaves records in the durable queue.
 */
export async function syncRingNow(
  onPhase?: (phase: RingSyncPhase, records?: number) => void,
): Promise<RingSyncOutcome> {
  onPhase?.('connecting')
  const result = await connectAndSync(45000, (n) => onPhase?.('measuring', n))
  const entries = buildEntries(result)
  await enqueueRing(entries)
  onPhase?.('queued', entries.length)
  onPhase?.('uploading', entries.length)
  const flushed = await flushRingQueue()
  return {
    deviceName: result.deviceName,
    records: entries.length,
    sent: flushed.sent,
    remaining: flushed.remaining,
    frameCount: result.frameCount,
    opcodes: result.opcodes,
  }
}

/* ── Continuous live session ──────────────────────────────────────────────
   A singleton, NOT React state, so collapsing the side panel or navigating
   does NOT stop collection. It keeps running as long as this browser TAB is
   open (Web Bluetooth cannot run in a service worker / background tab).
   Every reading is queued in IndexedDB BEFORE the network call, so closing
   the tab cannot lose a reading that was already captured.                    */

export interface LiveSyncState {
  running: boolean
  count: number // genuine readings captured from 06 01 frames
  lastBpm: number | null
  frames: number // raw BLE frames seen (diagnostic)
  opcodes: string[] // opcodes seen (diagnostic)
  error: string
}

let _session: { stop: () => Promise<void> } | null = null
let _state: LiveSyncState = { running: false, count: 0, lastBpm: null, frames: 0, opcodes: [], error: '' }
const _subs = new Set<(s: LiveSyncState) => void>()

function emit() { _subs.forEach((f) => f(_state)) }

export function subscribeLiveSync(fn: (s: LiveSyncState) => void) {
  _subs.add(fn)
  fn(_state)
  return () => { _subs.delete(fn) }
}

export function getLiveSyncState(): LiveSyncState { return _state }

export async function startLiveSync(): Promise<void> {
  if (_session) return
  _state = { running: true, count: 0, lastBpm: null, frames: 0, opcodes: [], error: '' }
  emit()
  let n = 0
  const seenOpcodes = new Set<string>()
  try {
    const session = await startLiveHrStream(
      async (bpm, rawHex) => {
        n += 1
        const seq = seqFor('live', `${rawHex}:${n}`, String(bpm))
        await enqueueRing([{
          kind: 'ring',
          seq,
          device: DEVICE_ID,
          payload: { device_id: DEVICE_ID, seq, bpm, timestamp: new Date().toISOString() },
        }])
        void flushRingQueue().catch(() => {})
        _state = { ..._state, count: n, lastBpm: bpm }
        emit()
      },
      // Every CRC-valid frame is counted so the UI can say WHERE a sync stalled:
      // 0 frames => GATT/notify problem; frames but no 0601 => ring not worn.
      (f) => {
        seenOpcodes.add(f.opcode)
        _state = { ..._state, frames: _state.frames + 1, opcodes: Array.from(seenOpcodes).sort() }
        emit()
      },
    )
    _session = { stop: session.stop }
  } catch (err) {
    _state = { running: false, count: n, lastBpm: _state.lastBpm, frames: _state.frames, opcodes: Array.from(seenOpcodes).sort(), error: describeRingError(err) }
    emit()
    throw err
  }
}

export async function stopLiveSync(): Promise<void> {
  const s = _session
  _session = null
  if (s) await s.stop().catch(() => {})
  _state = { ..._state, running: false }
  emit()
}

/** Turn a Web Bluetooth failure into something a patient can actually act on. */
export function describeRingError(err: unknown): string {
  const e = err as { name?: string; message?: string } | undefined
  const name = e?.name || ''
  const raw = (e?.message || String(err)).toLowerCase()

  switch (name) {
    case 'NotFoundError':
      return 'No ring selected — the picker was closed, or no ring was advertising nearby.'
    case 'NotSupportedError':
      return 'Bluetooth is not supported on this browser/device. Use Chrome or Edge.'
    case 'SecurityError':
      return 'Bluetooth was blocked. Open Sentinel over HTTPS (or localhost).'
    case 'NetworkError':
      return "Couldn't reach the ring — is it charged, out of its case, and within ~10 m?"
    case 'InvalidStateError':
      return 'The ring disconnected mid-sync — bring it closer and try again.'
    default:
      break
  }
  if (/no device|not found|cancel/.test(raw)) {
    return 'No ring selected — the picker was closed, or none was found nearby.'
  }
  if (/no gatt/.test(raw)) return 'That device is not the ring — pick the "R30 PRO" entry.'
  if (/gatt|disconnect|connect/.test(raw)) {
    return "Couldn't stay connected to the ring — bring it closer and retry."
  }
  if (/https|bluetooth|localhost|unavailable/.test(raw)) {
    return 'Web Bluetooth unavailable — use Chrome/Edge over HTTPS or localhost.'
  }
  return e?.message || String(err)
}
