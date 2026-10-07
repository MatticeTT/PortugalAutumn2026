import { defineConfig } from 'vite'
import { resolve } from 'node:path'

export default defineConfig({
  build: {
    chunkSizeWarningLimit: 1500,
    rollupOptions: {
      input: { main: resolve(__dirname, 'index.html'), rekenen: resolve(__dirname, 'rekenen.html'), controle: resolve(__dirname, 'controle.html') },
    },
  },
})
