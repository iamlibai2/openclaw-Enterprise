/**
 * 通用表单校验工具
 *
 * @deprecated 此文件待删除，未被使用。校验功能统一使用 rules.ts
 *
 * 提供常用的校验规则和校验函数
 */

// 校验结果类型
export interface ValidationResult {
  valid: boolean
  message?: string
}

// 校验规则类型
export type Validator = (value: any) => ValidationResult

/**
 * 必填校验
 */
export function required(message = '此项为必填项'): Validator {
  return (value: any) => {
    if (value === null || value === undefined || value === '') {
      return { valid: false, message }
    }
    if (Array.isArray(value) && value.length === 0) {
      return { valid: false, message }
    }
    return { valid: true }
  }
}

/**
 * 长度范围校验
 */
export function lengthRange(min: number, max: number, message?: string): Validator {
  return (value: string) => {
    if (!value) return { valid: true }
    const len = value.length
    if (len < min || len > max) {
      return { valid: false, message: message || `长度应在 ${min}-${max} 个字符之间` }
    }
    return { valid: true }
  }
}

/**
 * 最小长度校验
 */
export function minLength(min: number, message?: string): Validator {
  return (value: string) => {
    if (!value) return { valid: true }
    if (value.length < min) {
      return { valid: false, message: message || `长度不能少于 ${min} 个字符` }
    }
    return { valid: true }
  }
}

/**
 * 最大长度校验
 */
export function maxLength(max: number, message?: string): Validator {
  return (value: string) => {
    if (!value) return { valid: true }
    if (value.length > max) {
      return { valid: false, message: message || `长度不能超过 ${max} 个字符` }
    }
    return { valid: true }
  }
}

/**
 * URL 格式校验
 */
export function url(message = '请输入有效的 URL', protocols = ['http', 'https']): Validator {
  return (value: string) => {
    if (!value) return { valid: true }
    try {
      const url = new URL(value)
      if (!protocols.includes(url.protocol.replace(':', ''))) {
        return { valid: false, message: `URL 必须以 ${protocols.join(' 或 ')}:// 开头` }
      }
      if (!url.netloc) {
        return { valid: false, message }
      }
      return { valid: true }
    } catch {
      return { valid: false, message }
    }
  }
}

/**
 * WebSocket URL 格式校验
 */
export function wsUrl(message = '请输入有效的 WebSocket URL'): Validator {
  return (value: string) => {
    if (!value) return { valid: true }
    try {
      const url = new URL(value)
      if (!['ws', 'wss'].includes(url.protocol.replace(':', ''))) {
        return { valid: false, message: 'URL 必须以 ws:// 或 wss:// 开头' }
      }
      if (!url.host) {
        return { valid: false, message }
      }
      return { valid: true }
    } catch {
      return { valid: false, message }
    }
  }
}

/**
 * 邮箱格式校验
 */
export function email(message = '请输入有效的邮箱地址'): Validator {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return (value: string) => {
    if (!value) return { valid: true }
    if (!emailRegex.test(value)) {
      return { valid: false, message }
    }
    return { valid: true }
  }
}

/**
 * 手机号格式校验（中国）
 */
export function phone(message = '请输入有效的手机号'): Validator {
  const phoneRegex = /^1[3-9]\d{9}$/
  return (value: string) => {
    if (!value) return { valid: true }
    if (!phoneRegex.test(value.replace(/\s/g, ''))) {
      return { valid: false, message }
    }
    return { valid: true }
  }
}

/**
 * 数字范围校验
 */
export function numberRange(min: number, max: number, message?: string): Validator {
  return (value: any) => {
    if (value === null || value === undefined || value === '') return { valid: true }
    const num = Number(value)
    if (isNaN(num)) {
      return { valid: false, message: '请输入有效的数字' }
    }
    if (num < min || num > max) {
      return { valid: false, message: message || `数值应在 ${min}-${max} 之间` }
    }
    return { valid: true }
  }
}

/**
 * 整数校验
 */
export function integer(message = '请输入整数'): Validator {
  return (value: any) => {
    if (value === null || value === undefined || value === '') return { valid: true }
    if (!Number.isInteger(Number(value))) {
      return { valid: false, message }
    }
    return { valid: true }
  }
}

