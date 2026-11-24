import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/video': 'http://localhost:8000',
      '/scene': 'http://localhost:8000',
      '/character': 'http://localhost:8000',
      '/audiotrack': 'http://localhost:8000',
      '/subtitle': 'http://localhost:8000',
      '/playersettings': 'http://localhost:8000',
      '/animation': 'http://localhost:8000',
      '/media': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
      '/statistics': 'http://localhost:8000'
    }
  },
  build: {
    outDir: 'dist'
  }
})
