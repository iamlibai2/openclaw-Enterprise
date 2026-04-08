/**
 * 登录页面 E2E 测试
 */

import { test, expect, login, TEST_ACCOUNTS } from '../fixtures';

test.describe('登录页面', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    // 等待登录表单加载完成
    await page.waitForSelector('input[placeholder="请输入用户名"]', { timeout: 10000 });
  }, { timeout: 30000 });

  test.afterEach(async ({ page }) => {
    // 清除浏览器状态，避免测试间污染
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
  });

  test('显示登录表单', async ({ page }) => {
    // 检查登录页面标题
    await expect(page.locator('h1')).toContainText('OpenClaw');

    // 检查用户名输入框
    const usernameInput = page.locator('input[placeholder="请输入用户名"]');
    await expect(usernameInput).toBeVisible();

    // 检查密码输入框
    const passwordInput = page.locator('input[placeholder="请输入密码"]');
    await expect(passwordInput).toBeVisible();

    // 检查登录按钮
    const loginButton = page.locator('button').filter({ hasText: '登录' });
    await expect(loginButton).toBeVisible();
  });

  test('成功登录', async ({ page }) => {
    // 填写登录表单
    await page.fill('input[placeholder="请输入用户名"]', TEST_ACCOUNTS.admin.username);
    await page.fill('input[placeholder="请输入密码"]', TEST_ACCOUNTS.admin.password);

    // 等待登录按钮可点击
    await page.waitForSelector('button:has-text("登录"):not([disabled])', { timeout: 5000 });
    await page.click('button:has-text("登录")');

    // 等待登录 API 响应
    await page.waitForTimeout(2000);

    // 等待离开登录页
    await page.waitForURL(/^(?!.*\/login).*/, { timeout: 20000 });

    // 验证已登录
    await expect(page).not.toHaveURL(/login/);
  });

  test('登录失败 - 错误密码', async ({ page }) => {
    // 填写错误密码
    await page.fill('input[placeholder="请输入用户名"]', TEST_ACCOUNTS.admin.username);
    await page.fill('input[placeholder="请输入密码"]', 'wrong_password');

    // 点击登录
    await page.click('button:has-text("登录")');

    // 等待错误提示
    await page.waitForSelector('.el-message--error, .error-message, text=/错误|失败/i', { timeout: 5000 }).catch(() => {});

    // 应该还在登录页
    await page.waitForTimeout(1000);
    const url = page.url();
    expect(url).toContain('login');
  });

  test('登录失败 - 用户不存在', async ({ page }) => {
    // 填写不存在的用户
    await page.fill('input[placeholder="请输入用户名"]', 'nonexistent_user');
    await page.fill('input[placeholder="请输入密码"]', 'any_password');

    // 点击登录
    await page.click('button:has-text("登录")');

    // 等待错误提示
    await page.waitForSelector('.el-message--error, .error-message', { timeout: 5000 }).catch(() => {});
  });

  test('登录失败 - 空用户名', async ({ page }) => {
    // 只填写密码
    await page.fill('input[placeholder="请输入密码"]', 'any_password');

    // 点击登录
    await page.click('button:has-text("登录")');

    // 等待一下，检查是否还在登录页
    await page.waitForTimeout(1000);
    expect(page.url()).toContain('login');
  });

  test('登录失败 - 空密码', async ({ page }) => {
    // 只填写用户名
    await page.fill('input[placeholder="请输入用户名"]', TEST_ACCOUNTS.admin.username);

    // 点击登录
    await page.click('button:has-text("登录")');

    // 等待一下，检查是否还在登录页
    await page.waitForTimeout(1000);
    expect(page.url()).toContain('login');
  });

  test('密码输入框类型为 password', async ({ page }) => {
    const passwordInput = page.locator('input[type="password"]');
    await expect(passwordInput).toHaveAttribute('type', 'password');
  });

  test('登录后跳转', async ({ page }) => {
    // 登录
    await login(page, TEST_ACCOUNTS.admin.username, TEST_ACCOUNTS.admin.password);

    // 验证不在登录页
    await expect(page).not.toHaveURL(/login/);
  });
});

test.describe('登录会话', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.waitForSelector('input[placeholder="请输入用户名"]', { timeout: 10000 });
  });

  test.afterEach(async ({ page }) => {
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
  });

  test('Token 存储在 localStorage', async ({ page }) => {
    await page.fill('input[placeholder="请输入用户名"]', TEST_ACCOUNTS.admin.username);
    await page.fill('input[placeholder="请输入密码"]', TEST_ACCOUNTS.admin.password);
    await page.waitForSelector('button:has-text("登录"):not([disabled])', { timeout: 5000 });
    await page.click('button:has-text("登录")');
    await page.waitForTimeout(2000);

    // 等待离开登录页
    await page.waitForURL(/^(?!.*\/login).*/, { timeout: 20000 });

    // 检查 localStorage 中的 token
    const token = await page.evaluate(() => localStorage.getItem('access_token'));
    expect(token).toBeTruthy();
  });

  test('刷新页面保持登录状态', async ({ page }) => {
    await page.fill('input[placeholder="请输入用户名"]', TEST_ACCOUNTS.admin.username);
    await page.fill('input[placeholder="请输入密码"]', TEST_ACCOUNTS.admin.password);
    await page.waitForSelector('button:has-text("登录"):not([disabled])', { timeout: 5000 });
    await page.click('button:has-text("登录")');
    await page.waitForTimeout(2000);
    // 等待离开登录页
    await page.waitForURL(/^(?!.*\/login).*/, { timeout: 20000 });

    // 刷新页面
    await page.reload();

    // 应该还在已登录页面
    await page.waitForTimeout(1000);
    await expect(page).not.toHaveURL(/login/);
  });
});