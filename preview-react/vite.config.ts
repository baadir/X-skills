import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5731,
    proxy: {
      '/api': 'http://localhost:7731',
      '/visuals': 'http://localhost:7731',
    },
  },
  build: {
    outDir: '../preview/static-react',
    emptyOutDir: true,
  },
})
