"""
Workflow Orchestration Agent Service.

This service handles natural language interaction for workflow creation and management.
"""

import json
import re
from typing import Optional, Callable, Awaitable, Any
from datetime import datetime

from .models import Workflow, WorkflowNode, WorkflowEdge, InputParam
from .io import WorkflowIO


class OrchestrationAgent:
    """
    编排Agent - 处理自然语言交互的工作流管理

    职责：
    - 理解用户自然语言意图
    - 创建/修改工作流
    - 解析需要的步骤和Skill
    - 自动建立变量绑定关系
    """

    def __init__(
        self,
        workflow_io: WorkflowIO = None,
        llm_caller: Callable[[str], Awaitable[str]] = None
    ):
        """
        初始化编排Agent

        Args:
            workflow_io: 工作流文件操作
            llm_caller: LLM调用函数，签名为 async (prompt: str) -> str
        """
        self.workflow_io = workflow_io or WorkflowIO()
        self.llm_caller = llm_caller

    async def handle_message(self, message: str, context: dict = None) -> dict:
        """
        处理用户消息

        Args:
            message: 用户输入的自然语言
            context: 上下文信息（当前工作流等）

        Returns:
            响应结果，包含 action, message, data 等字段
        """
        context = context or {}

        # 1. 解析意图
        intent = await self._parse_intent(message, context)

        # 2. 根据意图执行操作
        action = intent.get('action')

        if action == 'create':
            return await self._handle_create(intent, context)
        elif action == 'modify':
            return await self._handle_modify(intent, context)
        elif action == 'execute':
            return await self._handle_execute(intent, context)
        elif action == 'query':
            return await self._handle_query(intent, context)
        elif action == 'list':
            return await self._handle_list(intent, context)
        else:
            return {
                'action': 'unknown',
                'message': '抱歉，我不太理解你的意思。你可以尝试说"创建工作流"、"修改工作流"或"执行工作流"。',
                'data': None
            }

    async def _parse_intent(self, message: str, context: dict) -> dict:
        """
        解析用户意图

        Args:
            message: 用户消息
            context: 上下文

        Returns:
            意图对象
        """
        if not self.llm_caller:
            # 没有配置LLM，使用规则匹配
            return self._parse_intent_by_rules(message, context)

        # 使用LLM解析意图
        prompt = self._build_intent_prompt(message, context)
        response = await self.llm_caller(prompt)

        try:
            # 尝试解析JSON响应
            return json.loads(response)
        except json.JSONDecodeError:
            # 解析失败，回退到规则匹配
            return self._parse_intent_by_rules(message, context)

    def _parse_intent_by_rules(self, message: str, context: dict) -> dict:
        """基于规则的意图解析（不依赖LLM）"""
        message_lower = message.lower()

        # 创建工作流
        if any(kw in message_lower for kw in ['创建', '新建', '建一个', '帮我建']):
            return {
                'action': 'create',
                'name': self._extract_name(message),
                'description': message,
                'raw_message': message
            }

        # 列出工作流
        if any(kw in message_lower for kw in ['列出', '有哪些', '查看所有', '所有工作流']):
            return {
                'action': 'list',
                'raw_message': message
            }

        # 查询工作流
        if any(kw in message_lower for kw in ['查看', '显示', '详情', '是什么']):
            return {
                'action': 'query',
                'name': self._extract_name(message),
                'raw_message': message
            }

        # 执行工作流
        if any(kw in message_lower for kw in ['执行', '运行', '跑一下']):
            return {
                'action': 'execute',
                'name': self._extract_name(message),
                'raw_message': message
            }

        # 修改工作流
        if any(kw in message_lower for kw in ['修改', '更改', '更新', '改成']):
            return {
                'action': 'modify',
                'name': context.get('current_workflow') or self._extract_name(message),
                'raw_message': message
            }

        return {
            'action': 'unknown',
            'raw_message': message
        }

    def _extract_name(self, message: str) -> Optional[str]:
        """从消息中提取工作流名称"""
        # 尝试匹配引号中的名称
        match = re.search(r'["""]([^"""]+)["""]', message)
        if match:
            return match.group(1)

        # 尝试匹配"xxx工作流"模式（不包含"创建"、"新建"等动词）
        match = re.search(r'(?:创建|新建|查看|执行|修改)?[，\s]*([^\s，。！？创建新建查看执行修改]+?)工作流', message)
        if match:
            name = match.group(1)
            # 过滤掉一些常见的无意义词
            if name not in ['一个', '这个', '那个', '']:
                return name

        return None

    async def _handle_create(self, intent: dict, context: dict) -> dict:
        """处理创建工作流"""
        name = intent.get('name') or f"workflow_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        description = intent.get('description', '')

        # 如果有LLM，让LLM生成详细的工作流定义
        if self.llm_caller:
            workflow_data = await self._generate_workflow_with_llm(description, context)
            # 使用LLM生成的名称（如果有）
            if workflow_data.get('name'):
                name = workflow_data['name']
        else:
            # 没有LLM，创建一个空的工作流模板
            workflow_data = self._create_empty_workflow(name)

        # 创建工作流文件
        try:
            filepath = self.workflow_io.create(
                name=name,
                workflow=Workflow.from_dict(workflow_data),
                description=description
            )

            return {
                'action': 'create',
                'message': f'已创建工作流「{name}」，包含 {len(workflow_data.get("nodes", []))} 个步骤。',
                'data': {
                    'name': name,
                    'filepath': filepath,
                    'workflow': workflow_data
                }
            }
        except Exception as e:
            return {
                'action': 'create',
                'message': f'创建工作流失败：{str(e)}',
                'data': None,
                'error': str(e)
            }

    async def _handle_modify(self, intent: dict, context: dict) -> dict:
        """处理修改工作流"""
        name = intent.get('name') or context.get('current_workflow')

        if not name:
            return {
                'action': 'modify',
                'message': '请指定要修改的工作流名称。',
                'data': None
            }

        if not self.workflow_io.exists(name):
            return {
                'action': 'modify',
                'message': f'工作流「{name}」不存在。',
                'data': None
            }

        # TODO: 实现修改逻辑
        return {
            'action': 'modify',
            'message': f'修改工作流「{name}」的功能正在开发中。',
            'data': None
        }

    async def _handle_execute(self, intent: dict, context: dict) -> dict:
        """处理执行工作流"""
        name = intent.get('name') or context.get('current_workflow')

        if not name:
            return {
                'action': 'execute',
                'message': '请指定要执行的工作流名称。',
                'data': None
            }

        if not self.workflow_io.exists(name):
            return {
                'action': 'execute',
                'message': f'工作流「{name}」不存在。',
                'data': None
            }

        # 返回需要执行的信息，由调用方处理实际执行
        return {
            'action': 'execute',
            'message': f'准备执行工作流「{name}」。',
            'data': {
                'name': name,
                'user_input': intent.get('user_input', {})
            }
        }

    async def _handle_query(self, intent: dict, context: dict) -> dict:
        """处理查询工作流"""
        name = intent.get('name')

        if name:
            if not self.workflow_io.exists(name):
                return {
                    'action': 'query',
                    'message': f'工作流「{name}」不存在。',
                    'data': None
                }

            content, workflow = self.workflow_io.read(name)
            return {
                'action': 'query',
                'message': f'工作流「{name}」包含 {len(workflow.nodes)} 个步骤。',
                'data': {
                    'name': name,
                    'workflow': workflow.to_dict(),
                    'markdown': content
                }
            }
        else:
            # 列出所有工作流
            workflows = self.workflow_io.list_all()
            return {
                'action': 'list',
                'message': f'当前共有 {len(workflows)} 个工作流。',
                'data': {
                    'workflows': workflows
                }
            }

    async def _handle_list(self, intent: dict, context: dict) -> dict:
        """处理列出工作流"""
        workflows = self.workflow_io.list_all()

        if not workflows:
            return {
                'action': 'list',
                'message': '当前没有任何工作流。你可以说"创建一个xxx工作流"来创建新的工作流。',
                'data': {
                    'workflows': []
                }
            }

        workflow_list = '\n'.join([
            f"- {w['display_name']} ({w['name']}): {w.get('node_count', 0)} 个步骤"
            for w in workflows
        ])

        return {
            'action': 'list',
            'message': f'当前共有 {len(workflows)} 个工作流：\n{workflow_list}',
            'data': {
                'workflows': workflows
            }
        }

    async def _generate_workflow_with_llm(self, description: str, context: dict) -> dict:
        """使用LLM生成工作流定义"""
        prompt = self._build_workflow_generation_prompt(description, context)
        response = await self.llm_caller(prompt)

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # 尝试提取JSON
            match = re.search(r'\{[\s\S]*\}', response)
            if match:
                return json.loads(match.group())
            raise ValueError("LLM返回的内容无法解析为JSON")

    def _create_empty_workflow(self, name: str) -> dict:
        """创建空的工作流模板"""
        return {
            'id': f'wf_{datetime.now().strftime("%Y%m%d%H%M%S")}',
            'name': name,
            'version': '1.0',
            'nodes': [],
            'edges': [],
            'userInputSchema': {}
        }

    def _build_intent_prompt(self, message: str, context: dict) -> str:
        """构建意图解析的Prompt"""
        return f"""你是一个工作流编排助手。请分析用户的意图，返回JSON格式的响应。

用户消息: {message}

上下文: {json.dumps(context, ensure_ascii=False, indent=2)}

请返回以下JSON格式（只返回JSON，不要其他内容）：
{{
    "action": "create|modify|execute|query|list|unknown",
    "name": "工作流名称（如果提到的话）",
    "description": "工作流描述",
    "steps": [
        {{
            "name": "步骤名称",
            "skill": "skill_id（如果知道的话）",
            "description": "步骤描述"
        }}
    ],
    "user_input": {{
        "key": "用户提供的参数值"
    }}
}}
"""

    def _build_workflow_generation_prompt(self, description: str, context: dict) -> str:
        """构建工作流生成的Prompt"""
        available_skills = context.get('available_skills', [])

        skills_info = ""
        if available_skills:
            skills_info = "\n可用的Skills:\n" + "\n".join([f"- {s}" for s in available_skills])

        return f"""你是一个工作流设计专家。请根据用户描述生成工作流定义，返回JSON格式。

用户描述: {description}
{skills_info}

请返回以下JSON格式（只返回JSON，不要其他内容）：
{{
    "id": "wf_xxx",
    "name": "工作流名称",
    "version": "1.0",
    "nodes": [
        {{
            "id": "node_1",
            "name": "步骤名称",
            "type": "skill",
            "skill": "skill_id",
            "input": {{
                "param1": "${{user_input.xxx}}",
                "param2": "${{node_1.output.xxx}}"
            }}
        }}
    ],
    "edges": [
        {{ "from": "node_1", "to": "node_2" }}
    ],
    "userInputSchema": {{
        "xxx": {{ "type": "string", "description": "描述" }}
    }}
}}

注意：
1. 节点的input中使用 ${{user_input.xxx}} 引用用户输入
2. 节点的input中使用 ${{node_N.output.xxx}} 引用上游节点输出
3. 边定义节点之间的执行顺序
4. 只返回JSON，不要包含markdown代码块标记
"""