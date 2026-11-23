import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Requests to /api are forwarded to the Django server, so the browser only
// ever talks to one address and the server needs no CORS configuration.
const server = 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, strictPort: true, proxy: { '/api': server } },
  preview: { port: 5173, strictPort: true, proxy: { '/api': server } },
})
