import { fileURLToPath, URL } from 'node:url'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  // GitHub Actions 上发布到 https://<owner>.github.io/job-matching/。
  // 本地 dev 和 pnpm build 仍用根路径。
  base: process.env.GITHUB_ACTIONS ? '/job-matching/' : '/',
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  build: {
    // Element Plus 体积较大,MVP 阶段先放宽告警阈值
    chunkSizeWarningLimit: 1500,
  },
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts'],
  },
})
