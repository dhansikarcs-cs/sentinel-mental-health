import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { flushRingQueue } from './ring/ringQueue'
import './index.css'

// A closed tab / sleeping Render backend must not lose ring readings. Retry
// the durable queue as soon as the app boots, and whenever connectivity returns.
void flushRingQueue()
window.addEventListener('online', () => { void flushRingQueue() })

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch((err) => {
      console.warn('[PWA] Service worker registration failed:', err)
    })
  })
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
)
