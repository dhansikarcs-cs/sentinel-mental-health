/**
 * Browser-side BLE connection to the Viaking R30 PRO.
 *
 * IMPORTANT: a hosted server has NO Bluetooth. Web Bluetooth runs on the
 * PATIENT'S device (Chrome/Edge, HTTPS or localhost, user gesture) and the
 * ring must be within ~10 m of THAT device.
 *
 * This unit does NOT retain stored history (verified on hardware: history
 * queries returned no records). So we use the LIVE HR stream instead:
 *   requestDevice -> GATT connect -> subscribe to YCBT cmd + stream ->
 *   documented handshake -> 03 2F start HR measurement -> collect 06 01
 *   frames (CRC-validated, bpm = payload[0]) -> 03 2F stop -> decode.
 *
 * Only documented/verified YCBT opcodes are written (set_time, vendor Get
 * tags, broadcast_enable, measurement start/stop). No DFU, no reset, no OTA,
 * no history deletes, no terminal ACK, no unknown writes. Raw frames are
 * preserved. Nothing is invented: a signal not measured is left out.
 */

import {
  CMD_CHAR,
  GET_TAGS,
  OPTIONAL_SERVICES,
  STREAM_CHAR,
  YCBT_SERVICE,
  epoch2000Local,
  fromHex,
  frame,
  parseFrame,
  type ParsedFrame,
  type SyncResult,
} from './ycbt'

// Minimal Web Bluetooth types (not in the TS DOM lib).
interface BleCharacteristic {
  startNotifications(): Promise<BleCharacteristic>
  stopNotifications(): Promise<BleCharacteristic>
  writeValueWithoutResponse(value: BufferSource): Promise<void>
  writeValueWithResponse(value: BufferSource): Promise<void>
  addEventListener(type: 'characteristicvaluechanged', listener: (ev: Event) => void): void
  removeEventListener(type: 'characteristicvaluechanged', listener: (ev: Event) => void): void
  value?: DataView
}
interface BleService {
  getCharacteristic(uuid: string): Promise<BleCharacteristic>
}
interface BleServer {
  connect(): Promise<BleServer>
  disconnect(): void
  getPrimaryService(uuid: string): Promise<BleService>
  connected: boolean
}
interface BleDevice {
  id: string
  name?: string
  gatt?: BleServer
}
interface BleBluetooth {
  requestDevice(options: {
    filters?: Array<{ namePrefix?: string; services?: string[] }>
    optionalServices?: string[]
    acceptAllDevices?: boolean
  }): Promise<BleDevice>
}
interface BleNavigator {
  bluetooth?: BleBluetooth
}

export function isWebBluetoothSupported(): boolean {
  return typeof navigator !== 'undefined' && !!(navigator as unknown as BleNavigator).bluetooth
}

function delay(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms))
}

/** Reassemble frames split across notifications using the declared length. */
function makeCollector(onFrame: (f: ParsedFrame) => void) {
  let buf = new Uint8Array(0)
  return (ev: Event) => {
    const target = ev.target as BleCharacteristic | null
    if (!target?.value) return
    const chunk = new Uint8Array(target.value.buffer, target.value.byteOffset, target.value.byteLength)
    const merged = new Uint8Array(buf.length + chunk.length)
    merged.set(buf, 0)
    merged.set(chunk, buf.length)
    buf = merged
    while (buf.length >= 4) {
      const declared = buf[2] | (buf[3] << 8)
      if (declared < 6 || declared > 512) {
        buf = new Uint8Array(0)
        return
      }
      if (buf.length < declared) return
      const one = buf.slice(0, declared)
      buf = buf.slice(declared)
      const parsed = parseFrame(one)
      if (parsed?.crcOk) onFrame(parsed)
    }
  }
}

async function write(char: BleCharacteristic, bytes: Uint8Array): Promise<void> {
  // Copy into a plain ArrayBuffer so the type is BufferSource-compatible
  // (Uint8Array<ArrayBufferLike> is not assignable in TS 5.6+).
  const buf = new ArrayBuffer(bytes.length)
  new Uint8Array(buf).set(bytes)
  try {
    await char.writeValueWithoutResponse(buf)
  } catch {
    await char.writeValueWithResponse(buf)
  }
}

export interface ConnectResult extends SyncResult {
  deviceName: string
  deviceId: string
  /** Raw frames seen and their opcodes — diagnostic only, never invented. */
  frameCount: number
  opcodes: string[]
}

export interface LiveSession {
  deviceName: string
  deviceId: string
  stop: () => Promise<void>
}

// Documented in hardware_lab/ycbt.py and proven on this unit: start HR
// measurement (03 2F 01 00) and the reversible stop (03 2F 00 00).
const HR_START = new Uint8Array([0x01, 0x00])
const HR_STOP = new Uint8Array([0x00, 0x00])

