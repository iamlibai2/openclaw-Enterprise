import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  test: {
    // 使用 happy-dom 作为测试环境
    environment: 'happy-dom',

    // 全局变量
    globals: true,

    // 覆盖率配置
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'tests/',
        '**/*.d.ts',
        '**/*.config.*',
        '**/index.ts',
      ],
    },

    // 包含的测试文件
    include: ['tests/**/*.{test,spec}.{js,ts,vue}'],

    // 排除的文件
    exclude: ['node_modules/', 'dist/'],
  },

  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
})