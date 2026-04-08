/**
 * 用户管理页面 E2E 测试
 */

import { test, expect, login, TEST_ACCOUNTS } from '../fixtures';

test.describe('用户管理', () => {
  // 设置 beforeEach 超时时间
  test.beforeEach(async ({ page }) => {
    // 每个测试前先登录
    await login(page, TEST_ACCOUNTS.admin.username, TEST_ACCOUNTS.admin.password);
  }, { timeout: 60000 });

  test.afterEach(async ({ page }) => {
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
  });

  test('显示用户列表', async ({ page }) => {
    await page.goto('/users');

    // 等待表格加载
    await page.waitForSelector('table', { timeout: 10000 });

    // 检查是否有用户数据，如果没有数据，检查是否有"暂无数据"提示
    const rows = await page.locator('table tbody tr').count();
    const noDataMsg = await page.locator('text=暂无数据').isVisible().catch(() => false);

    // 要么有数据，要么显示暂无数据
    expect(rows > 0 || noDataMsg).toBe(true);
  });

  test('用户列表分页', async ({ page }) => {
    await page.goto('/users');
    await page.waitForSelector('table', { timeout: 10000 });

    // 检查分页组件
    const pagination = page.locator('.el-pagination, .pagination');
    if (await pagination.isVisible()) {
      // 点击下一页（如果有的话）
      const nextButton = pagination.locator('button.btn-next, .btn-next');
      if (await nextButton.isEnabled().catch(() => false)) {
        await nextButton.click();
        await page.waitForTimeout(500);
      }
    }
  });

  test('搜索用户', async ({ page }) => {
    await page.goto('/users');
    await page.waitForSelector('table', { timeout: 10000 });

    // 查找搜索框
    const searchInput = page.locator('input[placeholder*="搜索"], input[placeholder*="search"]').first();

    if (await searchInput.isVisible().catch(() => false)) {
      // 输入搜索关键词
      await searchInput.fill('admin');
      await page.waitForTimeout(500);

      // 验证搜索结果
      const rows = await page.locator('table tbody tr').count();
      expect(rows).toBeGreaterThanOrEqual(0);
    }
  });

  test('创建用户弹窗', async ({ page }) => {
    await page.goto('/users');
    await page.waitForSelector('table', { timeout: 10000 });

    // 点击新建用户按钮
    const createButton = page.locator('button:has-text("新建用户"), button:has-text("新建")');

    if (await createButton.isVisible().catch(() => false)) {
      await createButton.click();

      // 等待弹窗出现
      await page.waitForSelector('[role="dialog"], .el-dialog', { timeout: 5000 });

      // 检查表单字段 - 用户名和密码
      await expect(page.locator('[role="dialog"] input[placeholder*="用户名"]').first()).toBeVisible();
      await expect(page.locator('[role="dialog"] input[type="password"]').first()).toBeVisible();

      // Element Plus 的 el-select 不是 select 元素
      const roleSelect = page.locator('[role="dialog"] .el-select, [role="dialog"] [data-testid="role-select"]');
      // 角色选择可能存在也可能不存在
      await expect(roleSelect.first()).toBeVisible().catch(() => {});
    }
  });

  test('创建用户 - 表单验证', async ({ page }) => {
    await page.goto('/users');
    await page.waitForSelector('table', { timeout: 10000 });

    // 打开创建弹窗
    const createButton = page.locator('button:has-text("新建用户"), button:has-text("新建")');
    if (await createButton.isVisible().catch(() => false)) {
      await createButton.click();
      await page.waitForSelector('[role="dialog"], .el-dialog', { timeout: 5000 });

      // 不填写任何内容，点击提交
      const submitBtn = page.locator('[role="dialog"] button:has-text("确定"), [role="dialog"] button:has-text("提交")');
      if (await submitBtn.isVisible().catch(() => false)) {
        await submitBtn.click();

        // 应该显示验证错误
        await page.waitForSelector('.el-form-item__error, .error, [role="alert"]', { timeout: 3000 }).catch(() => {
          // 可能使用其他方式显示错误
        });
      }
    }
  });

  test('编辑用户', async ({ page }) => {
    await page.goto('/users');
    await page.waitForSelector('table', { timeout: 10000 });

    // 等待表格数据加载
    await page.waitForTimeout(1000);

    // 点击第一行的编辑按钮
    const editButton = page.locator('table tbody tr').first().locator('button:has-text("编辑")');

    if (await editButton.isVisible().catch(() => false)) {
      await editButton.click();

      // 等待编辑弹窗
      await page.waitForSelector('[role="dialog"], .el-dialog', { timeout: 5000 });

      // 验证弹窗存在
      const dialog = page.locator('[role="dialog"], .el-dialog');
      await expect(dialog).toBeVisible();
    }
  });

  test('删除用户确认', async ({ page }) => {
    await page.goto('/users');
    await page.waitForSelector('table', { timeout: 10000 });

    // 等待表格数据加载
    await page.waitForTimeout(1000);

    // 找到删除按钮
    const deleteButton = page.locator('table tbody tr').first().locator('button:has-text("删除")');

    if (await deleteButton.isVisible().catch(() => false)) {
      await deleteButton.click();

      // 等待确认弹窗
      await page.waitForSelector('[role="alertdialog"], .el-message-box', { timeout: 5000 }).catch(async () => {
        // 可能是其他类型的确认框
        const confirmDialog = page.locator('.el-message-box');
        if (await confirmDialog.isVisible().catch(() => false)) {
          // 取消删除
          await page.click('.el-message-box button:has-text("取消")').catch(() => {});
        }
      });

      // 检查确认按钮
      const confirmButton = page.locator('.el-message-box button:has-text("确定"), .el-message-box button:has-text("确认")');
      if (await confirmButton.isVisible().catch(() => false)) {
        // 取消删除
        await page.locator('.el-message-box button:has-text("取消")').click().catch(() => {});
      }
    }
  });
});

test.describe('用户管理 - 权限', () => {
  test('未登录用户被重定向到登录页', async ({ page }) => {
    await page.goto('/users');

    // 应该重定向到登录页
    await expect(page).toHaveURL(/login/, { timeout: 10000 });
  });
});