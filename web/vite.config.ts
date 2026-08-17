import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The bundle is package data: `collective web` serves it from inside the
// installed package (or the zipapp), so the build lands in src/collective.
export default defineConfig({
  plugins: [react()],
  // Absolute base: the server answers unknown paths with the app shell, and a
  // shell served at a nested path must still resolve its assets from the root.
  base: '/',
  build: { outDir: '../src/collective/static', emptyOutDir: true },
  server: { proxy: { '/api': 'http://127.0.0.1:8788' } },
})
