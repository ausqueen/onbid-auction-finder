import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// VITE_HTTPS=false 로 설정하면 HTTP 모드 (Windows 로컬 개발용, 기본값)
// VITE_PORT 로 포트 오버라이드 가능
const useHttps = process.env.VITE_HTTPS === 'true'
const defaultPort = useHttps ? 443 : 5173
const port = parseInt(process.env.VITE_PORT || String(defaultPort))
const backendPort = process.env.VITE_BACKEND_PORT || '8001'

async function getPlugins() {
  if (useHttps) {
    const { default: basicSsl } = await import('@vitejs/plugin-basic-ssl')
    return [react(), basicSsl()]
  }
  return [react()]
}

export default defineConfig(async () => ({
  plugins: await getPlugins(),
  server: {
    host: '0.0.0.0',
    port,
    proxy: {
      '/api': {
        target: `http://127.0.0.1:${backendPort}`,
        changeOrigin: true,
      },
    },
  },
}))
