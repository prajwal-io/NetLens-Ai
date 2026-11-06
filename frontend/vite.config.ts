import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
export default defineConfig({
 plugins: [react(), tailwindcss()],
 server: { proxy: { '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true } } },
 preview: { headers: { 'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'strict-origin-when-cross-origin', 'Permissions-Policy': 'camera=(), microphone=(), geolocation=()' }, proxy: { '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true } } },
 build: { rollupOptions: { output: {
  onlyExplicitManualChunks: true,
  manualChunks(id) {
   if (!id.includes('node_modules')) return;
   if (/\/(react|react-dom|react-router|react-router-dom|scheduler|use-sync-external-store)\//.test(id)) return 'react-vendor';
   if (/\/(motion|motion-dom|motion-utils|framer-motion)\//.test(id)) return 'motion';
  }
 } } }
})