import sqlite3 from 'sqlite3';
import { v4 as uuidv4 } from 'uuid';
import bcrypt from 'bcryptjs';
import { User, OperationLog, RBAC_PERMISSIONS } from './types';

const db = new sqlite3.Database('./data/openclaw.db');

// 初始化数据库表
export async function initDatabase(): Promise<void> {
  return new Promise((resolve, reject) => {
    db.serialize(() => {
      // 用户表
      db.run(`
        CREATE TABLE IF NOT EXISTS users (
          id TEXT PRIMARY KEY,
          username TEXT UNIQUE NOT NULL,
          email TEXT UNIQUE NOT NULL,
          password_hash TEXT NOT NULL,
          role TEXT NOT NULL DEFAULT 'viewer',
          status TEXT NOT NULL DEFAULT 'active',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          last_login_at TEXT,
          login_count INTEGER DEFAULT 0
        )
      `);

      // 操作日志表
      db.run(`
        CREATE TABLE IF NOT EXISTS operation_logs (
          id TEXT PRIMARY KEY,
          user_id TEXT NOT NULL,
          username TEXT NOT NULL,
          action TEXT NOT NULL,
          resource TEXT NOT NULL,
          resource_id TEXT,
          details TEXT,
          ip_address TEXT NOT NULL,
          status TEXT NOT NULL,
          created_at TEXT NOT NULL,
          FOREIGN KEY (user_id) REFERENCES users(id)
        )
      `);

      // 会话表（用于跟踪活跃会话）
      db.run(`
        CREATE TABLE IF NOT EXISTS sessions (
          id TEXT PRIMARY KEY,
          user_id TEXT NOT NULL,
          token_hash TEXT NOT NULL,
          ip_address TEXT NOT NULL,
          created_at TEXT NOT NULL,
          expires_at TEXT NOT NULL,
          is_active INTEGER DEFAULT 1,
          FOREIGN KEY (user_id) REFERENCES users(id)
        )
      `);

      // 创建默认管理员账户
      const now = new Date().toISOString();
      const adminId = uuidv4();
      const adminPassword = bcrypt.hashSync('admin123', 10);

      db.run(
        `INSERT OR IGNORE INTO users (id, username, email, password_hash, role, status, created_at, updated_at, login_count)
         VALUES (?, 'admin', 'admin@openclaw.local', ?, 'admin', 'active', ?, ?, 0)`,
        [adminId, adminPassword, now, now],
        (err) => {
          if (err) {
            console.error('创建默认管理员失败:', err);
          } else {
            console.log('✅ 默认管理员已创建: admin / admin123');
          }
          resolve();
        }
      );
    });
  });
}

// 用户相关操作
export async function findUserByUsername(username: string): Promise<User | null> {
  return new Promise((resolve, reject) => {
    db.get(
      'SELECT * FROM users WHERE username = ?',
      [username],
      (err, row) => {
        if (err) reject(err);
        else resolve(row as User | null);
      }
    );
  });
}

export async function findUserById(id: string): Promise<User | null> {
  return new Promise((resolve, reject) => {
    db.get(
      'SELECT * FROM users WHERE id = ?',
      [id],
      (err, row) => {
        if (err) reject(err);
        else resolve(row as User | null);
      }
    );
  });
}

export async function createUser(user: Partial<User>): Promise<User> {
  const id = uuidv4();
  const now = new Date().toISOString();
  const passwordHash = user.password_hash ? bcrypt.hashSync(user.password_hash!, 10) : '';

  return new Promise((resolve, reject) => {
    db.run(
      `INSERT INTO users (id, username, email, password_hash, role, status, created_at, updated_at, login_count)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)`,
      [id, user.username, user.email, passwordHash, user.role || 'viewer', user.status || 'active', now, now],
      (err) => {
        if (err) reject(err);
        else {
          resolve({
            id,
            username: user.username!,
            email: user.email!,
            password_hash: passwordHash,
            role: user.role || 'viewer',
            status: user.status || 'active',
            created_at: now,
            updated_at: now,
            login_count: 0
          });
        }
      }
    );
  });
}

