/**
 * Yucheng YCBT protocol helpers, ported from hardware_lab/ycbt.py.
 *
 * Frame: [type:1][cmd:1][len:u16 LE][payload][crc16:u16 LE]
 * CRC = CRC16/CCITT-FALSE (poly 0x1021, init 0xFFFF, no reflection).
 * len = TOTAL frame length (header + payload + crc).
 *
 * Opcodes were recovered from the vendor SDK AAR, not guessed.
 */

export const YCBT_SERVICE = 'be940000-7333-be46-b7ae-689e71722bd5'
export const CMD_CHAR = 'be940001-7333-be46-b7ae-689e71722bd5'
export const STREAM_CHAR = 'be940003-7333-be46-b7ae-689e71722bd5'

// Vendor Get tags (empty-payload Gets return 0xFE "Data error").
export const GET_TAGS: Record<number, string> = { 0x00: '4743', 0x01: '4746', 0x03: '4750', 0x28: '4746' }

export const OPTIONAL_SERVICES = [YCBT_SERVICE]

export function crc16CcittFalse(data: Uint8Array): number {
  let crc = 0xffff
  for (const byte of data) {
    crc ^= byte << 8
    for (let i = 0; i < 8; i++) {
      crc = crc & 0x8000 ? ((crc << 1) ^ 0x1021) & 0xffff : (crc << 1) & 0xffff
    }
  }
  return crc & 0xffff
}

export function fromHex(hex: string): Uint8Array {
  const out = new Uint8Array(hex.length / 2)
  for (let i = 0; i < out.length; i++) out[i] = parseInt(hex.slice(i * 2, i * 2 + 2), 16)
  return out
}

export function toHex(bytes: Uint8Array): string {
  return Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('')
}

export function frame(type: number, cmd: number, payload: Uint8Array = new Uint8Array()): Uint8Array {
  const total = 4 + payload.length + 2
  const head = new Uint8Array(4 + payload.length)
  head[0] = type
  head[1] = cmd
  head[2] = total & 0xff
  head[3] = (total >> 8) & 0xff
  head.set(payload, 4)
  const crc = crc16CcittFalse(head)
  const out = new Uint8Array(total)
  out.set(head, 0)
  out[total - 2] = crc & 0xff
  out[total - 1] = (crc >> 8) & 0xff
  return out
}

export interface ParsedFrame {
  opcode: string
  payloadHex: string
  crcOk: boolean
  rawHex: string
}

export function parseFrame(raw: Uint8Array): ParsedFrame | null {
  if (raw.length < 6) return null
  const declared = raw[2] | (raw[3] << 8)
  if (declared !== raw.length || declared > 512) return null
  const crcGot = raw[raw.length - 2] | (raw[raw.length - 1] << 8)
  const crcCalc = crc16CcittFalse(raw.slice(0, raw.length - 2))
  return {
    opcode: toHex(raw.slice(0, 2)),
    payloadHex: toHex(raw.slice(4, raw.length - 2)),
    crcOk: crcGot === crcCalc,
    rawHex: toHex(raw),
  }
}

/** Seconds since 2000-01-01 in LOCAL wall-clock (vendor convention). */
export function epoch2000Local(): Uint8Array {
  const utcSeconds = Math.floor(Date.now() / 1000) - 946684800
  const localSeconds = utcSeconds - new Date().getTimezoneOffset() * 60
  const b = new Uint8Array(4)
  const v = new DataView(b.buffer)
  v.setUint32(0, localSeconds >>> 0, true)
  return b
}

export interface HrRecord {
  bpm: number
  id: string
}

export interface CombinedRecord {
  bpm: number | null
  spo2: number | null
  hrv: number | null
  temperatureC: number | null
  systolic: number | null
  diastolic: number | null
  id: string
}

/** 0515 data: N x 6 B = [ts:u32][sep][bpm]. */
export function decodeHrHistory(payload: Uint8Array): HrRecord[] {
  const out: HrRecord[] = []
  for (let i = 0; i + 5 < payload.length; i += 6) {
    const bpm = payload[i + 5]
    if (bpm >= 30 && bpm <= 250) {
      const id = toHex(payload.slice(i, i + 4))
      out.push({ bpm, id })
    }
  }
  return out
}

/** 0518 data: N x 20 B. Vendor doc 3367-3437 offsets; zero fields ignored. */
export function decodeCombined(payload: Uint8Array): CombinedRecord[] {
  const out: CombinedRecord[] = []
  for (let i = 0; i + 19 < payload.length; i += 20) {
    const r = payload.slice(i, i + 20)
    const ti = r[13]
    const tf = r[14]
    const temperatureC = ti !== 0 && tf !== 15 ? parseFloat(`${ti}.${tf}`) : null
    out.push({
      bpm: r[6] || null,
      spo2: r[9] || null,
      hrv: r[11] || null,
      temperatureC,
      systolic: r[7] || null,
      diastolic: r[8] || null,
      id: toHex(r.slice(0, 4)),
    })
  }
  return out
}

export interface SyncResult {
  hr: HrRecord[]
  combined: CombinedRecord[]
  rawFrames: string[]
}

export function extractRecords(frames: ParsedFrame[]): SyncResult {
  const hrMap = new Map<string, HrRecord>()
  const cbMap = new Map<string, CombinedRecord>()
  const rawFrames: string[] = []
  for (const f of frames) {
    if (!f.crcOk) continue
    rawFrames.push(f.rawHex)
    const p = fromHex(f.payloadHex)
    if (f.opcode === '0515') {
      for (const r of decodeHrHistory(p)) hrMap.set(`${r.id}-${r.bpm}`, r)
    } else if (f.opcode === '0518') {
      for (const r of decodeCombined(p)) {
        cbMap.set(`${r.id}-${r.bpm}-${r.spo2}-${r.hrv}-${r.temperatureC}`, r)
      }
    }
  }
  return { hr: Array.from(hrMap.values()), combined: Array.from(cbMap.values()), rawFrames }
}
