import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './index.css'

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch((err) => {
      console.warn('[PWA] Service worker registration failed:', err)
    })
  })
}

// Keep the Render free-tier services warm while this tab is open.
// Free instances sleep after ~15 min idle and the cold start can exceed
// Render's proxy timeout (surfacing as 502); a light ping every 5 minutes
// from any open tab prevents that during a live session.
function startKeepWarm() {
  const PING_INTERVAL_MS = 5 * 60 * 1000
  const ping = () => {
    fetch('/api/ai/health', { headers: { Accept: 'application/json' } }).catch(() => {})
  }
  ping()
  window.setInterval(ping, PING_INTERVAL_MS)
}
if (typeof window !== 'undefined') startKeepWarm()

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
)