/**
 * 正整数校验
 */
export function positiveInteger(message = '请输入正整数'): Validator {
  return (value: any) => {
    if (value === null || value === undefined || value === '') return { valid: true }
    const num = Number(value)
    if (!Number.isInteger(num) || num <= 0) {
      return { valid: false, message }
    }
    return { valid: true }
  }
}

/**
 * 标识符格式校验（字母开头，只含字母数字下划线连字符）
 */
export function identifier(message = '只能包含字母、数字、下划线、连字符，且必须以字母开头'): Validator {
  const pattern = /^[a-zA-Z][a-zA-Z0-9_-]*$/
  return (value: string) => {
    if (!value) return { valid: true }
    if (!pattern.test(value)) {
      return { valid: false, message }
    }
    return { valid: true }
  }
}

/**
 * 环境变量名格式校验
 */
export function envVarName(message = '只能包含字母、数字、下划线，且不能以数字开头'): Validator {
  const pattern = /^[A-Za-z_][A-Za-z0-9_]*$/
  return (value: string) => {
    if (!value) return { valid: true }
    if (!pattern.test(value)) {
      return { valid: false, message }
    }
    return { valid: true }
  }
}

/**
 * JSON 格式校验
 */
export function json(message = 'JSON 格式不正确'): Validator {
  return (value: string) => {
    if (!value || !value.trim()) return { valid: true }
    try {
      JSON.parse(value)
      return { valid: true }
    } catch {
      return { valid: false, message }
    }
  }
}

/**
 * 正则表达式校验
 */
export function pattern(regex: RegExp, message: string): Validator {
  return (value: string) => {
    if (!value) return { valid: true }
    if (!regex.test(value)) {
      return { valid: false, message }
    }
    return { valid: true }
  }
}

/**
 * 日期格式校验 (YYYY-MM-DD)
 */
export function date(message = '请输入有效的日期格式 (YYYY-MM-DD)'): Validator {
  const dateRegex = /^\d{4}-\d{2}-\d{2}$/
  return (value: string) => {
    if (!value) return { valid: true }
    if (!dateRegex.test(value)) {
      return { valid: false, message }
    }
    // 验证日期是否有效
    const date = new Date(value)
    if (isNaN(date.getTime())) {
      return { valid: false, message }
    }
    return { valid: true }
  }
}

/**
 * 生日格式校验 (MM-DD)
 */
export function birthday(message = '请输入有效的生日格式 (MM-DD)'): Validator {
  const birthdayRegex = /^(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$/
  return (value: string) => {
    if (!value) return { valid: true }
    if (!birthdayRegex.test(value)) {
      return { valid: false, message }
    }
    return { valid: true }
  }
}

/**
 * 组合多个校验器
 */
export function compose(...validators: Validator[]): Validator {
  return (value: any) => {
    for (const validator of validators) {
      const result = validator(value)
      if (!result.valid) {
        return result
      }
    }
    return { valid: true }
  }
}

/**
 * 校验表单数据
 * @param data 表单数据
 * @param rules 校验规则 { 字段名: 校验器数组 }
 * @returns { valid: boolean, errors: { 字段名: 错误信息 } }
 */
export function validateForm(
  data: Record<string, any>,
  rules: Record<string, Validator[]>
): { valid: boolean; errors: Record<string, string> } {
  const errors: Record<string, string> = {}

  for (const [field, validators] of Object.entries(rules)) {
    const value = data[field]
    for (const validator of validators) {
      const result = validator(value)
      if (!result.valid) {
        errors[field] = result.message || '校验失败'
        break
      }
    }
  }

  return {
    valid: Object.keys(errors).length === 0,
    errors
  }
}

/**
 * Element Plus 表单校验规则生成器
 */
export function createElRules(validators: Validator[]) {
  return [
    {
      validator: (rule: any, value: any, callback: (error?: Error) => void) => {
        for (const validator of validators) {
          const result = validator(value)
          if (!result.valid) {
            callback(new Error(result.message || '校验失败'))
            return
          }
        }
        callback()
      }
    }
  ]
}