"""
Workflow execution engine.
Handles the execution of workflow nodes in topological order.
"""

import asyncio
import json
import re
from datetime import datetime
from typing import Optional, Any, Callable, Awaitable
from pathlib import Path

from .models import Workflow, WorkflowNode, Execution, NodeExecution
from .io import WorkflowIO, ExecutionIO, OutputIO


class WorkflowEngine:
    """
    工作流执行引擎

    职责：
    - 读取工作流定义
    - 拓扑排序确定执行顺序
    - 解析变量绑定
    - 调用 Skill 执行节点
    - 存储输出
    - 记录执行过程
    """

    def __init__(
        self,
        workflow_io: WorkflowIO = None,
        execution_io: ExecutionIO = None,
        output_io: OutputIO = None,
        skill_invoker: Callable[[str, dict], Awaitable[Any]] = None
    ):
        """
        初始化执行引擎

        Args:
            workflow_io: 工作流文件操作
            execution_io: 执行记录文件操作
            output_io: 节点输出文件操作
            skill_invoker: Skill 调用函数，签名为 async (skill_id: str, input: dict) -> Any
        """
        self.workflow_io = workflow_io or WorkflowIO()
        self.execution_io = execution_io or ExecutionIO()
        self.output_io = output_io or OutputIO()
        self.skill_invoker = skill_invoker

        # 运行时状态
        self.node_outputs: dict = {}      # 内存缓存：{node_id: output}
        self.user_input: dict = {}        # 用户输入
        self.current_execution: Optional[Execution] = None

        # 状态回调（用于实时通知前端）
        self.on_node_start: Optional[Callable[[str], Awaitable]] = None
        self.on_node_complete: Optional[Callable[[str, Any], Awaitable]] = None
        self.on_node_error: Optional[Callable[[str, str], Awaitable]] = None

    async def execute(
        self,
        workflow_name: str,
        user_input: dict,
        execution_id: str = None
    ) -> dict:
        """
        执行工作流

        Args:
            workflow_name: 工作流名称
            user_input: 用户输入参数
            execution_id: 执行 ID（可选，默认自动生成）

        Returns:
            最终输出
        """
        # 1. 读取工作流定义
        _, workflow = self.workflow_io.read(workflow_name)

        # 2. 初始化执行状态
        self.user_input = user_input
        self.node_outputs = {}

        if not execution_id:
            execution_id = f"exec_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        self.current_execution = Execution(
            execution_id=execution_id,
            workflow_id=workflow.id,
            workflow_name=workflow.name,
            status="running",
            user_input=user_input,
            started_at=datetime.now()
        )

        # 3. 获取执行顺序
        order = workflow.get_execution_order()

        # 4. 初始化节点执行记录
        for node_id in order:
            self.current_execution.node_executions.append(
                NodeExecution(node_id=node_id, status="pending")
            )

        # 5. 逐节点执行
        try:
            for node_id in order:
                node = workflow.get_node(node_id)
                if not node:
                    raise ValueError(f"节点不存在: {node_id}")

                await self._execute_node(workflow_name, execution_id, node)

            # 执行成功
            self.current_execution.status = "completed"
            self.current_execution.completed_at = datetime.now()

            # 获取最终输出
            if order:
                last_node_id = order[-1]
                self.current_execution.final_output = self.node_outputs.get(last_node_id)
            else:
                # 没有节点的工作流
                self.current_execution.final_output = {"message": "工作流没有节点"}

        except Exception as e:
            # 执行失败
            self.current_execution.status = "failed"
            self.current_execution.completed_at = datetime.now()

            # 记录错误到当前节点
            for ne in self.current_execution.node_executions:
                if ne.status == "running":
                    ne.status = "failed"
                    ne.error = str(e)
                    break

            raise

        finally:
            # 6. 保存执行记录
            self.execution_io.create(workflow_name, self.current_execution)

        return self.current_execution.final_output or {}

    async def _execute_node(
        self,
        workflow_name: str,
        execution_id: str,
        node: WorkflowNode
    ):
        """
        执行单个节点

        Args:
            workflow_name: 工作流名称
            execution_id: 执行 ID
            node: 节点定义
        """
        # 更新节点状态
        ne = self._get_node_execution(node.id)
        ne.status = "running"
        ne.started_at = datetime.now()

        # 通知前端
        if self.on_node_start:
            await self.on_node_start(node.id)

        try:
            # 1. 解析输入
            input_data = self._resolve_inputs(node.input)

            # 2. 根据节点类型执行
            if node.type == "skill":
                output = await self._invoke_skill(node.skill, input_data)
            elif node.type == "agent":
                output = await self._invoke_agent(node.agent_id, input_data)
            else:
                raise ValueError(f"未知节点类型: {node.type}")

            # 3. 存到内存
            self.node_outputs[node.id] = output

            # 4. 存到文件
            output_file = self.output_io.save(workflow_name, execution_id, node.id, output)

            # 5. 更新节点状态
            ne.status = "completed"
            ne.completed_at = datetime.now()
            ne.duration = (ne.completed_at - ne.started_at).total_seconds()
            ne.output_file = output_file

            # 6. 通知前端
            if self.on_node_complete:
                await self.on_node_complete(node.id, output)

        except Exception as e:
            ne.status = "failed"
            ne.completed_at = datetime.now()
            ne.duration = (ne.completed_at - ne.started_at).total_seconds()
            ne.error = str(e)

            if self.on_node_error:
                await self.on_node_error(node.id, str(e))

            raise

    def _resolve_inputs(self, input_config: dict) -> dict:
        """
        解析输入变量绑定

        Args:
            input_config: 输入配置，如 {"query": "${user_input.topic}"}

        Returns:
            实际输入值
        """
        result = {}

        for param, expr in input_config.items():
            result[param] = self._evaluate_expression(expr)

        return result

    def _evaluate_expression(self, expr: Any) -> Any:
        """
        解析表达式

        支持的表达式格式：
        - "${user_input.xxx}" - 引用用户输入
        - "${node_1.output.xxx}" - 引用节点输出
        - 固定值（非字符串或不以 ${ 开头）

        Args:
            expr: 表达式

        Returns:
            实际值
        """
        # 非字符串，直接返回
        if not isinstance(expr, str):
            return expr

        # 不以 ${ 开头，直接返回
        if not expr.startswith("${"):
            return expr

        # 解析变量引用
        # 格式: ${source.field1.field2...}
        path = expr[2:-1]  # 去掉 ${ }
        parts = path.split(".")

        if not parts:
            return expr

        source = parts[0]

        if source == "user_input":
            # 引用用户输入
            if len(parts) < 2:
                raise ValueError(f"无效的用户输入引用: {expr}")
            return self.user_input.get(parts[1])

        else:
            # 引用节点输出: ${node_1.output.results}
            # parts = ["node_1", "output", "results", ...]
            node_id = source
            value = self.node_outputs.get(node_id)

            if value is None:
                raise ValueError(f"节点输出不存在: {node_id}")

            # 从第2个部分开始遍历字段路径
            # 但如果第2个部分是 "output"，则跳过它
            start_idx = 1
            if len(parts) > 1 and parts[1] == "output":
                start_idx = 2

            for i in range(start_idx, len(parts)):
                field = parts[i]
                if isinstance(value, dict):
                    value = value.get(field)
                elif isinstance(value, list) and field.isdigit():
                    idx = int(field)
                    if 0 <= idx < len(value):
                        value = value[idx]
                    else:
                        value = None
                else:
                    value = None

                if value is None:
                    break

            return value

    async def _invoke_skill(self, skill_id: str, input_data: dict) -> Any:
        """
        调用 Skill

        Args:
            skill_id: Skill ID
            input_data: 输入数据

        Returns:
            Skill 输出
        """
        if self.skill_invoker:
            return await self.skill_invoker(skill_id, input_data)

        # 默认实现：模拟调用
        # 实际使用时应该注入真实的 Skill 调用器
        raise NotImplementedError(
            f"未配置 skill_invoker，无法调用 Skill: {skill_id}。"
            "请在初始化 WorkflowEngine 时传入 skill_invoker 参数。"
        )

    async def _invoke_agent(self, agent_id: str, input_data: dict) -> Any:
        """
        调用 Agent

        Args:
            agent_id: Agent ID
            input_data: 输入数据

        Returns:
            Agent 输出
        """
        # TODO: 实现 Agent 调用
        raise NotImplementedError("Agent 节点尚未实现")

    def _get_node_execution(self, node_id: str) -> NodeExecution:
        """获取节点执行记录"""
        for ne in self.current_execution.node_executions:
            if ne.node_id == node_id:
                return ne
        raise ValueError(f"节点执行记录不存在: {node_id}")

    # ==================== 辅助方法 ====================

    def get_node_output(self, node_id: str) -> Any:
        """获取已执行节点的输出"""
        return self.node_outputs.get(node_id)

    def get_all_outputs(self) -> dict:
        """获取所有节点输出"""
        return self.node_outputs.copy()


class MockSkillInvoker:
    """
    模拟 Skill 调用器（用于测试）
    """

    def __init__(self, responses: dict = None):
        """
        初始化

        Args:
            responses: 预设响应，格式为 {skill_id: response}
        """
        self.responses = responses or {}
        self.calls = []  # 记录所有调用

    async def __call__(self, skill_id: str, input_data: dict) -> Any:
        """调用 Skill"""
        self.calls.append({
            "skill_id": skill_id,
            "input": input_data,
            "timestamp": datetime.now().isoformat()
        })

        # 返回预设响应或模拟数据
        if skill_id in self.responses:
            return self.responses[skill_id]

        # 默认模拟响应
        return {
            "status": "ok",
            "skill": skill_id,
            "input": input_data,
            "output": f"Mock output from {skill_id}"
        }