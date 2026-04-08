/**
 * 校验规则定义 - 单一来源
 *
 * 前端和后端都从这里获取规则定义，确保一致性
 */

// 正则表达式
export const PATTERNS = {
  // 标识符：字母开头，只含字母数字下划线连字符
  identifier: /^[a-zA-Z][a-zA-Z0-9_-]*$/,
  // 环境变量名
  envVarName: /^[A-Za-z_][A-Za-z0-9_]*$/,
  // 邮箱
  email: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
  // 手机号（中国）
  phone: /^1[3-9]\d{9}$/,
  // URL
  url: /^https?:\/\/.+/,
  // WebSocket URL
  wsUrl: /^wss?:\/\/.+/,
  // 日期 YYYY-MM-DD
  date: /^\d{4}-\d{2}-\d{2}$/,
  // 生日 MM-DD
  birthday: /^(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$/
}

// 字段规则类型
interface FieldRule {
  required?: boolean
  minLength?: number
  maxLength?: number
  pattern?: RegExp
  messages: {
    required?: string
    minLength?: string
    maxLength?: string
    pattern?: string
  }
}

// 字段规则定义
export const fieldRules: Record<string, FieldRule> = {
  // ========== 用户相关 ==========
  username: {
    required: true,
    minLength: 3,
    maxLength: 50,
    pattern: PATTERNS.identifier,
    messages: {
      required: '请输入用户名',
      minLength: '用户名至少3个字符',
      maxLength: '用户名最多50个字符',
      pattern: '用户名必须以字母开头，只能包含字母、数字、下划线、连字符'
    }
  },

  password: {
    required: true,
    minLength: 6,
    maxLength: 100,
    messages: {
      required: '请输入密码',
      minLength: '密码至少6个字符',
      maxLength: '密码最多100个字符'
    }
  },

  email: {
    required: false,
    pattern: PATTERNS.email,
    maxLength: 100,
    messages: {
      pattern: '请输入有效的邮箱地址',
      maxLength: '邮箱最多100个字符'
    }
  },

  phone: {
    required: false,
    pattern: PATTERNS.phone,
    messages: {
      pattern: '请输入有效的手机号'
    }
  },

  displayName: {
    required: false,
    maxLength: 50,
    messages: {
      maxLength: '显示名称最多50个字符'
    }
  },

  // ========== Gateway 相关 ==========
  gatewayName: {
    required: true,
    maxLength: 100,
    messages: {
      required: '请输入 Gateway 名称',
      maxLength: '名称最多100个字符'
    }
  },

  gatewayUrl: {
    required: true,
    pattern: PATTERNS.wsUrl,
    messages: {
      required: '请输入 WebSocket 地址',
      pattern: '地址必须以 ws:// 或 wss:// 开头'
    }
  },

  // ========== 模型提供商相关 ==========
  providerName: {
    required: true,
    maxLength: 50,
    pattern: PATTERNS.identifier,
    messages: {
      required: '请输入提供商名称',
      maxLength: '名称最多50个字符',
      pattern: '名称必须以字母开头，只能包含字母、数字、下划线、连字符'
    }
  },

  baseUrl: {
    required: true,
    pattern: PATTERNS.url,
    maxLength: 500,
    messages: {
      required: '请输入 Base URL',
      pattern: 'URL 必须以 http:// 或 https:// 开头',
      maxLength: 'URL 最多500个字符'
    }
  },

  apiKeyEnv: {
    required: true,
    pattern: PATTERNS.envVarName,
    maxLength: 100,
    messages: {
      required: '请输入环境变量名',
      pattern: '环境变量名只能包含字母、数字、下划线，且不能以数字开头',
      maxLength: '环境变量名最多100个字符'
    }
  },

  // ========== 部门/员工相关 ==========
  departmentName: {
    required: true,
    maxLength: 50,
    messages: {
      required: '请输入部门名称',
      maxLength: '部门名称最多50个字符'
    }
  },

  employeeName: {
    required: true,
    maxLength: 50,
    messages: {
      required: '请输入员工姓名',
      maxLength: '姓名最多50个字符'
    }
  },

  // ========== Agent 相关 ==========
  agentId: {
    required: true,
    minLength: 1,
    maxLength: 50,
    pattern: PATTERNS.identifier,
    messages: {
      required: '请输入 Agent ID',
      minLength: 'Agent ID 不能为空',
      maxLength: 'Agent ID 最多50个字符',
      pattern: 'ID 必须以字母开头，只能包含字母、数字、下划线、连字符'
    }
  },

  agentIdLower: {
    required: true,
    minLength: 1,
    maxLength: 50,
    pattern: /^[a-z0-9-]+$/,
    messages: {
      required: '请输入 Agent ID',
      minLength: 'Agent ID 不能为空',
      maxLength: 'Agent ID 最多50个字符',
      pattern: 'ID 只能包含小写字母、数字和连字符'
    }
  },

  agentName: {
    required: true,
    maxLength: 100,
    messages: {
      required: '请输入 Agent 名称',
      maxLength: '名称最多100个字符'
    }
  },

  modelSelect: {
    required: true,
    messages: {
      required: '请选择模型'
    }
  },

  agentSelect: {
    required: true,
    messages: {
      required: '请选择 Agent'
    }
  },

  accountId: {
    required: true,
    maxLength: 100,
    messages: {
      required: '请输入账号标识',
      maxLength: '账号标识最多100个字符'
    }
  },

  // ========== Skill 相关 ==========
  skillName: {
    required: true,
    maxLength: 100,
    pattern: /^[a-z0-9_-]+$/,
    messages: {
      required: '请输入 Skill 名称',
      maxLength: '名称最多100个字符',
      pattern: '只能包含小写字母、数字、下划线和横线'
    }
  },

  skillLocation: {
    required: true,
    messages: {
      required: '请选择存储位置'
    }
  },

  skillContent: {
    required: true,
    messages: {
      required: '请输入内容'
    }
  },

  // ========== Template 相关 ==========
  templateId: {
    required: true,
    maxLength: 50,
    pattern: /^[a-z0-9-]+$/,
    messages: {
      required: '请输入模板ID',
      maxLength: '模板ID最多50个字符',
      pattern: '只能包含小写字母、数字和连字符'
    }
  },

  templateName: {
    required: true,
    maxLength: 100,
    messages: {
      required: '请输入模板名称',
      maxLength: '名称最多100个字符'
    }
  },

  templateFileType: {
    required: true,
    messages: {
      required: '请选择文件类型'
    }
  },

  templateContent: {
    required: true,
    messages: {
      required: '请输入模板内容'
    }
  },

  // ========== 模型相关 ==========
  modelName: {
    required: true,
    maxLength: 100,
    messages: {
      required: '请输入模型名称',
      maxLength: '模型名称最多100个字符'
    }
  },

  modelDisplayName: {
    required: true,
    maxLength: 100,
    messages: {
      required: '请输入显示名称',
      maxLength: '显示名称最多100个字符'
    }
  },

  apiBase: {
    required: false,
    maxLength: 500,
    messages: {
      maxLength: 'API 地址最多500个字符'
    }
  },

  apiKey: {
    required: false,
    maxLength: 500,
    messages: {
      maxLength: 'API Key 最多500个字符'
    }
  },

  // ========== 通用 ==========
  json: {
    required: false,
    messages: {
      pattern: 'JSON 格式不正确'
    }
  }
}

// ========== 工具函数 ==========

/**
 * 验证单个字段
 */
export function validateField(
  fieldName: string,
  value: any
): { valid: boolean; message?: string } {
  const rule = fieldRules[fieldName]
  if (!rule) return { valid: true }

  // 必填校验
  if (rule.required && (value === null || value === undefined || value === '')) {
    return { valid: false, message: rule.messages?.required || '此项为必填项' }
  }

  // 非必填且为空，跳过其他校验
  if (value === null || value === undefined || value === '') {
    return { valid: true }
  }

  // 长度校验
  const minLen = rule.minLength
  const maxLen = rule.maxLength
  if (minLen !== undefined && value.length < minLen) {
    return { valid: false, message: rule.messages?.minLength }
  }
  if (maxLen !== undefined && value.length > maxLen) {
    return { valid: false, message: rule.messages?.maxLength }
  }

  // 正则校验
  if (rule.pattern && !rule.pattern.test(value)) {
    return { valid: false, message: rule.messages?.pattern }
  }

  return { valid: true }
}

/**
 * 验证多个字段
 */
export function validateFields(
  data: Record<string, any>,
  fields: string[]
): { valid: boolean; errors: Record<string, string> } {
  const errors: Record<string, string> = {}

  for (const field of fields) {
    const result = validateField(field, data[field])
    if (!result.valid && result.message) {
      errors[field] = result.message
    }
  }

  return {
    valid: Object.keys(errors).length === 0,
    errors
  }
}

/**
 * 转换为 Element Plus 表单规则
 */
export function toElRules(
  fieldName: string,
  trigger: 'blur' | 'change' = 'blur'
): any[] {
  const rule = fieldRules[fieldName]
  if (!rule) return []

  const rules: any[] = []

  if (rule.required) {
    rules.push({
      required: true,
      message: rule.messages?.required || '此项为必填项',
      trigger
    })
  }

  const minLen = rule.minLength
  const maxLen = rule.maxLength
  if (minLen !== undefined || maxLen !== undefined) {
    rules.push({
      min: minLen || 0,
      max: maxLen || Infinity,
      message: rule.messages?.minLength || rule.messages?.maxLength,
      trigger
    })
  }

  if (rule.pattern) {
    rules.push({
      pattern: rule.pattern,
      message: rule.messages?.pattern,
      trigger
    })
  }

  return rules
}

/**
 * 创建表单规则对象（用于 el-form :rules）
 */
export function createFormRules(
  fields: Record<string, string>
): Record<string, any[]> {
  const rules: Record<string, any[]> = {}
  for (const [formField, ruleName] of Object.entries(fields)) {
    rules[formField] = toElRules(ruleName)
  }
  return rules
}

/**
 * 清理输入数据 - 去除字符串首尾空格
 */
export function sanitizeData(data: Record<string, any>): Record<string, any> {
  const result: Record<string, any> = {}
  for (const [key, value] of Object.entries(data)) {
    if (typeof value === 'string') {
      result[key] = value.trim()
    } else if (value !== null && typeof value === 'object' && !Array.isArray(value)) {
      // 递归处理嵌套对象
      result[key] = sanitizeData(value)
    } else {
      result[key] = value
    }
  }
  return result
}