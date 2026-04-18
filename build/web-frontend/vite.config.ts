import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Bind dev server to localhost (not 127.0.0.1) so host matches backend cookies
    host: 'localhost',
    // Open explicitly at localhost to avoid terminal link resolving to 127.0.0.1
    open: 'http://localhost:5173',
    // Proxy API requests to backend to keep same-origin during dev
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/setupTests.ts',
    include: ['src/**/*.test.{ts,tsx}'],
  },
})
