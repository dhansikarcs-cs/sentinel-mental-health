import { readFileSync } from 'node:fs'
const html = readFileSync('dist/index.html', 'utf8')
const m = html.match(/assets\/index-[\w-]+\.js/)
const b = readFileSync('dist/' + m[0], 'utf8')
for (const n of ['Connect your ring', 'waiting to upload', 'Backend is waking up', 'cold start', 'sentinel-ring-queue']) {
  console.log(`contains ${JSON.stringify(n)}:`, b.includes(n))
}
console.log('bundle bytes:', b.length)
