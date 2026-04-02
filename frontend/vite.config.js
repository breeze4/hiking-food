import path from 'path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  base: '/hiking-food/',
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    proxy: {
      '/hiking-food/api': {
        target: 'http://localhost:8000',
        rewrite: (path) => path.replace(/^\/hiking-food/, ''),
      },
    },
  },
})
