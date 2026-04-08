/**
 * rules.ts 单元测试
 */

import { describe, it, expect } from 'vitest'
import {
  PATTERNS,
  fieldRules,
  validateField,
  validateFields,
  toElRules,
  createFormRules,
  sanitizeData
} from '@/utils/rules'

describe('PATTERNS 正则表达式', () => {
  describe('identifier', () => {
    it('匹配有效标识符', () => {
      expect(PATTERNS.identifier.test('abc')).toBe(true)
      expect(PATTERNS.identifier.test('Test123')).toBe(true)
      expect(PATTERNS.identifier.test('my_id')).toBe(true)
      expect(PATTERNS.identifier.test('my-var')).toBe(true)
    })
    it('拒绝无效标识符', () => {
      expect(PATTERNS.identifier.test('123abc')).toBe(false) // 数字开头
      expect(PATTERNS.identifier.test('_test')).toBe(false)  // 下划线开头
      expect(PATTERNS.identifier.test('test!')).toBe(false)  // 特殊字符
    })
  })

  describe('envVarName', () => {
    it('匹配有效环境变量名', () => {
      expect(PATTERNS.envVarName.test('API_KEY')).toBe(true)
      expect(PATTERNS.envVarName.test('_PRIVATE')).toBe(true)
      expect(PATTERNS.envVarName.test('myVar123')).toBe(true)
    })
    it('拒绝无效环境变量名', () => {
      expect(PATTERNS.envVarName.test('123VAR')).toBe(false) // 数字开头
      expect(PATTERNS.envVarName.test('my-var')).toBe(false) // 含连字符
    })
  })

  describe('email', () => {
    it('匹配有效邮箱', () => {
      expect(PATTERNS.email.test('test@example.com')).toBe(true)
      expect(PATTERNS.email.test('user.name@domain.org')).toBe(true)
    })
    it('拒绝无效邮箱', () => {
      expect(PATTERNS.email.test('not-an-email')).toBe(false)
      expect(PATTERNS.email.test('@example.com')).toBe(false)
    })
  })

  describe('phone', () => {
    it('匹配有效中国手机号', () => {
      expect(PATTERNS.phone.test('13800138000')).toBe(true)
      expect(PATTERNS.phone.test('19912345678')).toBe(true)
    })
    it('拒绝无效手机号', () => {
      expect(PATTERNS.phone.test('12345678901')).toBe(false) // 非1开头
      expect(PATTERNS.phone.test('1380013800')).toBe(false)  // 10位
    })
  })

  describe('url', () => {
    it('匹配有效 HTTP URL', () => {
      expect(PATTERNS.url.test('http://example.com')).toBe(true)
      expect(PATTERNS.url.test('https://example.com/path')).toBe(true)
    })
    it('拒绝无效 URL', () => {
      expect(PATTERNS.url.test('ftp://example.com')).toBe(false)
      expect(PATTERNS.url.test('example.com')).toBe(false)
    })
  })

  describe('wsUrl', () => {
    it('匹配有效 WebSocket URL', () => {
      expect(PATTERNS.wsUrl.test('ws://example.com')).toBe(true)
      expect(PATTERNS.wsUrl.test('wss://example.com/ws')).toBe(true)
    })
    it('拒绝无效 WebSocket URL', () => {
      expect(PATTERNS.wsUrl.test('http://example.com')).toBe(false)
    })
  })

  describe('date', () => {
    it('匹配有效日期', () => {
      expect(PATTERNS.date.test('2024-01-15')).toBe(true)
      expect(PATTERNS.date.test('1999-12-31')).toBe(true)
    })
    it('拒绝无效日期', () => {
      expect(PATTERNS.date.test('2024/01/15')).toBe(false)
      expect(PATTERNS.date.test('15-01-2024')).toBe(false)
    })
  })

  describe('birthday', () => {
    it('匹配有效生日', () => {
      expect(PATTERNS.birthday.test('01-15')).toBe(true)
      expect(PATTERNS.birthday.test('12-31')).toBe(true)
    })
    it('拒绝无效生日', () => {
      expect(PATTERNS.birthday.test('1-15')).toBe(false)
      expect(PATTERNS.birthday.test('13-01')).toBe(false)
    })
  })
})

