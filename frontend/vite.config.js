import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    headers: {
      // Matches index.html meta: OnlyOffice’s client script uses `unload` in this document.
      'Permissions-Policy': 'unload=(self)',
    },
  },
  preview: {
    headers: {
      'Permissions-Policy': 'unload=(self)',
    },
  },
})
