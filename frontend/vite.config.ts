import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// API target for dev-proxying. Override with VITE_API_TARGET if port 8000 is
// taken by another project, e.g.:
//   VITE_API_TARGET=http://localhost:8001 npm run dev
const apiTarget = process.env.VITE_API_TARGET || 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': { target: apiTarget, changeOrigin: true },
    },
  },
})
