/**
 * 输入历史管理
 * 参考 OpenClaw: /home/iamlibai/workspace/github_code/openclaw/ui/src/ui/chat/input-history.ts
 */

const MAX_HISTORY = 50

export class InputHistory {
  private items: string[] = []
  private cursor = -1

  /**
   * 添加历史记录
   */
  push(text: string): void {
    const trimmed = text.trim()
    if (!trimmed) {
      return
    }
    // 去重：不添加与最后一条相同的记录
    if (this.items[this.items.length - 1] === trimmed) {
      return
    }
    this.items.push(trimmed)
    // 超过上限时移除最旧的
    if (this.items.length > MAX_HISTORY) {
      this.items.shift()
    }
    // 重置游标
    this.cursor = -1
  }

  /**
   * 向上翻（获取更早的历史）
   */
  up(): string | null {
    if (this.items.length === 0) {
      return null
    }
    if (this.cursor < 0) {
      // 首次按上，定位到最新的历史
      this.cursor = this.items.length - 1
    } else if (this.cursor > 0) {
      // 继续往上
      this.cursor--
    }
    return this.items[this.cursor] ?? null
  }

  /**
   * 向下翻（获取更新的历史）
   */
  down(): string | null {
    if (this.cursor < 0) {
      return null
    }
    this.cursor++
    if (this.cursor >= this.items.length) {
      // 超出范围，返回空并重置
      this.cursor = -1
      return null
    }
    return this.items[this.cursor] ?? null
  }

  /**
   * 重置游标（发送消息后调用）
   */
  reset(): void {
    this.cursor = -1
  }

  /**
   * 获取所有历史记录（只读）
   */
  getAll(): readonly string[] {
    return this.items
  }

  /**
   * 清空历史
   */
  clear(): void {
    this.items = []
    this.cursor = -1
  }
}