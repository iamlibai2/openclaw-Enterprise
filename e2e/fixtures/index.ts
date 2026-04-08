/**
 * E2E 测试 Fixtures
 *
 * 提供测试中常用的辅助函数和配置
 */

import { test as base, Page, BrowserContext } from '@playwright/test';

// 测试账号
export const TEST_ACCOUNTS = {
  admin: {
    username: 'admin',
    password: 'admin123',
  },
  operator: {
    username: 'operator',
    password: 'operator123',
  },
  viewer: {
    username: 'viewer',
    password: 'viewer123',
  },
};

// 扩展 base test
export const test = base.extend<{
  // 登录页面
  loginPage: Page;
  // 已登录的管理员页面
  adminPage: Page;
}>({
  // 登录页面 fixture
  loginPage: async ({ page }, use) => {
    await page.goto('/login');
    await use(page);
  },

  // 已登录的管理员页面 fixture
  adminPage: async ({ page }, use) => {
    // 访问登录页
    await page.goto('/login');

    // 等待登录表单加载
    await page.waitForSelector('input[placeholder*="用户名"]', { timeout: 10000 });

    // 填写登录表单
    await page.fill('input[placeholder*="用户名"]', TEST_ACCOUNTS.admin.username);
    await page.fill('input[placeholder*="密码"]', TEST_ACCOUNTS.admin.password);

    // 点击登录按钮
    await page.click('button:has-text("登录")');

    // 等待登录成功，跳转到首页
    await page.waitForURL(/\/(dashboard|home|users)/, { timeout: 15000 }).catch(() => {
      // 可能跳转到其他页面
    });

    await use(page);
  },
});

// 登录辅助函数 - 通过 API 直接登录（绕过 UI，更可靠）
export async function login(page: Page, username: string, password: string) {
  // 直接调用登录 API
  const response = await page.request.post('http://localhost:5001/api/auth/login', {
    headers: { 'Content-Type': 'application/json' },
    data: { username, password }
  });

  if (!response.ok()) {
    throw new Error(`Login API failed: ${response.status()}`);
  }

  const body = await response.json();
  if (!body.success && !body.data?.access_token) {
    throw new Error('Login API failed: ' + (body.error || 'No token returned'));
  }

  // 使用 addInitScript 在页面加载前注入 localStorage
  await page.addInitScript((data) => {
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('refresh_token', data.refresh_token);
    localStorage.setItem('user_info', JSON.stringify(data.user));
  }, body.data);

  // 导航到首页
  await page.goto('/');

  // 等待页面加载（不在登录页）
  await page.waitForURL(/^(?!.*\/login).*/, { timeout: 10000 });
}

// 登出辅助函数
export async function logout(page: Page) {
  // 点击用户头像/菜单
  await page.click('[data-testid="user-menu"], .user-avatar, .user-info').catch(() => {});
  // 点击登出按钮
  await page.click('text=退出, text=登出, text=Logout').catch(() => {});
}

// 等待 API 响应
export async function waitForAPI(page: Page, urlPattern: string | RegExp) {
  return page.waitForResponse((response) =>
    typeof urlPattern === 'string'
      ? response.url().includes(urlPattern)
      : urlPattern.test(response.url())
  );
}

// 检查 Toast 消息
export async function checkToast(page: Page, message: string) {
  await page.waitForSelector(`text=${message}`, { timeout: 5000 });
}

// 截图辅助
export async function takeScreenshot(page: Page, name: string) {
  await page.screenshot({ path: `screenshots/${name}.png`, fullPage: true });
}

// 获取表格数据
export async function getTableData(page: Page, tableSelector: string = 'table') {
  const rows = await page.locator(`${tableSelector} tbody tr`).all();
  const data: string[][] = [];

  for (const row of rows) {
    const cells = await row.locator('td').allTextContents();
    data.push(cells);
  }

  return data;
}

// 点击表格行操作按钮
export async function clickTableRowAction(
  page: Page,
  tableSelector: string,
  rowIndex: number,
  actionText: string
) {
  const row = page.locator(`${tableSelector} tbody tr`).nth(rowIndex);
  await row.click();
  await page.click(`button:has-text("${actionText}")`);
}

// 填写表单
export async function fillForm(page: Page, fields: Record<string, string>) {
  for (const [label, value] of Object.entries(fields)) {
    await page.fill(`label:has-text("${label}") + input, input[placeholder*="${label}"]`, value);
  }
}

export { expect } from '@playwright/test';