export async function updateUser(id: string, updates: Partial<User>): Promise<User | null> {
  const now = new Date().toISOString();
  const fields = Object.keys(updates).map(k => `${k} = ?`).join(', ');
  const values = Object.values(updates);

  return new Promise((resolve, reject) => {
    db.run(
      `UPDATE users SET ${fields}, updated_at = ? WHERE id = ?`,
      [...values, now, id],
      async (err) => {
        if (err) reject(err);
        else resolve(await findUserById(id));
      }
    );
  });
}

export async function deleteUser(id: string): Promise<boolean> {
  return new Promise((resolve, reject) => {
    db.run('DELETE FROM users WHERE id = ?', [id], (err) => {
      if (err) reject(err);
      else resolve(true);
    });
  });
}

export async function listUsers(): Promise<User[]> {
  return new Promise((resolve, reject) => {
    db.all('SELECT * FROM users ORDER BY created_at DESC', (err, rows) => {
      if (err) reject(err);
      else resolve(rows as User[]);
    });
  });
}

export async function updateLoginInfo(id: string): Promise<void> {
  const now = new Date().toISOString();
  return new Promise((resolve, reject) => {
    db.run(
      'UPDATE users SET last_login_at = ?, login_count = login_count + 1 WHERE id = ?',
      [now, id],
      (err) => {
        if (err) reject(err);
        else resolve();
      }
    );
  });
}

// 操作日志相关操作
export async function createLog(log: Partial<OperationLog>): Promise<OperationLog> {
  const id = uuidv4();
  const now = new Date().toISOString();

  return new Promise((resolve, reject) => {
    db.run(
      `INSERT INTO operation_logs (id, user_id, username, action, resource, resource_id, details, ip_address, status, created_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [id, log.user_id, log.username, log.action, log.resource, log.resource_id, log.details, log.ip_address, log.status, now],
      (err) => {
        if (err) reject(err);
        else {
          resolve({
            id,
            user_id: log.user_id!,
            username: log.username!,
            action: log.action!,
            resource: log.resource!,
            resource_id: log.resource_id,
            details: log.details!,
            ip_address: log.ip_address!,
            status: log.status!,
            created_at: now
          });
        }
      }
    );
  });
}

export async function listLogs(limit: number = 100, offset: number = 0): Promise<OperationLog[]> {
  return new Promise((resolve, reject) => {
    db.all(
      'SELECT * FROM operation_logs ORDER BY created_at DESC LIMIT ? OFFSET ?',
      [limit, offset],
      (err, rows) => {
        if (err) reject(err);
        else resolve(rows as OperationLog[]);
      }
    );
  });
}

export async function countLogs(): Promise<number> {
  return new Promise((resolve, reject) => {
    db.get('SELECT COUNT(*) as count FROM operation_logs', (err, row) => {
      if (err) reject(err);
      else resolve((row as any).count);
    });
  });
}

// 会话相关操作
export async function createSession(userId: string, tokenHash: string, ipAddress: string, expiresAt: string): Promise<void> {
  const id = uuidv4();
  const now = new Date().toISOString();

  return new Promise((resolve, reject) => {
    db.run(
      `INSERT INTO sessions (id, user_id, token_hash, ip_address, created_at, expires_at, is_active)
       VALUES (?, ?, ?, ?, ?, ?, 1)`,
      [id, userId, tokenHash, ipAddress, now, expiresAt],
      (err) => {
        if (err) reject(err);
        else resolve();
      }
    );
  });
}

export async function invalidateSession(tokenHash: string): Promise<void> {
  return new Promise((resolve, reject) => {
    db.run(
      'UPDATE sessions SET is_active = 0 WHERE token_hash = ?',
      [tokenHash],
      (err) => {
        if (err) reject(err);
        else resolve();
      }
    );
  });
}

export async function cleanupExpiredSessions(): Promise<void> {
  const now = new Date().toISOString();
  return new Promise((resolve, reject) => {
    db.run(
      'UPDATE sessions SET is_active = 0 WHERE expires_at < ? AND is_active = 1',
      [now],
      (err) => {
        if (err) reject(err);
        else resolve();
      }
    );
  });
}

// 权限查询
export function getUserPermissions(role: string): string[] {
  return RBAC_PERMISSIONS[role] || [];
}

export function hasPermission(role: string, permission: string): boolean {
  const permissions = getUserPermissions(role);
  return permissions.includes(permission);
}

export default db;