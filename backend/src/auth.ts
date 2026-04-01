import jwt from 'jsonwebtoken';
import bcrypt from 'bcryptjs';
import { Request, Response, NextFunction } from 'express';
import { JWTPayload, User } from './types';
import { findUserById, updateLoginInfo, createSession, createLog, hasPermission } from './database';

const JWT_SECRET = process.env.JWT_SECRET || 'openclaw-secret-key-change-in-production';
const JWT_EXPIRES_IN = process.env.JWT_EXPIRES_IN || '24h';

// 生成 JWT Token
export function generateToken(user: User): string {
  const payload: JWTPayload = {
    userId: user.id,
    username: user.username,
    role: user.role,
    permissions: []
  };

  return jwt.sign(payload, JWT_SECRET, { expiresIn: JWT_EXPIRES_IN });
}

// 验证密码
export async function verifyPassword(password: string, hash: string): Promise<boolean> {
  return bcrypt.compare(password, hash);
}

// JWT 认证中间件
export async function authMiddleware(req: Request, res: Response, next: NextFunction): Promise<void> {
  const authHeader = req.headers.authorization;

  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    res.status(401).json({ success: false, message: '未提供认证令牌' });
    return;
  }

  const token = authHeader.substring(7);

  try {
    const payload = jwt.verify(token, JWT_SECRET) as JWTPayload;
    req.user = payload;
    next();
  } catch (error) {
    res.status(401).json({ success: false, message: '令牌无效或已过期' });
    return;
  }
}

// 权限检查中间件工厂
export function requirePermission(permission: string) {
  return async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    if (!req.user) {
      res.status(401).json({ success: false, message: '未认证' });
      return;
    }

    if (!hasPermission(req.user.role, permission)) {
      // 记录权限拒绝日志
      await createLog({
        user_id: req.user.userId,
        username: req.user.username,
        action: 'permission_check',
        resource: permission,
        details: `权限不足，需要 ${permission}`,
        ip_address: req.ip || 'unknown',
        status: 'failure'
      });

      res.status(403).json({ success: false, message: '权限不足' });
      return;
    }

    next();
  };
}

// 角色检查中间件工厂
export function requireRole(minRole: 'admin' | 'operator' | 'viewer') {
  return async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    if (!req.user) {
      res.status(401).json({ success: false, message: '未认证' });
      return;
    }

    const roleHierarchy = { admin: 3, operator: 2, viewer: 1 };
    const userLevel = roleHierarchy[req.user.role as keyof typeof roleHierarchy] || 0;
    const requiredLevel = roleHierarchy[minRole];

    if (userLevel < requiredLevel) {
      res.status(403).json({ success: false, message: '角色权限不足' });
      return;
    }

    next();
  };
}

// 登录处理
export async function handleLogin(
  username: string,
  password: string,
  ipAddress: string
): Promise<{ success: boolean; token?: string; user?: Partial<User>; message?: string }> {
  const user = await findUserByUsername(username);

  if (!user) {
    await createLog({
      user_id: 'unknown',
      username: username,
      action: 'login',
      resource: 'auth',
      details: '用户不存在',
      ip_address: ipAddress,
      status: 'failure'
    });

    return { success: false, message: '用户名或密码错误' };
  }

  if (user.status !== 'active') {
    await createLog({
      user_id: user.id,
      username: user.username,
      action: 'login',
      resource: 'auth',
      details: `账户状态: ${user.status}`,
      ip_address: ipAddress,
      status: 'failure'
    });

    return { success: false, message: '账户已禁用或锁定' };
  }

  const isValid = await verifyPassword(password, user.password_hash);

  if (!isValid) {
    await createLog({
      user_id: user.id,
      username: user.username,
      action: 'login',
      resource: 'auth',
      details: '密码错误',
      ip_address: ipAddress,
      status: 'failure'
    });

    return { success: false, message: '用户名或密码错误' };
  }

  // 更新登录信息
  await updateLoginInfo(user.id);

  // 生成 token
  const token = generateToken(user);

  // 记录会话
  const expiresAt = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString();
  const tokenHash = bcrypt.hashSync(token, 10);
  await createSession(user.id, tokenHash, ipAddress, expiresAt);

  // 记录成功登录日志
  await createLog({
    user_id: user.id,
    username: user.username,
    action: 'login',
    resource: 'auth',
    details: '登录成功',
    ip_address: ipAddress,
    status: 'success'
  });

  return {
    success: true,
    token,
    user: {
      id: user.id,
      username: user.username,
      email: user.email,
      role: user.role,
      status: user.status,
      last_login_at: user.last_login_at
    }
  };
}

// 扩展 Express Request 类型
declare global {
  namespace Express {
    interface Request {
      user?: JWTPayload;
    }
  }
}