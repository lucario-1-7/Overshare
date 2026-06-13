import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In dev, proxy the API routes to the FastAPI backend so the frontend can use
// relative URLs (works the same when the built app is served from the same origin
// behind the Cloudflare tunnel in Phase 6). Override the target with VITE_API_BASE.
const API = process.env.VITE_API_BASE || 'http://localhost:8077'
const proxy = Object.fromEntries(
  ['/analyze', '/health', '/sample-report', '/extras'].map((p) => [
    p,
    { target: API, changeOrigin: true },
  ]),
)

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy },
  preview: { port: 4173, proxy },
})
