/**
 * 会话缓存
 * 参考 OpenClaw: /home/iamlibai/workspace/github_code/openclaw/ui/src/ui/chat/session-cache.ts
 */

export const MAX_CACHED_CHAT_SESSIONS = 20

/**
 * 获取或创建会话缓存值（LRU 策略）
 */
export function getOrCreateSessionCacheValue<T>(
  map: Map<string, T>,
  sessionKey: string,
  create: () => T
): T {
  if (map.has(sessionKey)) {
    const existing = map.get(sessionKey) as T
    // LRU: 删除后重新插入，使最近使用的会话保持在缓存中
    map.delete(sessionKey)
    map.set(sessionKey, existing)
    return existing
  }

  const created = create()
  map.set(sessionKey, created)

  // 超过上限时移除最旧的
  while (map.size > MAX_CACHED_CHAT_SESSIONS) {
    const oldest = map.keys().next().value
    if (typeof oldest !== 'string') {
      break
    }
    map.delete(oldest)
  }

  return created
}

/**
 * 会话缓存管理器
 */
export class SessionCache<T> {
  private cache = new Map<string, T>()

  get(sessionKey: string): T | undefined {
    const value = this.cache.get(sessionKey)
    if (value !== undefined) {
      // LRU: 刷新位置
      this.cache.delete(sessionKey)
      this.cache.set(sessionKey, value)
    }
    return value
  }

  set(sessionKey: string, value: T): void {
    // 先删除（如果存在），确保位置更新
    this.cache.delete(sessionKey)
    this.cache.set(sessionKey, value)

    // 超过上限时移除最旧的
    while (this.cache.size > MAX_CACHED_CHAT_SESSIONS) {
      const oldest = this.cache.keys().next().value
      if (typeof oldest !== 'string') {
        break
      }
      this.cache.delete(oldest)
    }
  }

  has(sessionKey: string): boolean {
    return this.cache.has(sessionKey)
  }

  delete(sessionKey: string): boolean {
    return this.cache.delete(sessionKey)
  }

  clear(): void {
    this.cache.clear()
  }

  get size(): number {
    return this.cache.size
  }
}