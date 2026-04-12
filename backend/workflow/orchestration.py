"""
Workflow Orchestration - 编排引擎

Backend 只负责编排，不执行 Skill。
Prometheus Agent 通过编排 API 获取执行指令。
"""

import json
from datetime import datetime
from typing import Optional, Any, Dict, List
from pathlib import Path

from .models import Workflow, WorkflowNode, WorkflowEdge, Execution, NodeExecution
from .io import WorkflowIO, ExecutionIO, OutputIO


class OrchestrationEngine:
    """
    编排引擎

    职责：
    - 读取工作流定义
    - 拓扑排序确定执行顺序
    - 解析变量绑定
    - 返回"下一步执行什么"的指令
    - 接收节点执行结果
    - 存储输出和执行记录
    """

    def __init__(
        self,
        workflow_io: WorkflowIO = None,
        execution_io: ExecutionIO = None,
        output_io: OutputIO = None
    ):
        self.workflow_io = workflow_io or WorkflowIO()
        self.execution_io = execution_io or ExecutionIO()
        self.output_io = output_io or OutputIO()

        # 运行时状态（按 execution_id 存储）
        self.executions: Dict[str, Dict] = {}  # {execution_id: state}

    def start(
        self,
        workflow_name: str,
        user_input: dict,
        execution_id: str = None
    ) -> Dict:
        """
        开始工作流执行

        Returns:
            编排指令：
            {
                "status": "running",
                "execution_id": "exec_xxx",
                "next_action": "execute_node",
                "node_id": "node_1",
                "node_name": "搜索资料",
                "type": "skill",
                "skill": "baidu-search",
                "agent_id": null,
                "input": {"query": "AI技术"},
                "progress": {
                    "completed": [],
                    "running": "node_1",
                    "pending": ["node_2", "node_3"]
                }
            }
        """
        # 读取工作流
        if not self.workflow_io.exists(workflow_name):
            return {"status": "error", "error": f"工作流不存在: {name}"}

        _, workflow = self.workflow_io.read(workflow_name)

        # 生成 execution_id
        if not execution_id:
            execution_id = f"exec_{datetime.now().strftime('%Y%m%d%H%M%S')}_{workflow_name}"

        # 获取执行顺序
        order = workflow.get_execution_order()

        # 初始化执行状态
        state = {
            "workflow": workflow,
            "workflow_name": workflow_name,
            "user_input": user_input,
            "execution_id": execution_id,
            "order": order,  # 执行顺序列表
            "current_index": 0,  # 当前执行到哪个节点
            "node_outputs": {},  # 节点输出
            "completed": [],  # 已完成的节点
            "started_at": datetime.now().isoformat(),
            "status": "running"
        }
        self.executions[execution_id] = state

        # 返回第一个节点的执行指令
        return self._get_next_instruction(state)

    def submit_result(
        self,
        execution_id: str,
        node_id: str,
        output: Any
    ) -> Dict:
        """
        提交节点执行结果

        Args:
            execution_id: 执行 ID
            node_id: 节点 ID
            output: 节点输出

        Returns:
            下一个编排指令，或完成/失败状态
        """
        state = self.executions.get(execution_id)
        if not state:
            return {"status": "error", "error": f"执行不存在: {execution_id}"}

        # 存储输出
        state["node_outputs"][node_id] = output

        # 标记完成
        state["completed"].append(node_id)
        state["current_index"] += 1

        # 存储到文件
        self.output_io.save(
            state["workflow_name"],
            execution_id,
            node_id,
            output
        )

        # 检查是否完成
        if state["current_index"] >= len(state["order"]):
            state["status"] = "completed"
            state["completed_at"] = datetime.now().isoformat()

            # 保存执行记录
            execution = Execution(
                execution_id=execution_id,
                workflow_id=state["workflow"].id,
                workflow_name=state["workflow_name"],
                status="completed",
                user_input=state["user_input"],
                started_at=datetime.fromisoformat(state["started_at"]),
                completed_at=datetime.now(),
                final_output=output
            )
            self.execution_io.create(state["workflow_name"], execution)

            return {
                "status": "completed",
                "execution_id": execution_id,
                "final_output": output,
                "progress": {
                    "completed": state["completed"],
                    "running": None,
                    "pending": []
                }
            }

        # 返回下一个节点的执行指令
        return self._get_next_instruction(state)

    def submit_error(
        self,
        execution_id: str,
        node_id: str,
        error: str
    ) -> Dict:
        """
        提交节点执行错误
        """
        state = self.executions.get(execution_id)
        if not state:
            return {"status": "error", "error": f"执行不存在: {execution_id}"}

        state["status"] = "failed"
        state["failed_at"] = datetime.now().isoformat()
        state["failed_node"] = node_id
        state["error"] = error

        # 保存执行记录
        execution = Execution(
            execution_id=execution_id,
            workflow_id=state["workflow"].id,
            workflow_name=state["workflow_name"],
            status="failed",
            user_input=state["user_input"],
            started_at=datetime.fromisoformat(state["started_at"]),
            completed_at=datetime.now(),
            error=error
        )
        self.execution_io.create(state["workflow_name"], execution)

        return {
            "status": "failed",
            "execution_id": execution_id,
            "error": error,
            "failed_node": node_id
        }

    def get_status(self, execution_id: str) -> Dict:
        """
        获取执行状态
        """
        state = self.executions.get(execution_id)
        if not state:
            return {"status": "error", "error": f"执行不存在: {execution_id}"}

        return {
            "status": state["status"],
            "execution_id": execution_id,
            "workflow_name": state["workflow_name"],
            "progress": {
                "completed": state["completed"],
                "running": state["order"][state["current_index"]] if state["current_index"] < len(state["order"]) else None,
                "pending": state["order"][state["current_index"]+1:] if state["current_index"] < len(state["order"]) else []
            }
        }

    def continue_from(
        self,
        execution_id: str,
        from_agent: str,
        context: dict
    ) -> Dict:
        """
        Agent 交接后继续执行

        当 Prometheus 执行到 agent 类型节点时，交接给指定 Agent。
        该 Agent 执行完后调用此方法继续后续节点。

        Args:
            execution_id: 执行 ID
            from_agent: 交接来的 Agent ID
            context: Agent 提供的上下文（包含节点输出等）

        Returns:
            下一个执行指令
        """
        state = self.executions.get(execution_id)
        if not state:
            return {"status": "error", "error": f"执行不存在: {execution_id}"}

        # 更新上下文（Agent 可能添加了额外的输出）
        if "node_outputs" in context:
            state["node_outputs"].update(context["node_outputs"])

        # Agent 执行完了当前节点，提交结果继续
        current_node_id = state["order"][state["current_index"]]
        if "output" in context:
            state["node_outputs"][current_node_id] = context["output"]

        state["completed"].append(current_node_id)
        state["current_index"] += 1

        # 存储到文件
        if "output" in context:
            self.output_io.save(
                state["workflow_name"],
                execution_id,
                current_node_id,
                context["output"]
            )

        # 检查是否完成
        if state["current_index"] >= len(state["order"]):
            state["status"] = "completed"
            state["completed_at"] = datetime.now().isoformat()
            return {
                "status": "completed",
                "execution_id": execution_id,
                "final_output": context.get("output"),
                "progress": {
                    "completed": state["completed"],
                    "running": None,
                    "pending": []
                }
            }

        # 返回下一个节点的执行指令
        return self._get_next_instruction(state)

    def _get_next_instruction(self, state: Dict) -> Dict:
        """
        获取下一个执行指令
        """
        workflow = state["workflow"]
        order = state["order"]
        current_index = state["current_index"]

        if current_index >= len(order):
            return {
                "status": "completed",
                "execution_id": state["execution_id"]
            }

        node_id = order[current_index]
        node = workflow.get_node(node_id)

        if not node:
            return {
                "status": "error",
                "error": f"节点不存在: {node_id}"
            }

        # 解析输入
        input_data = self._resolve_inputs(node.input, state)

        # 构建进度信息
        progress = {
            "completed": state["completed"],
            "running": node_id,
            "pending": order[current_index+1:]
        }

        return {
            "status": "running",
            "execution_id": state["execution_id"],
            "next_action": "execute_node" if node.type == "skill" else "handover",
            "node_id": node_id,
            "node_name": node.name,
            "type": node.type,
            "skill": node.skill if node.type == "skill" else None,
            "agent_id": node.agent_id if node.type == "agent" else None,
            "input": input_data,
            "workflow_name": state["workflow_name"],
            "context": {
                "previous_outputs": state["node_outputs"],
                "user_input": state["user_input"],
                "remaining_nodes": order[current_index+1:]
            },
            "progress": progress
        }

    def _resolve_inputs(self, input_config: Dict, state: Dict) -> Dict:
        """
        解析输入变量绑定

        ${user_input.xxx} -> 用户输入
        ${node_1.output.xxx} -> 节点输出
        """
        result = {}

        for param, expr in input_config.items():
            result[param] = self._evaluate_expression(expr, state)

        return result

    def _evaluate_expression(self, expr: Any, state: Dict) -> Any:
        """
        解析表达式
        """
        if not isinstance(expr, str):
            return expr

        if not expr.startswith("${"):
            return expr

        # 解析变量引用: ${source.field1.field2...}
        path = expr[2:-1]
        parts = path.split(".")

        if not parts:
            return expr

        source = parts[0]

        if source == "user_input":
            if len(parts) < 2:
                return expr
            return state["user_input"].get(parts[1])

        else:
            # 引用节点输出: ${node_1.output.xxx}
            node_id = source
            value = state["node_outputs"].get(node_id)

            if value is None:
                # 还没有输出，返回 null
                return None

            # 遍历字段路径
            start_idx = 1
            if len(parts) > 1 and parts[1] == "output":
                start_idx = 2

            for i in range(start_idx, len(parts)):
                field = parts[i]
                if isinstance(value, dict):
                    value = value.get(field)
                elif isinstance(value, list) and field.isdigit():
                    idx = int(field)
                    value = value[idx] if 0 <= idx < len(value) else None
                else:
                    value = None

                if value is None:
                    break

            return value