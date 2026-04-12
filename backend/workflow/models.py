"""
Workflow data models.
"""

from dataclasses import dataclass, field
from typing import Optional, Any
from datetime import datetime


@dataclass
class WorkflowNode:
    """工作流节点"""
    id: str
    name: str
    type: str  # 'skill' | 'agent'
    input: dict = field(default_factory=dict)
    skill: Optional[str] = None      # type=skill 时
    agent_id: Optional[str] = None   # type=agent 时

    def to_dict(self) -> dict:
        result = {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'input': self.input
        }
        if self.skill:
            result['skill'] = self.skill
        if self.agent_id:
            result['agent_id'] = self.agent_id
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'WorkflowNode':
        return cls(
            id=data['id'],
            name=data['name'],
            type=data['type'],
            input=data.get('input', {}),
            skill=data.get('skill'),
            agent_id=data.get('agent_id')
        )


@dataclass
class WorkflowEdge:
    """工作流边（连接）"""
    from_node: str
    to_node: str

    def to_dict(self) -> dict:
        return {
            'from': self.from_node,
            'to': self.to_node
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'WorkflowEdge':
        return cls(
            from_node=data['from'],
            to_node=data['to']
        )


@dataclass
class InputParam:
    """用户输入参数定义"""
    type: str
    description: str = ''
    enum: Optional[list] = None
    default: Optional[Any] = None

    def to_dict(self) -> dict:
        result = {
            'type': self.type,
            'description': self.description
        }
        if self.enum:
            result['enum'] = self.enum
        if self.default is not None:
            result['default'] = self.default
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'InputParam':
        return cls(
            type=data.get('type', 'string'),
            description=data.get('description', ''),
            enum=data.get('enum'),
            default=data.get('default')
        )


@dataclass
class Workflow:
    """工作流定义"""
    id: str
    name: str
    version: str = '1.0'
    nodes: list = field(default_factory=list)
    edges: list = field(default_factory=list)
    user_input_schema: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'version': self.version,
            'nodes': [n.to_dict() if isinstance(n, WorkflowNode) else n for n in self.nodes],
            'edges': [e.to_dict() if isinstance(e, WorkflowEdge) else e for e in self.edges],
            'userInputSchema': {
                k: v.to_dict() if isinstance(v, InputParam) else v
                for k, v in self.user_input_schema.items()
            }
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Workflow':
        nodes = [WorkflowNode.from_dict(n) if isinstance(n, dict) else n for n in data.get('nodes', [])]
        edges = [WorkflowEdge.from_dict(e) if isinstance(e, dict) else e for e in data.get('edges', [])]

        user_input_schema = {}
        for key, val in data.get('userInputSchema', {}).items():
            if isinstance(val, dict):
                user_input_schema[key] = InputParam.from_dict(val)
            else:
                user_input_schema[key] = val

        return cls(
            id=data['id'],
            name=data['name'],
            version=data.get('version', '1.0'),
            nodes=nodes,
            edges=edges,
            user_input_schema=user_input_schema
        )

    def get_node(self, node_id: str) -> Optional[WorkflowNode]:
        """根据 ID 获取节点"""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    def get_execution_order(self) -> list[str]:
        """获取拓扑排序后的执行顺序"""
        # 构建图
        graph = {n.id: [] for n in self.nodes}
        in_degree = {n.id: 0 for n in self.nodes}

        for edge in self.edges:
            graph[edge.from_node].append(edge.to_node)
            in_degree[edge.to_node] += 1

        # BFS 拓扑排序
        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        result = []

        while queue:
            node = queue.pop(0)
            result.append(node)
            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return result


@dataclass
class NodeExecution:
    """节点执行记录"""
    node_id: str
    status: str  # 'pending' | 'running' | 'completed' | 'failed'
    duration: float = 0
    output_file: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        result = {
            'nodeId': self.node_id,
            'status': self.status,
            'duration': self.duration
        }
        if self.output_file:
            result['outputFile'] = self.output_file
        if self.error:
            result['error'] = self.error
        if self.started_at:
            result['startedAt'] = self.started_at.isoformat()
        if self.completed_at:
            result['completedAt'] = self.completed_at.isoformat()
        return result


@dataclass
class Execution:
    """工作流执行记录"""
    execution_id: str
    workflow_id: str
    workflow_name: str
    status: str  # 'running' | 'completed' | 'failed'
    user_input: dict = field(default_factory=dict)
    node_executions: list = field(default_factory=list)
    final_output: Optional[dict] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        result = {
            'executionId': self.execution_id,
            'workflowId': self.workflow_id,
            'workflowName': self.workflow_name,
            'status': self.status,
            'userInput': self.user_input,
            'nodeExecutions': [e.to_dict() if isinstance(e, NodeExecution) else e for e in self.node_executions]
        }
        if self.final_output:
            result['finalOutput'] = self.final_output
        if self.started_at:
            result['startedAt'] = self.started_at.isoformat()
        if self.completed_at:
            result['completedAt'] = self.completed_at.isoformat()
        return result