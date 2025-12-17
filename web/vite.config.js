import { fileURLToPath, URL } from "node:url"
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue(),
    AutoImport({
      resolvers: [ElementPlusResolver()],
    }),
    Components({
      resolvers: [ElementPlusResolver()],
    }),
  ],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url))
    }
  },
  devtools: { enabled: true },
  server: {
    // /** Set host: true to use Network to access projects with IP */
    // host: true, // host: "0.0.0.0"
    // /** Port number */
    // port: 5173,
    // /** Whether to automatically open the browser */
    // open: false,
    /** Cross-domain settings allow */
    // cors: true,
    /** When the port is occupied, will it be directly exited */
    strictPort: false,
    //hmr: {port: 5000}, 
    /** Interface Agent */
      allowedHosts: true,
      proxy: {
        "/socket.io": {
          target: "http://192.168.1.2:5000",
          ws: true,
        },
      },
    },
})