describe('validateField', () => {
  describe('username', () => {
    it('有效用户名', () => {
      expect(validateField('username', 'testuser')).toEqual({ valid: true })
    })
    it('空值必填', () => {
      const result = validateField('username', '')
      expect(result.valid).toBe(false)
      expect(result.message).toBe('请输入用户名')
    })
    it('过短', () => {
      const result = validateField('username', 'ab')
      expect(result.valid).toBe(false)
      expect(result.message).toBe('用户名至少3个字符')
    })
    it('无效格式', () => {
      const result = validateField('username', '123abc')
      expect(result.valid).toBe(false)
      expect(result.message).toContain('字母开头')
    })
  })

  describe('password', () => {
    it('有效密码', () => {
      expect(validateField('password', 'password123')).toEqual({ valid: true })
    })
    it('空值必填', () => {
      const result = validateField('password', '')
      expect(result.valid).toBe(false)
      expect(result.message).toBe('请输入密码')
    })
    it('过短', () => {
      const result = validateField('password', '12345')
      expect(result.valid).toBe(false)
      expect(result.message).toBe('密码至少6个字符')
    })
  })

  describe('email (非必填)', () => {
    it('有效邮箱', () => {
      expect(validateField('email', 'test@example.com')).toEqual({ valid: true })
    })
    it('空值允许', () => {
      expect(validateField('email', '')).toEqual({ valid: true })
    })
    it('无效格式', () => {
      const result = validateField('email', 'not-email')
      expect(result.valid).toBe(false)
      expect(result.message).toBe('请输入有效的邮箱地址')
    })
  })

  describe('phone (非必填)', () => {
    it('有效手机号', () => {
      expect(validateField('phone', '13800138000')).toEqual({ valid: true })
    })
    it('空值允许', () => {
      expect(validateField('phone', '')).toEqual({ valid: true })
    })
    it('无效格式', () => {
      const result = validateField('phone', '12345678901')
      expect(result.valid).toBe(false)
      expect(result.message).toBe('请输入有效的手机号')
    })
  })

  describe('未知字段', () => {
    it('返回有效', () => {
      expect(validateField('unknown', 'any')).toEqual({ valid: true })
    })
  })
})

describe('validateFields', () => {
  it('全部有效', () => {
    const result = validateFields(
      { username: 'test', password: 'password123' },
      ['username', 'password']
    )
    expect(result.valid).toBe(true)
    expect(result.errors).toEqual({})
  })

  it('部分无效', () => {
    const result = validateFields(
      { username: 'ab', password: '' },
      ['username', 'password']
    )
    expect(result.valid).toBe(false)
    expect(result.errors.username).toBeDefined()
    expect(result.errors.password).toBeDefined()
  })
})

describe('toElRules', () => {
  it('转换为 Element Plus 规则', () => {
    const rules = toElRules('username')
    expect(rules.length).toBeGreaterThan(0)
    expect(rules[0]).toHaveProperty('required')
    expect(rules[0]).toHaveProperty('trigger')
  })

  it('未知字段返回空数组', () => {
    expect(toElRules('unknown')).toEqual([])
  })

  it('指定 trigger', () => {
    const rules = toElRules('username', 'change')
    expect(rules[0].trigger).toBe('change')
  })
})

describe('createFormRules', () => {
  it('创建表单规则对象', () => {
    const rules = createFormRules({
      username: 'username',
      password: 'password'
    })
    expect(rules.username).toBeDefined()
    expect(rules.password).toBeDefined()
    expect(Array.isArray(rules.username)).toBe(true)
  })
})

describe('sanitizeData', () => {
  it('去除字符串首尾空格', () => {
    const result = sanitizeData({ name: '  test  ' })
    expect(result.name).toBe('test')
  })

  it('保留非字符串值', () => {
    const result = sanitizeData({ count: 123, active: true })
    expect(result.count).toBe(123)
    expect(result.active).toBe(true)
  })

  it('递归处理嵌套对象', () => {
    const result = sanitizeData({ user: { name: '  test  ' } })
    expect(result.user.name).toBe('test')
  })

  it('处理 null 和 undefined', () => {
    const result = sanitizeData({ a: null, b: undefined })
    expect(result.a).toBeNull()
    expect(result.b).toBeUndefined()
  })
})