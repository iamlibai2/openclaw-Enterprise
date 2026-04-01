import { Router, Request, Response } from 'express';
import { body, validationResult } from 'express-validator';
import { handleLogin, authMiddleware } from '../auth';
import { createUser, findUserByUsername, findUserById, createLog, invalidateSession } from '../database';
import bcrypt from 'bcryptjs';

const router = Router();

// 登录
router.post(
  '/login',
  [
    body('username').notEmpty().withMessage('用户名不能为空'),
    body('password').notEmpty().withMessage('密码不能为空')
  ],
  async (req: Request, res: Response) => {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({ success: false, errors: errors.array() });
    }

    const { username, password } = req.body;
    const ipAddress = req.ip || 'unknown';

    const result = await handleLogin(username, password, ipAddress);

    if (result.success) {
      return res.json(result);
    } else {
      return res.status(401).json(result);
    }
  }
);

// 注册（仅管理员可用）
router.post(
  '/register',
  authMiddleware,
  [
    body('username').notEmpty().isAlphanumeric().withMessage('用户名只能包含字母和数字'),
    body('email').isEmail().withMessage('邮箱格式不正确'),
    body('password').isLength({ min: 6 }).withMessage('密码至少6位'),
    body('role').optional().isIn(['admin', 'operator', 'viewer']).withMessage('角色不合法')
  ],
  async (req: Request, res: Response) => {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({ success: false, errors: errors.array() });
    }

    // 权限检查：只有管理员可以创建用户
    if (req.user?.role !== 'admin') {
      return res.status(403).json({ success: false, message: '只有管理员可以创建用户' });
    }

    const { username, email, password, role } = req.body;

    // 检查用户是否已存在
    const existing = await findUserByUsername(username);
    if (existing) {
      return res.status(400).json({ success: false, message: '用户名已存在' });
    }

    try {
      const user = await createUser({
        username,
        email,
        password_hash: password,
        role: role || 'viewer'
      });

      // 记录创建用户日志
      await createLog({
        user_id: req.user!.userId,
        username: req.user!.username,
        action: 'create_user',
        resource: 'users',
        resource_id: user.id,
        details: `创建用户: ${username}`,
        ip_address: req.ip || 'unknown',
        status: 'success'
      });

      return res.json({
        success: true,
        user: {
          id: user.id,
          username: user.username,
          email: user.email,
          role: user.role
        }
      });
    } catch (error) {
      return res.status(500).json({ success: false, message: '创建用户失败' });
    }
  }
);

// 获取当前用户信息
router.get('/me', authMiddleware, async (req: Request, res: Response) => {
  if (!req.user) {
    return res.status(401).json({ success: false, message: '未认证' });
  }

  const user = await findUserById(req.user.userId);

  if (!user) {
    return res.status(404).json({ success: false, message: '用户不存在' });
  }

  return res.json({
    success: true,
    user: {
      id: user.id,
      username: user.username,
      email: user.email,
      role: user.role,
      status: user.status,
      last_login_at: user.last_login_at,
      login_count: user.login_count
    }
  });
});

// 修改密码
router.post(
  '/change-password',
  authMiddleware,
  [
    body('oldPassword').notEmpty().withMessage('旧密码不能为空'),
    body('newPassword').isLength({ min: 6 }).withMessage('新密码至少6位')
  ],
  async (req: Request, res: Response) => {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({ success: false, errors: errors.array() });
    }

    if (!req.user) {
      return res.status(401).json({ success: false, message: '未认证' });
    }

    const { oldPassword, newPassword } = req.body;
    const user = await findUserById(req.user.userId);

    if (!user) {
      return res.status(404).json({ success: false, message: '用户不存在' });
    }

    // 验证旧密码
    const isValid = await bcrypt.compare(oldPassword, user.password_hash);
    if (!isValid) {
      return res.status(400).json({ success: false, message: '旧密码不正确' });
    }

    // 更新密码
    const newHash = bcrypt.hashSync(newPassword, 10);
    await updateUserPassword(user.id, newHash);

    // 记录日志
    await createLog({
      user_id: user.id,
      username: user.username,
      action: 'change_password',
      resource: 'auth',
      details: '密码修改成功',
      ip_address: req.ip || 'unknown',
      status: 'success'
    });

    return res.json({ success: true, message: '密码修改成功' });
  }
);

// 登出
router.post('/logout', authMiddleware, async (req: Request, res: Response) => {
  if (!req.user) {
    return res.status(401).json({ success: false, message: '未认证' });
  }

  const authHeader = req.headers.authorization;
  if (authHeader) {
    const token = authHeader.substring(7);
    const tokenHash = bcrypt.hashSync(token, 10);
    await invalidateSession(tokenHash);
  }

  await createLog({
    user_id: req.user.userId,
    username: req.user.username,
    action: 'logout',
    resource: 'auth',
    details: '登出成功',
    ip_address: req.ip || 'unknown',
    status: 'success'
  });

  return res.json({ success: true, message: '登出成功' });
});

// 辅助函数：更新密码
async function updateUserPassword(userId: string, passwordHash: string): Promise<void> {
  const db = require('../database').default;
  const now = new Date().toISOString();

  return new Promise((resolve, reject) => {
    db.run(
      'UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?',
      [passwordHash, now, userId],
      (err: Error | null) => {
        if (err) reject(err);
        else resolve();
      }
    );
  });
}

export default router;