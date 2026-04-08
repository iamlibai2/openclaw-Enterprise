# E2E 测试框架指南

## 概述

OpenClaw Control UI 使用 Playwright 进行端到端（E2E）测试。

### 技术栈

| 工具 | 版本 | 用途 |
|------|------|------|
| Playwright | 1.59.1 | E2E 测试框架 |
| TypeScript | ES2020 | 测试代码语言 |

---

## 文件结构

```
e2e/
├── playwright.config.ts    # Playwright 配置
├── package.json            # 依赖管理
├── tsconfig.json           # TypeScript 配置
├── .gitignore              # Git 忽略文件
├── fixtures/
│   └── index.ts            # 测试 Fixtures 和辅助函数
├── tests/
│   ├── login.spec.ts       # 登录测试
│   ├── users.spec.ts       # 用户管理测试
│   └── navigation.spec.ts  # 导航测试
├── .auth/                  # 认证状态存储
├── report/                 # HTML 测试报告
└── screenshots/            # 失败截图
```

---

## 运行测试

### 基本命令

```bash
# 进入 e2e 目录
cd /home/iamlibai/.openclaw/workspace-aqiang/openclaw-control-ui/e2e

# 运行所有测试
npm test

# UI 模式（推荐开发时使用）
npm run test:ui

# 有界面模式
npm run test:headed

# 调试模式
npm run test:debug

# 查看测试报告
npm run report

# 代码生成器
npm run codegen
```

### 运行特定测试

```bash
# 运行指定文件
npx playwright test login.spec.ts

# 运行指定测试
npx playwright test -g "登录"

# 运行指定浏览器
npx playwright test --project=chromium
```

---

## Fixtures 使用

### 测试账号

```typescript
import { TEST_ACCOUNTS } from '../fixtures';

// 使用管理员账号
TEST_ACCOUNTS.admin.username  // 'admin'
TEST_ACCOUNTS.admin.password  // 'admin123'
```

### 登录辅助函数

```typescript
import { login, logout } from '../fixtures';

// 登录
await login(page, 'admin', 'admin123');

// 登出
await logout(page);
```

### 已登录 Fixture

```typescript
import { test, expect, adminPage } from '../fixtures';

test('测试已登录状态', async ({ adminPage }) => {
  // adminPage 已经登录管理员账号
  await adminPage.goto('/users');
  // ...
});
```

---

## 编写测试

### 测试模板

```typescript
import { test, expect } from '../fixtures';

test.describe('功能模块名称', () => {
  test.beforeEach(async ({ page }) => {
    // 测试前置操作
  });

  test('测试用例描述', async ({ page }) => {
    // 1. 导航到页面
    await page.goto('/some-page');

    // 2. 执行操作
    await page.click('button');

    // 3. 验证结果
    await expect(page.locator('.result')).toBeVisible();
  });
});
```

### 常用选择器

```typescript
// 文本选择器
page.locator('text=登录')
page.locator('button:has-text("提交")')

// 属性选择器
page.locator('[data-testid="submit-button"]')
page.locator('input[name="username"]')

// CSS 选择器
page.locator('.class-name')
page.locator('#element-id')

// 组合选择器
page.locator('form >> input[type="text"]')
```

### 常用断言

```typescript
// 可见性
await expect(locator).toBeVisible()

// 文本内容
await expect(locator).toHaveText('期望文本')
await expect(locator).toContainText('部分文本')

// 属性
await expect(locator).toHaveAttribute('disabled', '')

// 数量
await expect(locator).toHaveCount(3)

// URL
await expect(page).toHaveURL('/users')

// 值
await expect(input).toHaveValue('input value')
```

### 等待策略

```typescript
// 等待元素
await page.waitForSelector('.element')

// 等待导航
await page.waitForURL('/new-page')

// 等待网络空闲
await page.waitForLoadState('networkidle')

// 等待响应
await page.waitForResponse('**/api/users')
```

---

## 测试策略

### 测试优先级

| 优先级 | 测试内容 | 说明 |
|--------|----------|------|
| P0 | 登录/登出 | 核心功能，必须通过 |
| P0 | 核心业务流程 | 用户管理、部门管理等 |
| P1 | 表单验证 | 创建、编辑表单验证 |
| P1 | 权限控制 | 未登录访问、权限不足 |
| P2 | UI 交互 | 弹窗、下拉菜单等 |
| P2 | 响应式布局 | 移动端适配 |

### 测试覆盖范围

- [x] 登录页面
- [x] 用户管理
- [x] 导航菜单
- [ ] 部门管理
- [ ] 员工管理
- [ ] 模型配置
- [ ] Gateway 管理
- [ ] 模板管理
- [ ] 系统配置

---

## 调试技巧

### 截图和视频

```typescript
// 手动截图
await page.screenshot({ path: 'screenshot.png' });

// 配置自动截图（playwright.config.ts）
use: {
  screenshot: 'only-on-failure',
  video: 'retain-on-failure',
}
```

### 调试模式

```bash
# 使用 Playwright Inspector
npx playwright test --debug

# 查看测试 trace
npx playwright show-trace trace.zip
```

### 控制台日志

```typescript
// 监听控制台
page.on('console', msg => console.log(msg.text()));

// 监听页面错误
page.on('pageerror', error => console.log(error));
```

---

## CI/CD 集成

### GitHub Actions

```yaml
name: E2E Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
      - run: npm ci
      - run: npx playwright install --with-deps
      - run: npm test
      - uses: actions/upload-artifact@v3
        if: always()
        with:
          name: playwright-report
          path: playwright-report/
```

---

## 常见问题

### 1. 元素找不到

```typescript
// 使用更宽松的等待
await page.waitForSelector('.element', { timeout: 10000 });

// 使用 text 选择器
await page.click('text=按钮文本');
```

### 2. 测试超时

```typescript
// 单个测试增加超时
test('慢测试', async ({ page }) => {
  // ...
}, { timeout: 30000 });
```

### 3. 环境差异

```typescript
// 检查环境变量
const baseUrl = process.env.BASE_URL || 'http://localhost:5000';
```

### 4. 登录流程问题（2026-04-08 发现）

**问题**：Element Plus 按钮 loading 状态、Vue 表单验证时机导致 UI 点击无效

**解决方案**：使用 API 登录 + `addInitScript` 注入 localStorage

```typescript
// fixtures/index.ts
export async function login(page: Page, username: string, password: string) {
  // 直接调用登录 API
  const response = await page.request.post('http://localhost:5001/api/auth/login', {
    headers: { 'Content-Type': 'application/json' },
    data: { username, password }
  });

  const body = await response.json();

  // 使用 addInitScript 在页面加载前注入 localStorage
  await page.addInitScript((data) => {
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('refresh_token', data.refresh_token);
    localStorage.setItem('user_info', JSON.stringify(data.user));
  }, body.data);

  // 导航到首页
  await page.goto('/');
  await page.waitForURL(/^(?!.*\/login).*/, { timeout: 10000 });
}
```

### 5. 速率限制问题

**问题**：后端登录接口限制每分钟 5 次请求，测试会触发 429 错误

**解决方案**：
- 测试之间增加等待时间
- 使用多个测试账号分散请求
- 测试环境使用独立后端实例