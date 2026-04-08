/**
 * text-direction.ts 单元测试
 */

import { describe, it, expect } from 'vitest'
import { detectTextDirection } from '@/utils/text-direction'

describe('detectTextDirection', () => {
  describe('LTR 文本', () => {
    it('英文返回 ltr', () => {
      expect(detectTextDirection('Hello World')).toBe('ltr')
    })

    it('中文返回 ltr', () => {
      expect(detectTextDirection('你好世界')).toBe('ltr')
    })

    it('数字返回 ltr', () => {
      expect(detectTextDirection('12345')).toBe('ltr')
    })

    it('混合 LTR 文本返回 ltr', () => {
      expect(detectTextDirection('Hello 世界 123')).toBe('ltr')
    })
  })

  describe('RTL 文本', () => {
    it('阿拉伯语返回 rtl', () => {
      expect(detectTextDirection('مرحبا')).toBe('rtl')
    })

    it('希伯来语返回 rtl', () => {
      expect(detectTextDirection('שלום')).toBe('rtl')
    })

    it('RTL 开头的混合文本返回 rtl', () => {
      expect(detectTextDirection('مرحبا Hello')).toBe('rtl')
    })
  })

  describe('空值和边界', () => {
    it('空字符串返回 ltr', () => {
      expect(detectTextDirection('')).toBe('ltr')
    })

    it('null 返回 ltr', () => {
      expect(detectTextDirection(null)).toBe('ltr')
    })

    it('只有空格返回 ltr', () => {
      expect(detectTextDirection('   ')).toBe('ltr')
    })

    it('只有标点返回 ltr', () => {
      expect(detectTextDirection('!@#$%')).toBe('ltr')
    })
  })

  describe('跳过模式', () => {
    it('标点后第一个有效字符决定方向', () => {
      expect(detectTextDirection('...Hello')).toBe('ltr')
      expect(detectTextDirection('...مرحبا')).toBe('rtl')
    })
  })
})