/** Decode a CRC-validated 06 01 frame. bpm = payload[0]. */
export function decodeLiveHr(f: ParsedFrame): number | null {
  if (f.opcode !== '0601' || !f.crcOk) return null
  const p = fromHex(f.payloadHex)
  const bpm = p.length ? p[0] : 0
  return bpm >= 30 && bpm <= 250 ? bpm : null
}

/**
 * Open ONE GATT connection and keep streaming live HR until stop() is called.
 * Must be called from a user gesture (click handler). Each measurement is
 * delivered to onReading immediately, so the caller can persist it durably.
 */
export async function startLiveHrStream(
  onReading: (bpm: number, rawHex: string) => void,
  onFrame?: (f: ParsedFrame) => void,
): Promise<LiveSession> {
  const bluetooth = (navigator as unknown as BleNavigator).bluetooth
  if (!bluetooth) throw new Error('Web Bluetooth unavailable. Use Chrome/Edge on HTTPS or localhost.')

  // Advertised name is not stable: "R30 PRO F085", " F085", "R30PRO".
  // Filters are OR'd; the standard Heart Rate service guarantees it appears.
  const device = await bluetooth.requestDevice({
    filters: [{ namePrefix: 'R30 PRO' }, { namePrefix: 'F085' }, { services: ['heart_rate'] }],
    optionalServices: OPTIONAL_SERVICES,
  })
  if (!device.gatt) throw new Error('Device has no GATT server')
  const server = await device.gatt.connect()
  const service = await server.getPrimaryService(YCBT_SERVICE)
  const cmd = await service.getCharacteristic(CMD_CHAR)
  const stream = await service.getCharacteristic(STREAM_CHAR)

  // One collector PER characteristic (proven Python gateway does the same).
  // 06 01 arrives on stream; 03 2F echoes and status arrive on cmd.
  const cmdHandler = makeCollector((f) => onFrame?.(f))
  const streamHandler = makeCollector((f) => {
    onFrame?.(f)
    const bpm = decodeLiveHr(f)
    if (bpm !== null) onReading(bpm, f.rawHex)
  })
  await cmd.startNotifications()
  await stream.startNotifications()
  cmd.addEventListener('characteristicvaluechanged', cmdHandler)
  stream.addEventListener('characteristicvaluechanged', streamHandler)

  // Documented handshake (same as the proven sync_history.py), then start HR.
  try {
    await write(cmd, frame(0x01, 0x00, epoch2000Local()))
    await delay(700)
    for (const [xx, tag] of Object.entries(GET_TAGS)) {
      await write(cmd, frame(0x02, Number(xx), fromHex(tag)))
      await delay(700)
    }
    await write(cmd, frame(0x03, 0x09))
    await delay(700)
    await write(cmd, frame(0x03, 0x2F, HR_START))
    await delay(300)
  } catch (err) {
    // Clean up a half-open session before propagating.
    cmd.removeEventListener('characteristicvaluechanged', cmdHandler)
    stream.removeEventListener('characteristicvaluechanged', streamHandler)
    try { await cmd.stopNotifications(); await stream.stopNotifications() } catch { /* disconnected */ }
    server.disconnect()
    throw err
  }

  let stopped = false
  const stop = async () => {
    if (stopped) return
    stopped = true
    try { await write(cmd, frame(0x03, 0x2F, HR_STOP)) } catch { /* already gone */ }
    cmd.removeEventListener('characteristicvaluechanged', cmdHandler)
    stream.removeEventListener('characteristicvaluechanged', streamHandler)
    try { await cmd.stopNotifications(); await stream.stopNotifications() } catch { /* disconnected */ }
    server.disconnect()
  }
  return { deviceName: device.name || 'R30 PRO', deviceId: device.id, stop }
}

/**
 * Bounded one-shot sync: connect, measure live for durationMs, stop, decode.
 * Kept so the Connect ring button still has a simple click-and-finish mode.
 */
export async function connectAndSync(
  durationMs = 45000,
  onProgress?: (readings: number) => void,
): Promise<ConnectResult> {
  const hr: { bpm: number; id: string }[] = []
  const rawFrames: string[] = []
  const opcodes = new Set<string>()
  let frameCount = 0
  const session = await startLiveHrStream(
    (bpm, rawHex) => {
      hr.push({ bpm, id: rawHex })
      rawFrames.push(rawHex)
      onProgress?.(hr.length)
    },
    (f) => { frameCount++; opcodes.add(f.opcode) },
  )
  try {
    await delay(durationMs)
  } finally {
    await session.stop()
  }
  const seen = new Set<string>()
  const unique = hr.filter((r) => {
    if (seen.has(r.id)) return false
    seen.add(r.id)
    return true
  })
  return {
    deviceName: session.deviceName,
    deviceId: session.deviceId,
    frameCount,
    opcodes: Array.from(opcodes).sort(),
    hr: unique,
    combined: [],
    rawFrames,
  }
}
