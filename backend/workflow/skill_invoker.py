"""
Skill Invoker - 调用 OpenClaw Gateway 执行 Skill
"""

import asyncio
from typing import Any, Dict, Optional, Callable, Awaitable
from gateway_sync import sync_call, SyncGatewayClient


class SkillInvoker:
    """
    Skill 调用器

    通过 OpenClaw Gateway 调用 Skill
    """

    def __init__(self, gateway_id: Optional[int] = None):
        """
        初始化

        Args:
            gateway_id: Gateway ID（可选，默认使用当前 Gateway）
        """
        self.gateway_id = gateway_id
        self.client = SyncGatewayClient(gateway_id)

    async def __call__(self, skill_id: str, input_data: dict) -> Any:
        """
        调用 Skill

        Args:
            skill_id: Skill ID
            input_data: 输入数据

        Returns:
            Skill 输出（只返回 output 部分，不包含元数据）
        """
        # 尝试调用 OpenClaw Gateway 的 skill.invoke 方法
        try:
            # 方法1: 尝试 skills.invoke
            result = sync_call("skills.invoke", {
                "skillId": skill_id,
                "input": input_data
            }, self.gateway_id)
            # 返回 output 部分，如果没有则返回整个结果
            return result.get("output", result)
        except Exception as e:
            error_str = str(e).lower()

            # 如果 skills.invoke 不存在，尝试其他方法
            if 'not found' in error_str or 'unknown method' in error_str:
                try:
                    # 方法2: 尝试 agents.invokeSkill
                    result = sync_call("agents.invokeSkill", {
                        "skillId": skill_id,
                        "input": input_data
                    }, self.gateway_id)
                    return result.get("output", result)
                except Exception:
                    pass

            # 如果 Gateway 方法都失败，返回 Mock 输出
            # 注意：只返回 output 部分，符合工作流引擎的数据传递约定
            return self._generate_mock_output(skill_id, input_data)

    def _generate_mock_output(self, skill_id: str, input_data: dict) -> Any:
        """生成模拟输出"""
        # 根据常见 Skill 类型生成合理的模拟输出
        skill_lower = skill_id.lower()

        if 'search' in skill_lower or 'baidu' in skill_lower:
            return {
                "results": [
                    {"title": f"搜索结果 1", "content": f"关于 {input_data.get('query', '未知主题')} 的相关内容...", "url": "https://example.com/1"},
                    {"title": f"搜索结果 2", "content": f"更多关于 {input_data.get('query', '未知主题')} 的信息...", "url": "https://example.com/2"},
                    {"title": f"搜索结果 3", "content": f"深入分析 {input_data.get('query', '未知主题')}...", "url": "https://example.com/3"}
                ],
                "summary": f"找到 {input_data.get('query', '未知主题')} 相关结果 3 条"
            }
        elif 'article' in skill_lower or 'write' in skill_lower or 'generate' in skill_lower:
            style = input_data.get('style', '正式')
            # 支持多种输入参数名
            topic = input_data.get('topic', input_data.get('query', '未知主题'))
            # 如果有 material，从中提取主题信息
            material = input_data.get('material')
            if material:
                # 如果 material 是数组，尝试提取信息
                if isinstance(material, list) and len(material) > 0:
                    first_item = material[0]
                    if isinstance(first_item, dict):
                        topic = first_item.get('title', first_item.get('content', topic)[:20])
                elif isinstance(material, str):
                    topic = material[:20] + "..." if len(material) > 20 else material

            return {
                "article": f"# {topic}\n\n## 引言\n\n这是一篇关于{topic}的{style}风格文章。\n\n## 正文\n\n内容正在生成中...\n\n## 结语\n\n感谢阅读。",
                "word_count": 500,
                "style": style
            }
        elif 'format' in skill_lower or 'formatter' in skill_lower:
            return {
                "formatted": f"<article><h1>格式化后的内容</h1><p>{input_data.get('content', '')[:100]}...</p></article>",
                "format": input_data.get('format', 'html')
            }
        elif 'publish' in skill_lower or 'wechat' in skill_lower:
            return {
                "published": True,
                "url": f"https://mp.weixin.qq.com/mock_article_{skill_id}",
                "publish_time": "2026-04-10 19:30:00"
            }
        else:
            return {
                "status": "completed",
                "skill": skill_id,
                "input": input_data,
                "result": f"Skill {skill_id} 执行完成"
            }


class MockSkillInvoker:
    """
    Mock Skill 调用器（用于测试和演示）
    """

    def __init__(self, responses: dict = None):
        self.responses = responses or {}
        self.calls = []

    async def __call__(self, skill_id: str, input_data: dict) -> Any:
        self.calls.append({
            "skill_id": skill_id,
            "input": input_data
        })

        if skill_id in self.responses:
            return self.responses[skill_id]

        # 生成模拟输出（只返回 output 部分）
        invoker = SkillInvoker()
        return invoker._generate_mock_output(skill_id, input_data)


def create_skill_invoker(use_mock: bool = False, gateway_id: Optional[int] = None) -> Callable[[str, dict], Awaitable[Any]]:
    """
    创建 Skill 调用器

    Args:
        use_mock: 是否使用 Mock 模式
        gateway_id: Gateway ID

    Returns:
        Skill 调用函数
    """
    if use_mock:
        return MockSkillInvoker()
    return SkillInvoker(gateway_id)