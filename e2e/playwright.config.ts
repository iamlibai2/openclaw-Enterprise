import { defineConfig, devices } from '@playwright/test';

/**
 * E2E 测试配置
 *
 * 运行命令：
 * npx playwright test          # 运行所有测试
 * npx playwright test --ui     # UI 模式
 * npx playwright test --headed # 有界面模式
 */
export default defineConfig({
  // 测试目录
  testDir: './tests',

  // 完全并行运行测试
  fullyParallel: true,

  // CI 上失败时禁止 test.only
  forbidOnly: !!process.env.CI,

  // CI 上重试失败测试
  retries: process.env.CI ? 2 : 0,

  // 测试超时时间（毫秒）
  timeout: 60000,

  // beforeEach/afterEach 超时时间
  expect: {
    timeout: 10000,
  },

  // 限制并发 workers，避免登录状态冲突
  workers: 1,

  // Reporter 配置
  reporter: [
    ['html', { outputFolder: 'report' }],
    ['list']
  ],

  // 全局设置
  use: {
    // 基础 URL
    baseURL: 'http://localhost:5000',

    // 每个测试使用新的浏览器上下文
    storageState: undefined,

    // 收集失败测试的 trace
    trace: 'on-first-retry',

    // 截图
    screenshot: 'only-on-failure',

    // 视频录制
    video: 'retain-on-failure',
  },

  // 配置项目（浏览器）
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
      // 完全并行运行，每个测试独立上下文
      fullyParallel: true,
    },
    // 可以取消注释以测试其他浏览器
    // {
    //   name: 'firefox',
    //   use: { ...devices['Desktop Firefox'] },
    // },
    // {
    //   name: 'webkit',
    //   use: { ...devices['Desktop Safari'] },
    // },
  ],

  // 启动前端开发服务器（可选）
  // webServer: {
  //   command: 'npm run dev',
  //   url: 'http://localhost:5000',
  //   reuseExistingServer: !process.env.CI,
  // },
});