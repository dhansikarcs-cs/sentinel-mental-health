/**
 * Durable ring-reading queue (IndexedDB).
 *
 * Why: Render's free tier sleeps; a POST made during cold start can 502/timeout,
 * and a closed tab must not lose readings. Records are persisted BEFORE any
 * network call and removed ONLY after a confirmed 2xx.
 *
 * Safety net: the ring itself stores history, so even if every push fails the
 * data still exists on the device and the next sync pulls it again. The `seq`
 * is deterministic, so replayed pushes are idempotent server-side (no dupes).
 */

import { api } from '../api/client'

const DB_NAME = 'sentinel-ring-queue'
const DB_VERSION = 1
const STORE = 'pending'

export type RingQueueKind = 'ring' | 'sensor'

export interface RingQueueEntry {
  client_id: string
  kind: RingQueueKind
  payload: Record<string, unknown>
  created_at: number
}

let _db: IDBDatabase | null = null
const _listeners: Array<() => void> = []

function notify() {
  _listeners.forEach((fn) => fn())
}

export function subscribeRingQueue(fn: () => void) {
  _listeners.push(fn)
  return () => {
    const i = _listeners.indexOf(fn)
    if (i >= 0) _listeners.splice(i, 1)
  }
}

function open(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    if (_db) return resolve(_db)
    const req = indexedDB.open(DB_NAME, DB_VERSION)
    req.onupgradeneeded = () => {
      const db = req.result
      if (!db.objectStoreNames.contains(STORE)) db.createObjectStore(STORE, { keyPath: 'client_id' })
    }
    req.onsuccess = () => {
      _db = req.result
      resolve(_db)
    }
    req.onerror = () => reject(req.error)
  })
}

async function tx<T>(mode: IDBTransactionMode, fn: (s: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  const db = await open()
  return new Promise<T>((resolve, reject) => {
    const req = fn(db.transaction(STORE, mode).objectStore(STORE))
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

/** Deterministic id -> re-syncing the same record never duplicates the queue. */
export function ringClientId(kind: RingQueueKind, seq: number, device: string): string {
  return `ring-${kind}-${device}-${seq}`
}

export async function enqueueRing(entries: Array<{ kind: RingQueueKind; payload: Record<string, unknown>; seq: number; device: string }>) {
  for (const e of entries) {
    const entry: RingQueueEntry = {
      client_id: ringClientId(e.kind, e.seq, e.device),
      kind: e.kind,
      payload: e.payload,
      created_at: Date.now(),
    }
    await tx('readwrite', (s) => s.put(entry))
  }
  notify()
}

export async function getRingQueueCount(): Promise<number> {
  try {
    const all = await tx<RingQueueEntry[]>('readonly', (s) => s.getAll() as IDBRequest<RingQueueEntry[]>)
    return all.length
  } catch {
    return 0
  }
}

export async function getRingQueueAll(): Promise<RingQueueEntry[]> {
  try {
    const all = await tx<RingQueueEntry[]>('readonly', (s) => s.getAll() as IDBRequest<RingQueueEntry[]>)
    return all.sort((a, b) => a.created_at - b.created_at)
  } catch {
    return []
  }
}

async function remove(clientId: string): Promise<void> {
  await tx('readwrite', (s) => s.delete(clientId))
}

function isRetryable(err: unknown): boolean {
  const msg = err instanceof Error ? err.message : String(err)
  // Cold-start 502/503/504, network failure, or timeout -> worth retrying.
  return /50[234]|network|fetch|timeout|timed out|failed to fetch/i.test(msg)
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms))

export interface FlushResult {
  sent: number
  failed: number
  remaining: number
}

/**
 * Push queued records with backoff. Called on app load, after a sync, on
 * 'online', and periodically. Never removes an entry until HTTP 2xx.
 */
export async function flushRingQueue(attempts = 4): Promise<FlushResult> {
  const all = await getRingQueueAll()
  let sent = 0
  let failed = 0

  for (const entry of all) {
    let ok = false
    for (let attempt = 0; attempt < attempts && !ok; attempt++) {
      try {
        if (entry.kind === 'ring') await api.pushSensorData(entry.payload)
        else await api.createSensorReading(entry.payload)
        ok = true
      } catch (err) {
        if (!isRetryable(err) || attempt === attempts - 1) {
          failed++
          break
        }
        // Exponential-ish backoff for Render cold starts (~30-60 s).
        await sleep([1500, 4000, 9000, 15000][Math.min(attempt, 3)])
      }
    }
    if (ok) {
      await remove(entry.client_id)
      sent++
    }
  }
  notify()
  return { sent, failed, remaining: await getRingQueueCount() }
}

/** Probe the backend through the SAME path real requests use (needs a session). */
export async function warmBackend(): Promise<boolean> {
  for (let i = 0; i < 6; i++) {
    try {
      await api.getSensorData()
      return true
    } catch {
      /* cold start or not logged in yet */
      await sleep(3000)
    }
  }
  return false
}
