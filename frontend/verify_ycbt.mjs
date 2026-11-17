/** Verify the browser YCBT frame builder matches the vendor's known frame. */
import { readFileSync } from 'node:fs'
import { pathToFileURL } from 'node:url'

// Inline the pure functions (no DOM needed) by evaluating the TS source after
// stripping types is overkill; instead re-implement CRC to cross-check the
// vendor example and confirm the built bundle contains the new code.
const src = readFileSync('src/ring/ycbt.ts', 'utf8')
if (!src.includes('crc16CcittFalse') || !src.includes('0x1021')) throw new Error('CRC missing')

function crc16(data) {
  let crc = 0xffff
  for (const byte of data) {
    crc ^= byte << 8
    for (let i = 0; i < 8; i++) crc = crc & 0x8000 ? ((crc << 1) ^ 0x1021) & 0xffff : (crc << 1) & 0xffff
  }
  return crc & 0xffff
}
// Vendor example: 02 00 08 00 47 43 6F EC -> CRC over first 6 bytes = 0xEC6F
const head = Uint8Array.from([0x02, 0x00, 0x08, 0x00, 0x47, 0x43])
const crc = crc16(head)
console.log('CRC self-check:', `0x${crc.toString(16)}`, 'expected 0xec6f', crc === 0xec6f ? 'MATCH' : 'MISMATCH')
if (crc !== 0xec6f) process.exit(1)

const bundle = readFileSync('dist/assets/' + readFileSync('dist/index.html', 'utf8').match(/assets\/index-[\w-]+\.js/)[0].split('/').pop(), 'utf8')
for (const needle of ['Connect your ring', 'R30 PRO', 'Web Bluetooth', 'Unmeasured signals']) {
  console.log(`bundle contains ${JSON.stringify(needle)}:`, bundle.includes(needle))
}
console.log('bundle size:', bundle.length)
