import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      // Forward REST API calls to FastAPI backend
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      // Forward WebSocket connections to FastAPI backend
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
      // Forward health & metrics endpoints
      '/health': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/live': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/metrics': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
