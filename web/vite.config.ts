import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 开发服务器将 /api 代理到后端 FastAPI（默认 8000 端口）
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
