"""
Workflow API routes (Flask Blueprint).
"""

from flask import Blueprint, request, jsonify
import asyncio
from typing import Dict, Any

from workflow import (
    WorkflowIO,
    ExecutionIO,
    OutputIO,
    WorkflowEngine,
    OrchestrationAgent,
    create_skill_invoker
)
from workflow.orchestration import OrchestrationEngine

# Create blueprint
bp = Blueprint('workflow', __name__, url_prefix='/api/workflow')

# Initialize components
workflow_io = WorkflowIO()
execution_io = ExecutionIO()
output_io = OutputIO()

# 编排引擎（用于 Prometheus 调用）
orchestration_engine = OrchestrationEngine(
    workflow_io=workflow_io,
    execution_io=execution_io,
    output_io=output_io
)

# 旧的执行引擎（保留用于测试）
skill_invoker = create_skill_invoker(use_mock=True)
engine = WorkflowEngine(
    workflow_io=workflow_io,
    execution_io=execution_io,
    output_io=output_io,
    skill_invoker=skill_invoker
)
agent = OrchestrationAgent(workflow_io=workflow_io)


# ==================== Helper Functions ====================

def run_async(coro):
    """Run async function in sync context"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


# ==================== Workflow CRUD ====================

@bp.route('/list', methods=['GET'])
def list_workflows():
    """列出所有工作流"""
    workflows = workflow_io.list_all()
    return jsonify({"success": True, "data": workflows})


@bp.route('/<name>', methods=['GET'])
def get_workflow(name):
    """获取工作流详情"""
    if not workflow_io.exists(name):
        return jsonify({"success": False, "error": f"工作流不存在: {name}"}), 404

    content, workflow = workflow_io.read(name)
    return jsonify({
        "success": True,
        "data": {
            "name": name,
            "markdown": content,
            "workflow": workflow.to_dict()
        }
    })


@bp.route('/create', methods=['POST'])
def create_workflow():
    """创建工作流"""
    data = request.get_json()
    name = data.get('name')
    description = data.get('description', '')
    nodes = data.get('nodes', [])
    edges = data.get('edges', [])
    user_input_schema = data.get('userInputSchema', {})

    if not name:
        return jsonify({"success": False, "error": "缺少工作流名称"}), 400

    from workflow.models import Workflow, WorkflowNode, WorkflowEdge, InputParam

    workflow_nodes = [WorkflowNode.from_dict(n) for n in nodes]
    workflow_edges = [WorkflowEdge.from_dict(e) for e in edges]

    # 构建 user_input_schema
    input_schema = {}
    for key, val in user_input_schema.items():
        if isinstance(val, dict):
            input_schema[key] = InputParam.from_dict(val)
        else:
            input_schema[key] = val

    workflow = Workflow(
        id=f"wf_{name}",
        name=name,
        nodes=workflow_nodes,
        edges=workflow_edges,
        user_input_schema=input_schema
    )

    try:
        filepath = workflow_io.create(name, workflow, description)
        return jsonify({
            "success": True,
            "message": f"工作流「{name}」创建成功",
            "data": {
                "name": name,
                "filepath": filepath,
                "workflow": workflow.to_dict()
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route('/<name>', methods=['PUT'])
def update_workflow(name):
    """更新工作流"""
    if not workflow_io.exists(name):
        return jsonify({"success": False, "error": f"工作流不存在: {name}"}), 404

    data = request.get_json()
    from workflow.models import WorkflowNode, WorkflowEdge

    _, workflow = workflow_io.read(name)

    if 'nodes' in data:
        workflow.nodes = [WorkflowNode.from_dict(n) for n in data['nodes']]
    if 'edges' in data:
        workflow.edges = [WorkflowEdge.from_dict(e) for e in data['edges']]

    workflow_io.update_json(name, workflow)

    return jsonify({"success": True, "message": f"工作流「{name}」已更新"})


@bp.route('/<name>', methods=['DELETE'])
def delete_workflow(name):
    """删除工作流"""
    if not workflow_io.exists(name):
        return jsonify({"success": False, "error": f"工作流不存在: {name}"}), 404

    workflow_io.delete(name)
    return jsonify({"success": True, "message": f"工作流「{name}」已删除"})


@bp.route('/<name>/validate', methods=['GET'])
def validate_workflow(name):
    """验证工作流"""
    is_valid, error = workflow_io.validate(name)
    return jsonify({"success": True, "data": {"valid": is_valid, "error": error}})


# ==================== Execution ====================

@bp.route('/execute', methods=['POST'])
def execute_workflow():
    """执行工作流"""
    data = request.get_json()
    name = data.get('name')
    user_input = data.get('user_input', {})

    if not name:
        return jsonify({"success": False, "error": "缺少工作流名称"}), 400

    if not workflow_io.exists(name):
        return jsonify({"success": False, "error": f"工作流不存在: {name}"}), 404

    try:
        result = run_async(engine.execute(name, user_input))
        return jsonify({
            "success": True,
            "message": f"工作流「{name}」执行完成",
            "data": {
                "execution_id": engine.current_execution.execution_id,
                "output": result
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route('/<name>/executions', methods=['GET'])
def list_executions(name):
    """列出工作流的执行记录"""
    if not workflow_io.exists(name):
        return jsonify({"success": False, "error": f"工作流不存在: {name}"}), 404

    executions = execution_io.list_all(name)
    return jsonify({"success": True, "data": executions})


@bp.route('/<name>/executions/<filename>', methods=['GET'])
def get_execution(name, filename):
    """获取执行记录详情"""
    try:
        content, execution = execution_io.read(name, filename)
        return jsonify({
            "success": True,
            "data": {
                "markdown": content,
                "execution": execution.to_dict()
            }
        })
    except FileNotFoundError:
        return jsonify({"success": False, "error": "执行记录不存在"}), 404


@bp.route('/<name>/outputs/<execution_id>/<node_id>', methods=['GET'])
def get_node_output(name, execution_id, node_id):
    """获取节点输出"""
    output = output_io.load(name, execution_id, node_id)
    if output is None:
        return jsonify({"success": False, "error": "输出不存在"}), 404
    return jsonify({"success": True, "data": output})


# ==================== Agent Chat ====================

@bp.route('/chat', methods=['POST'])
def agent_chat():
    """与编排Agent对话"""
    data = request.get_json()
    message = data.get('message', '')
    context = data.get('context', {})

    if not message:
        return jsonify({"success": False, "error": "消息不能为空"}), 400

    result = run_async(agent.handle_message(message, context))
    return jsonify({"success": True, "data": result})


# ==================== Orchestration (编排 API) ====================

@bp.route('/orchestrate/start', methods=['POST'])
def orchestrate_start():
    """
    开始工作流编排

    返回第一个节点的执行指令，让 Prometheus 去执行
    """
    data = request.get_json()
    name = data.get('name')
    user_input = data.get('user_input', {})
    execution_id = data.get('execution_id')  # 可选

    if not name:
        return jsonify({"success": False, "error": "缺少工作流名称"}), 400

    result = orchestration_engine.start(name, user_input, execution_id)

    if result.get("status") == "error":
        return jsonify({"success": False, "error": result.get("error")}), 400

    return jsonify({"success": True, "data": result})


@bp.route('/orchestrate/result', methods=['POST'])
def orchestrate_submit_result():
    """
    提交节点执行结果

    Prometheus 执行完节点后，提交结果，获取下一个节点指令
    """
    data = request.get_json()
    execution_id = data.get('execution_id')
    node_id = data.get('node_id')
    output = data.get('output')

    if not execution_id:
        return jsonify({"success": False, "error": "缺少 execution_id"}), 400
    if not node_id:
        return jsonify({"success": False, "error": "缺少 node_id"}), 400

    result = orchestration_engine.submit_result(execution_id, node_id, output)

    if result.get("status") == "error":
        return jsonify({"success": False, "error": result.get("error")}), 400

    return jsonify({"success": True, "data": result})


@bp.route('/orchestrate/error', methods=['POST'])
def orchestrate_submit_error():
    """
    提交节点执行错误

    Prometheus 执行节点失败时提交
    """
    data = request.get_json()
    execution_id = data.get('execution_id')
    node_id = data.get('node_id')
    error = data.get('error')

    if not execution_id:
        return jsonify({"success": False, "error": "缺少 execution_id"}), 400
    if not node_id:
        return jsonify({"success": False, "error": "缺少 node_id"}), 400

    result = orchestration_engine.submit_error(execution_id, node_id, error)

    return jsonify({"success": True, "data": result})


@bp.route('/orchestrate/status/<execution_id>', methods=['GET'])
def orchestrate_get_status(execution_id):
    """
    获取执行状态

    用于查询当前进度
    """
    result = orchestration_engine.get_status(execution_id)

    if result.get("status") == "error":
        return jsonify({"success": False, "error": result.get("error")}), 404

    return jsonify({"success": True, "data": result})


@bp.route('/orchestrate/continue', methods=['POST'])
def orchestrate_continue():
    """
    Agent 交接后继续执行

    当 Prometheus 执行到 agent 类型节点时，交接给指定 Agent。
    该 Agent 执行完后调用此方法继续后续节点。

    请求体:
    {
        "execution_id": "exec_xxx",
        "from_agent": "agent_zhangsan",
        "context": {
            "output": {...},  // Agent 节点的输出
            "node_outputs": {...}  // 可选，Agent 执行期间的其他节点输出
        }
    }
    """
    data = request.get_json()
    execution_id = data.get('execution_id')
    from_agent = data.get('from_agent')
    context = data.get('context', {})

    if not execution_id:
        return jsonify({"success": False, "error": "缺少 execution_id"}), 400

    result = orchestration_engine.continue_from(execution_id, from_agent, context)

    if result.get("status") == "error":
        return jsonify({"success": False, "error": result.get("error")}), 400

    return jsonify({"success": True, "data": result})