import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/ws': {
        target: 'ws://127.0.0.1:8000',
        ws: true
      },
      '/recordings': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/snapshots': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/evidence': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      }
    }
  },
  preview: {
    port: 5173,
    host: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/ws': {
        target: 'ws://127.0.0.1:8000',
        ws: true
      },
      '/recordings': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/snapshots': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/evidence': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      }
    }
  }
})
