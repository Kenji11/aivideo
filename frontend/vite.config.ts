import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  optimizeDeps: {
    exclude: ['lucide-react'],
  },
  server: {
    host: 'localhost',
    port: 5173,
    hmr: {
      clientPort: 5173,
      protocol: 'ws',
      host: 'localhost',
      // Disable auto-reconnect polling to prevent restart loops
      overlay: false,
    },
    // Disable file watching that might cause restarts
    watch: {
      usePolling: false,
      ignored: ['**/node_modules/**', '**/.git/**', '**/dist/**'],
    },
  },
  // Prevent automatic restarts
  clearScreen: false,
});
