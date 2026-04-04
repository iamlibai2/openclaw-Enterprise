/**
 * 文本方向检测
 * 检测 RTL（从右到左）语言：希伯来语、阿拉伯语等
 * 参考: /home/iamlibai/workspace/github_code/openclaw/ui/src/ui/text-direction.ts
 */

const RTL_CHAR_REGEX =
  /\p{Script=Hebrew}|\p{Script=Arabic}|\p{Script=Syriac}|\p{Script=Thaana}|\p{Script=Nko}|\p{Script=Samaritan}|\p{Script=Mandaic}|\p{Script=Adlam}|\p{Script=Phoenician}|\p{Script=Lydian}/u

/**
 * 从第一个有效字符检测文本方向
 * @param text - 要检测的文本
 * @param skipPattern - 跳过的字符模式（默认跳过空白和标点）
 */
export function detectTextDirection(
  text: string | null,
  skipPattern: RegExp = /[\s\p{P}\p{S}]/u
): 'rtl' | 'ltr' {
  if (!text) return 'ltr'

  for (const char of text) {
    if (skipPattern.test(char)) continue
    return RTL_CHAR_REGEX.test(char) ? 'rtl' : 'ltr'
  }

  return 'ltr'
}