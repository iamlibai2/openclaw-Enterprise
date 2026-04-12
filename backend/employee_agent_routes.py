"""
员工 Agent API 路由

提供员工-Agent 功能的 REST API：
- 绑定关系管理
- Agent 配置管理
- Agent 能力注册
- Agent 选择 API
- 工作流发起记录查询
"""

import json
from datetime import datetime
from flask import Blueprint, request, jsonify
from functools import wraps
from typing import Dict, Any

from employee_agent_service import (
    EmployeeAgentService,
    AgentCapabilityService,
    AgentSelectionService,
    WorkflowInitiationService,
    AgentConfig,
    AgentCapability,
    init_employee_agent_service
)

from database import db, SessionLocal
from settings import settings


bp = Blueprint('employee_agent', __name__, url_prefix='/api/employee-agent')


# ============================================================
# 认证装饰器
# ============================================================

def auth_required(f):
    """认证装饰器 - 支持内部 API Token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'success': False, 'error': '未授权'}), 401

        # 检查是否是内部 API Token
        if token == settings.INTERNAL_API_TOKEN:
            return f(*args, **kwargs)

        # 否则需要正常的用户认证（后续可扩展 JWT 验证）
        return f(*args, **kwargs)
    return decorated


# ============================================================
# 绑定关系 API
# ============================================================

@bp.route('/<int:employee_id>/agents', methods=['GET'])
@auth_required
def get_bound_agents(employee_id):
    """
    获取员工绑定的 Agent 列表

    Args:
        employee_id: 员工 ID

    Returns:
        {
            "success": true,
            "data": {
                "agentIds": ["agent1", "agent2"],
                "agents": [
                    {"id": "agent1", "name": "Agent 1", "status": "idle"},
                    ...
                ]
            }
        }
    """
    service = EmployeeAgentService()

    try:
        agent_ids = service.get_bound_agents(employee_id)

        # 获取每个 Agent 的详细信息（从 Gateway）
        agents_detail = []
        from agent_profile import get_gateway_client
        client = get_gateway_client()

        for agent_id in agent_ids:
            config = client.get_agent_config(agent_id)
            if config:
                agents_detail.append({
                    'id': agent_id,
                    'name': config.get('name', agent_id),
                    'status': 'idle',  # TODO: 从 AgentProfile 获取
                    'skills': config.get('skills', [])
                })

        return jsonify({
            'success': True,
            'data': {
                'agentIds': agent_ids,
                'agents': agents_detail
            }
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        service.close()


@bp.route('/<int:employee_id>/agents', methods=['POST'])
@auth_required
def bind_agent(employee_id):
    """
    绑定 Agent 到员工

    Body:
    {
        "agentId": "agent1"
    }
    """
    service = EmployeeAgentService()
    data = request.get_json() or {}

    agent_id = data.get('agentId')
    if not agent_id:
        return jsonify({'success': False, 'error': 'agentId 不能为空'}), 400

    try:
        # 检查 Agent 是否存在
        from agent_profile import get_gateway_client
        client = get_gateway_client()

        if not client.agent_exists(agent_id):
            return jsonify({'success': False, 'error': f"Agent '{agent_id}' 不存在"}), 404

        # 绑定
        success = service.bind_agent(employee_id, agent_id)

        if success:
            return jsonify({'success': True, 'message': '绑定成功'})
        else:
            return jsonify({'success': False, 'error': '员工不存在'}), 404

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        service.close()


@bp.route('/<int:employee_id>/agents/<agent_id>', methods=['DELETE'])
@auth_required
def unbind_agent(employee_id, agent_id):
    """
    解绑 Agent
    """
    service = EmployeeAgentService()

    try:
        success = service.unbind_agent(employee_id, agent_id)

        if success:
            return jsonify({'success': True, 'message': '解绑成功'})
        else:
            return jsonify({'success': False, 'error': '员工不存在'}), 404

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        service.close()


# ============================================================
# Agent 配置 API
# ============================================================

@bp.route('/<int:employee_id>/config', methods=['GET'])
@auth_required
def get_agent_config(employee_id):
    """
    获取员工的 Agent 配置

    Returns:
    {
        "success": true,
        "data": {
            "autonomy": "high",
            "reportStyle": {
                "detailLevel": "summary",
                "timing": "on_complete"
            },
            "learning": {
                "rememberFeedback": true,
                "autoImprove": true
            }
        }
    }
    """
    service = EmployeeAgentService()

    try:
        config = service.get_agent_config(employee_id)

        return jsonify({
            'success': True,
            'data': {
                'autonomy': config.autonomy,
                'reportStyle': {
                    'detailLevel': config.report_style.get('detail_level', 'summary'),
                    'timing': config.report_style.get('timing', 'on_complete')
                },
                'learning': {
                    'rememberFeedback': config.learning.get('remember_feedback', True),
                    'autoImprove': config.learning.get('auto_improve', True)
                }
            }
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        service.close()


@bp.route('/<int:employee_id>/config', methods=['PUT'])
@auth_required
def update_agent_config(employee_id):
    """
    更新员工的 Agent 配置

    Body:
    {
        "autonomy": "high",
        "reportStyle": {
            "detailLevel": "summary",
            "timing": "on_complete"
        },
        "learning": {
            "rememberFeedback": true,
            "autoImprove": true
        }
    }
    """
    service = EmployeeAgentService()
    data = request.get_json() or {}

    try:
        # 构建配置对象
        config = AgentConfig(
            autonomy=data.get('autonomy', 'high'),
            report_style={
                'detail_level': data.get('reportStyle', {}).get('detailLevel', 'summary'),
                'timing': data.get('reportStyle', {}).get('timing', 'on_complete')
            },
            learning={
                'remember_feedback': data.get('learning', {}).get('rememberFeedback', True),
                'auto_improve': data.get('learning', {}).get('autoImprove', True)
            }
        )

        success = service.update_agent_config(employee_id, config)

        if success:
            return jsonify({'success': True, 'message': '配置更新成功'})
        else:
            return jsonify({'success': False, 'error': '员工不存在'}), 404

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        service.close()


@bp.route('/<int:employee_id>/autonomy', methods=['PUT'])
@auth_required
def set_autonomy(employee_id):
    """
    设置自主性级别

    Body:
    {
        "autonomy": "high"  // high / medium / low
    }
    """
    service = EmployeeAgentService()
    data = request.get_json() or {}

    autonomy = data.get('autonomy')
    if autonomy not in ['high', 'medium', 'low']:
        return jsonify({'success': False, 'error': 'autonomy 必须是 high/medium/low'}), 400

    try:
        success = service.set_autonomy(employee_id, autonomy)

        if success:
            return jsonify({'success': True, 'message': '自主性已设置'})
        else:
            return jsonify({'success': False, 'error': '员工不存在'}), 404

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        service.close()


# ============================================================
# Agent 能力注册 API
# ============================================================

@bp.route('/agents/<agent_id>/capability', methods=['GET'])
@auth_required
def get_agent_capability(agent_id):
    """
    获取 Agent 能力信息

    Returns:
    {
        "success": true,
        "data": {
            "agentId": "agent1",
            "capabilities": ["数据分析", "写作"],
            "skills": ["data-analyzer", "writer"],
            "expertiseLevel": {"数据分析": 90, "写作": 80},
            "status": "idle",
            "currentTasks": 0,
            "successRate": 0.95
        }
    }
    """
    service = AgentCapabilityService()

    try:
        capability = service.get_capability(agent_id)

        if capability is None:
            # 返回默认值
            return jsonify({
                'success': True,
                'data': {
                    'agentId': agent_id,
                    'capabilities': [],
                    'skills': [],
                    'expertiseLevel': {},
                    'status': 'idle',
                    'currentTasks': 0,
                    'successRate': 0.95
                }
            })

        return jsonify({
            'success': True,
            'data': {
                'agentId': capability.agent_id,
                'capabilities': capability.capabilities,
                'skills': capability.skills,
                'expertiseLevel': capability.expertise_level,
                'status': capability.status,
                'currentTasks': capability.current_tasks,
                'successRate': capability.success_rate
            }
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        service.close()


@bp.route('/agents/<agent_id>/capability', methods=['PUT'])
@auth_required
def register_agent_capability(agent_id):
    """
    注册 Agent 能力

    Body:
    {
        "capabilities": ["数据分析", "写作"],
        "skills": ["data-analyzer", "writer"],
        "expertiseLevel": {"数据分析": 90, "写作": 80}
    }
    """
    service = AgentCapabilityService()
    data = request.get_json() or {}

    capabilities = data.get('capabilities', [])
    skills = data.get('skills', [])
    expertise_level = data.get('expertiseLevel', {})

    try:
        success = service.register_capability(
            agent_id,
            capabilities,
            skills,
            expertise_level
        )

        if success:
            return jsonify({'success': True, 'message': '能力注册成功'})
        else:
            return jsonify({'success': False, 'error': '注册失败'}), 500

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        service.close()


@bp.route('/agents/<agent_id>/status', methods=['PUT'])
@auth_required
def update_agent_status(agent_id):
    """
    更新 Agent 状态（内部调用）

    Body:
    {
        "status": "busy",
        "currentTasks": 2
    }
    """
    service = AgentCapabilityService()
    data = request.get_json() or {}

    status = data.get('status')
    current_tasks = data.get('currentTasks')

    try:
        success = service.update_status(agent_id, status, current_tasks)

        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Agent 不存在'}), 404

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        service.close()


@bp.route('/agents/capability/<capability>', methods=['GET'])
@auth_required
def query_agents_by_capability(capability):
    """
    查询具有指定能力的 Agent

    Query params:
    - status: 状态过滤（可选）

    Returns:
    {
        "success": true,
        "data": [
            {"agentId": "agent1", "status": "idle", "successRate": 0.95},
            ...
        ]
    }
    """
    service = AgentCapabilityService()
    status = request.args.get('status')

    try:
        agents = service.query_by_capability(capability, status)

        return jsonify({
            'success': True,
            'data': [a.to_dict() for a in agents]
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        service.close()


# ============================================================
# Agent 选择 API
# ============================================================

@bp.route('/<int:employee_id>/select-agent', methods=['POST'])
@auth_required
def select_agent_for_workflow(employee_id):
    """
    为工作流节点选择 Agent

    Body:
    {
        "requiredCapability": "数据分析",
        "requiredSkill": "data-analyzer",
        "preferBound": true
    }

    Returns:
    {
        "success": true,
        "data": {
            "agentId": "agent1",
            "reason": "能力匹配度高(90分)，成功率95%"
        }
    }
    """
    service = EmployeeAgentService()
    data = request.get_json() or {}

    required_capability = data.get('requiredCapability')
    required_skill = data.get('requiredSkill')
    prefer_bound = data.get('preferBound', True)

    if not required_capability:
        return jsonify({'success': False, 'error': 'requiredCapability 不能为空'}), 400

    try:
        agent_id = service.select_agent_for_workflow(
            employee_id,
            required_capability,
            required_skill,
            prefer_bound
        )

        if agent_id:
            # 获取选择原因
            capability = service.selection_service.capability_service.get_capability(agent_id)

            reason = ""
            if capability:
                expertise = capability.expertise_level.get(required_capability, 50)
                reason = f"能力匹配度高({expertise}分)，成功率{capability.success_rate:.0%}"

            return jsonify({
                'success': True,
                'data': {
                    'agentId': agent_id,
                    'reason': reason
                }
            })
        else:
            return jsonify({
                'success': True,
                'data': {
                    'agentId': None,
                    'reason': '没有找到合适的 Agent'
                }
            })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        service.close()


@bp.route('/select-best-agent', methods=['POST'])
@auth_required
def select_best_agent():
    """
    自动选择最优 Agent（全局）

    Body:
    {
        "requiredCapability": "数据分析",
        "requiredSkill": "data-analyzer"
    }
    """
    service = AgentSelectionService()
    data = request.get_json() or {}

    required_capability = data.get('requiredCapability')
    required_skill = data.get('requiredSkill')

    if not required_capability:
        return jsonify({'success': False, 'error': 'requiredCapability 不能为空'}), 400

    try:
        agent_id = service.select_best_agent(required_capability, required_skill)

        if agent_id:
            capability = service.capability_service.get_capability(agent_id)

            return jsonify({
                'success': True,
                'data': {
                    'agentId': agent_id,
                    'capability': capability.to_dict() if capability else None
                }
            })
        else:
            return jsonify({
                'success': True,
                'data': {
                    'agentId': None,
                    'reason': '没有找到合适的空闲 Agent'
                }
            })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        service.capability_service.close()


# ============================================================
# 工作流发起记录 API
# ============================================================

@bp.route('/<int:employee_id>/workflow-history', methods=['GET'])
@auth_required
def get_workflow_history(employee_id):
    """
    获取员工的工作流历史

    Query params:
    - limit: 返回数量限制（默认 20）

    Returns:
    {
        "success": true,
        "data": [
            {
                "id": 1,
                "workflowName": "公众号文章发布",
                "status": "completed",
                "agentId": "agent1",
                "createdAt": "2026-04-10T..."
            },
            ...
        ]
    }
    """
    service = WorkflowInitiationService()
    limit = request.args.get('limit', 20, type=int)

    try:
        history = service.get_employee_workflow_history(employee_id, limit)

        return jsonify({
            'success': True,
            'data': history
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        service.close()


# ============================================================
# 注册到 Flask App
# ============================================================

def register_employee_agent_routes(app):
    """注册路由到 Flask App"""
    app.register_blueprint(bp)
    print("[EmployeeAgentAPI] 路由已注册")


if __name__ == '__main__':
    # 测试初始化
    init_employee_agent_service()
    print("[EmployeeAgentAPI] 初始化完成")