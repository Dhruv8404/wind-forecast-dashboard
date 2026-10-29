import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],

  // ── Development server ──────────────────────────────────────────────────
  server: {
    port: 5173,
    host: 'localhost',          // Change to '0.0.0.0' if running Vite inside Docker
    proxy: {
      // Forwards /api/* to the FastAPI backend during local development.
      // In production (Docker), Nginx handles this proxying instead.
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      }
    }
  },

  // ── Production build ────────────────────────────────────────────────────
  build: {
    outDir: 'dist',             // Nginx COPY --from=builder /app/dist
    sourcemap: false,           // Disable sourcemaps in production
    chunkSizeWarningLimit: 800, // Raise Rollup chunk-size warning threshold (kB)
  },
})
