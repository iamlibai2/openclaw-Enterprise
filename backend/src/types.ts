// 类型定义

export interface User {
  id: string;
  username: string;
  email: string;
  password_hash: string;
  role: 'admin' | 'operator' | 'viewer';
  status: 'active' | 'inactive' | 'locked';
  created_at: string;
  updated_at: string;
  last_login_at?: string;
  login_count: number;
}

export interface Role {
  id: string;
  name: string;
  description: string;
  permissions: Permission[];
}

export interface Permission {
  id: string;
  resource: string;
  action: 'read' | 'write' | 'delete' | 'manage';
  description: string;
}

export interface OperationLog {
  id: string;
  user_id: string;
  username: string;
  action: string;
  resource: string;
  resource_id?: string;
  details: string;
  ip_address: string;
  status: 'success' | 'failure';
  created_at: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  success: boolean;
  token?: string;
  user?: Partial<User>;
  message?: string;
}

export interface JWTPayload {
  userId: string;
  username: string;
  role: string;
  permissions: string[];
}

// RBAC 权限矩阵
export const RBAC_PERMISSIONS: Record<string, string[]> = {
  admin: [
    'gateway:read', 'gateway:write', 'gateway:manage',
    'agents:read', 'agents:write', 'agents:delete', 'agents:manage',
    'bindings:read', 'bindings:write', 'bindings:delete', 'bindings:manage',
    'tools:read', 'tools:write', 'tools:delete', 'tools:manage',
    'models:read', 'models:write', 'models:delete', 'models:manage',
    'sessions:read', 'sessions:write', 'sessions:delete', 'sessions:manage',
    'logs:read', 'logs:write', 'logs:delete', 'logs:manage',
    'config:read', 'config:write', 'config:delete', 'config:manage',
    'users:read', 'users:write', 'users:delete', 'users:manage',
    'audit:read', 'audit:manage',
    'system:manage'
  ],
  operator: [
    'gateway:read', 'gateway:write',
    'agents:read', 'agents:write',
    'bindings:read', 'bindings:write',
    'tools:read', 'tools:write',
    'models:read',
    'sessions:read', 'sessions:write',
    'logs:read',
    'config:read', 'config:write',
    'audit:read'
  ],
  viewer: [
    'gateway:read',
    'agents:read',
    'bindings:read',
    'tools:read',
    'models:read',
    'sessions:read',
    'logs:read',
    'config:read',
    'audit:read'
  ]
};