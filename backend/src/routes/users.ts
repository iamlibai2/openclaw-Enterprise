import { Router, Request, Response } from 'express';
import { body, validationResult } from 'express-validator';
import { authMiddleware, requirePermission } from '../auth';
import { listUsers, findUserById, updateUser, deleteUser, createLog } from '../database';

const router = Router();

// 所有用户路由都需要认证
router.use(authMiddleware);

// 获取用户列表（需要 users:read 权限）
router.get('/', requirePermission('users:read'), async (req: Request, res: Response) => {
  try {
    const users = await listUsers();

    // 记录查看日志
    await createLog({
      user_id: req.user!.userId,
      username: req.user!.username,
      action: 'list_users',
      resource: 'users',
      details: `查看用户列表，共 ${users.length} 个用户`,
      ip_address: req.ip || 'unknown',
      status: 'success'
    });

    // 过滤敏感信息
    const safeUsers = users.map(u => ({
      id: u.id,
      username: u.username,
      email: u.email,
      role: u.role,
      status: u.status,
      created_at: u.created_at,
      last_login_at: u.last_login_at,
      login_count: u.login_count
    }));

    return res.json({ success: true, users: safeUsers });
  } catch (error) {
    return res.status(500).json({ success: false, message: '获取用户列表失败' });
  }
});

// 获取单个用户详情
router.get('/:id', requirePermission('users:read'), async (req: Request, res: Response) => {
  try {
    const user = await findUserById(req.params.id);

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
        created_at: user.created_at,
        last_login_at: user.last_login_at,
        login_count: user.login_count
      }
    });
  } catch (error) {
    return res.status(500).json({ success: false, message: '获取用户信息失败' });
  }
});

// 更新用户信息
router.patch(
  '/:id',
  requirePermission('users:write'),
  [
    body('email').optional().isEmail().withMessage('邮箱格式不正确'),
    body('role').optional().isIn(['admin', 'operator', 'viewer']).withMessage('角色不合法'),
    body('status').optional().isIn(['active', 'inactive', 'locked']).withMessage('状态不合法')
  ],
  async (req: Request, res: Response) => {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({ success: false, errors: errors.array() });
    }

    try {
      const existing = await findUserById(req.params.id);
      if (!existing) {
        return res.status(404).json({ success: false, message: '用户不存在' });
      }

      // 不能修改自己的角色为更低级别（防止管理员把自己降级）
      if (req.params.id === req.user!.userId && req.body.role) {
        const roleHierarchy = { admin: 3, operator: 2, viewer: 1 };
        const currentLevel = roleHierarchy[req.user!.role as keyof typeof roleHierarchy];
        const newLevel = roleHierarchy[req.body.role as keyof typeof roleHierarchy];

        if (newLevel < currentLevel) {
          return res.status(400).json({ success: false, message: '不能降低自己的角色级别' });
        }
      }

      const updates: any = {};
      if (req.body.email) updates.email = req.body.email;
      if (req.body.role) updates.role = req.body.role;
      if (req.body.status) updates.status = req.body.status;

      const updated = await updateUser(req.params.id, updates);

      await createLog({
        user_id: req.user!.userId,
        username: req.user!.username,
        action: 'update_user',
        resource: 'users',
        resource_id: req.params.id,
        details: `更新用户: ${existing.username}, 修改: ${JSON.stringify(updates)}`,
        ip_address: req.ip || 'unknown',
        status: 'success'
      });

      return res.json({
        success: true,
        user: {
          id: updated!.id,
          username: updated!.username,
          email: updated!.email,
          role: updated!.role,
          status: updated!.status
        }
      });
    } catch (error) {
      return res.status(500).json({ success: false, message: '更新用户失败' });
    }
  }
);

// 删除用户
router.delete('/:id', requirePermission('users:delete'), async (req: Request, res: Response) => {
  try {
    const existing = await findUserById(req.params.id);

    if (!existing) {
      return res.status(404).json({ success: false, message: '用户不存在' });
    }

    // 不能删除自己
    if (req.params.id === req.user!.userId) {
      return res.status(400).json({ success: false, message: '不能删除自己的账户' });
    }

    // 不能删除最后一个管理员
    const users = await listUsers();
    const adminCount = users.filter(u => u.role === 'admin' && u.status === 'active').length;
    if (existing.role === 'admin' && adminCount <= 1) {
      return res.status(400).json({ success: false, message: '不能删除最后一个管理员' });
    }

    await deleteUser(req.params.id);

    await createLog({
      user_id: req.user!.userId,
      username: req.user!.username,
      action: 'delete_user',
      resource: 'users',
      resource_id: req.params.id,
      details: `删除用户: ${existing.username}`,
      ip_address: req.ip || 'unknown',
      status: 'success'
    });

    return res.json({ success: true, message: '用户已删除' });
  } catch (error) {
    return res.status(500).json({ success: false, message: '删除用户失败' });
  }
});

export default router;