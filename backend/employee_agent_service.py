"""
员工 Agent 服务层

实现员工-Agent 关系管理：
- 绑定关系管理（agent_ids）
- 能力配置管理（agent_config）
- Agent 自动选择机制
- 工作流发起记录

设计理念：
- Agent 是员工的能力延伸，不是下属
- 员工是受益者，不是管理者
- 全自动 Agent 选择，无需人工参与
"""

import json
from datetime import datetime
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from database import (
    SessionLocal, Employee, AgentProfile, Base,
    engine, JSON
)


# ============================================================
# 数据类型定义
# ============================================================

@dataclass
class AgentConfig:
    """Agent 能力配置"""
    autonomy: str = "high"  # high / medium / low
    report_style: Dict = field(default_factory=lambda: {
        "detail_level": "summary",
        "timing": "on_complete"
    })
    learning: Dict = field(default_factory=lambda: {
        "remember_feedback": True,
        "auto_improve": True
    })

    def to_dict(self) -> dict:
        return {
            "autonomy": self.autonomy,
            "report_style": self.report_style,
            "learning": self.learning
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'AgentConfig':
        if not data:
            return cls()
        return cls(
            autonomy=data.get("autonomy", "high"),
            report_style=data.get("report_style", {
                "detail_level": "summary",
                "timing": "on_complete"
            }),
            learning=data.get("learning", {
                "remember_feedback": True,
                "auto_improve": True
            })
        )


@dataclass
class AgentCapability:
    """Agent 能力信息"""
    agent_id: str
    name: str
    capabilities: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    expertise_level: Dict[str, int] = field(default_factory=dict)
    status: str = "idle"
    current_tasks: int = 0
    success_rate: float = 0.95

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "capabilities": self.capabilities,
            "skills": self.skills,
            "expertise_level": self.expertise_level,
            "status": self.status,
            "current_tasks": self.current_tasks,
            "success_rate": self.success_rate
        }


# ============================================================
# Agent 能力扩展
# ============================================================

def extend_agent_profile_table():
    """
    扩展 AgentProfile 表，添加能力字段

    新增字段：
    - capabilities: JSONB 能力标签
    - skills: JSONB 可执行 Skills
    - expertise_level: JSONB 专业度评分
    - status: String 当前状态
    - current_tasks: Integer 当前任务数
    - success_rate: Float 成功率
    """
    # 检查列是否已存在
    session = SessionLocal()
    try:
        from sqlalchemy import text

        # 检查 capabilities 列
        result = session.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'agent_profiles'
            AND column_name = 'capabilities'
        """))

        if result.fetchone() is None:
            # 添加能力相关列
            session.execute(text("""
                ALTER TABLE agent_profiles
                ADD COLUMN capabilities JSONB,
                ADD COLUMN skills JSONB,
                ADD COLUMN expertise_level JSONB,
                ADD COLUMN status VARCHAR(20) DEFAULT 'idle',
                ADD COLUMN current_tasks INTEGER DEFAULT 0,
                ADD COLUMN success_rate FLOAT DEFAULT 0.95
            """))
            session.commit()
            print("[EmployeeAgentService] AgentProfile 能力字段已添加")
        else:
            print("[EmployeeAgentService] AgentProfile 能力字段已存在")

    except Exception as e:
        session.rollback()
        print(f"[EmployeeAgentService] 扩展 AgentProfile 失败: {e}")
        raise
    finally:
        session.close()


# ============================================================
# Agent 能力注册服务
# ============================================================

class AgentCapabilityService:
    """
    Agent 能力注册和管理服务

    职责：
    - 注册 Agent 能力
    - 查询 Agent 能力池
    - 更新 Agent 状态和统计
    """

    def __init__(self, session: Session = None):
        self.session = session or SessionLocal()

    def register_capability(
        self,
        agent_id: str,
        capabilities: List[str],
        skills: List[str],
        expertise_level: Dict[str, int] = None
    ) -> bool:
        """
        注册 Agent 能力

        Args:
            agent_id: Agent ID
            capabilities: 能力标签列表，如 ["数据分析", "写作", "搜索"]
            skills: 可执行 Skills 列表，如 ["data-analyzer", "writer"]
            expertise_level: 专业度评分，如 {"数据分析": 90, "写作": 80}

        Returns:
            是否成功
        """
        # 获取或创建 AgentProfile
        profile = self.session.get(AgentProfile, agent_id)

        if profile is None:
            # 创建新的 profile
            profile = AgentProfile(
                agent_id=agent_id,
                capabilities=capabilities,
                skills=skills,
                expertise_level=expertise_level or {},
                status='idle',
                current_tasks=0,
                success_rate=0.95
            )
            self.session.add(profile)
        else:
            # 更新现有 profile
            profile.capabilities = capabilities
            profile.skills = skills
            profile.expertise_level = expertise_level or {}

        self.session.commit()
        return True

    def get_capability(self, agent_id: str) -> Optional[AgentCapability]:
        """
        获取 Agent 能力信息

        Args:
            agent_id: Agent ID

        Returns:
            AgentCapability 对象或 None
        """
        profile = self.session.get(AgentProfile, agent_id)

        if profile is None:
            return None

        return AgentCapability(
            agent_id=profile.agent_id,
            name="",  # 从 Gateway 获取名称
            capabilities=profile.capabilities or [],
            skills=profile.skills or [],
            expertise_level=profile.expertise_level or {},
            status=profile.status or 'idle',
            current_tasks=profile.current_tasks or 0,
            success_rate=profile.success_rate or 0.95
        )

    def query_by_capability(
        self,
        capability: str,
        status: str = None
    ) -> List[AgentCapability]:
        """
        查询具有指定能力的 Agent

        Args:
            capability: 能力标签
            status: 状态过滤（可选）

        Returns:
            Agent 能力列表
        """
        from sqlalchemy import text

        # PostgreSQL JSONB 包含查询
        query = text("""
            SELECT agent_id, capabilities, skills, expertise_level,
                   status, current_tasks, success_rate
            FROM agent_profiles
            WHERE capabilities @> :capability
        """)

        params = {"capability": json.dumps([capability])}

        if status:
            query = text("""
                SELECT agent_id, capabilities, skills, expertise_level,
                       status, current_tasks, success_rate
                FROM agent_profiles
                WHERE capabilities @> :capability AND status = :status
            """)
            params["status"] = status

        result = self.session.execute(query, params)
        rows = result.fetchall()

        return [
            AgentCapability(
                agent_id=row[0],
                name="",
                capabilities=row[1] or [],
                skills=row[2] or [],
                expertise_level=row[3] or {},
                status=row[4] or 'idle',
                current_tasks=row[5] or 0,
                success_rate=row[6] or 0.95
            )
            for row in rows
        ]

    def update_status(
        self,
        agent_id: str,
        status: str,
        current_tasks: int = None
    ) -> bool:
        """
        更新 Agent 状态

        Args:
            agent_id: Agent ID
            status: 新状态（idle / busy）
            current_tasks: 当前任务数（可选）

        Returns:
            是否成功
        """
        profile = self.session.get(AgentProfile, agent_id)

        if profile is None:
            return False

        profile.status = status
        if current_tasks is not None:
            profile.current_tasks = current_tasks

        self.session.commit()
        return True

    def update_success_rate(
        self,
        agent_id: str,
        success: bool
    ) -> bool:
        """
        更新 Agent 成功率

        Args:
            agent_id: Agent ID
            success: 本次执行是否成功

        Returns:
            是否成功
        """
        profile = self.session.get(AgentProfile, agent_id)

        if profile is None:
            return False

        # 简单的移动平均更新
        # 新成功率 = 旧成功率 * 0.95 + 本次结果 * 0.05
        old_rate = profile.success_rate or 0.95
        new_rate = old_rate * 0.95 + (1.0 if success else 0.0) * 0.05

        profile.success_rate = new_rate
        self.session.commit()
        return True

    def get_idle_agents(self) -> List[AgentCapability]:
        """
        获取所有空闲的 Agent

        Returns:
            空闲 Agent 列表
        """
        from sqlalchemy import text

        query = text("""
            SELECT agent_id, capabilities, skills, expertise_level,
                   status, current_tasks, success_rate
            FROM agent_profiles
            WHERE status = 'idle'
        """)

        result = self.session.execute(query)
        rows = result.fetchall()

        return [
            AgentCapability(
                agent_id=row[0],
                name="",
                capabilities=row[1] or [],
                skills=row[2] or [],
                expertise_level=row[3] or {},
                status=row[4] or 'idle',
                current_tasks=row[5] or 0,
                success_rate=row[6] or 0.95
            )
            for row in rows
        ]

    def close(self):
        """关闭 Session"""
        if self.session:
            self.session.close()


# ============================================================
# Agent 自动选择服务
# ============================================================

class AgentSelectionService:
    """
    Agent 自动选择服务

    核心原则：全自动选择，无需人工参与

    选择策略：
    - 能力匹配度优先
    - 成功率次优先
    - 负载均衡考虑
    """

    def __init__(
        self,
        capability_service: AgentCapabilityService = None,
        session: Session = None
    ):
        self.capability_service = capability_service or AgentCapabilityService(session)

    def select_best_agent(
        self,
        required_capability: str,
        required_skill: str = None
    ) -> Optional[str]:
        """
        自动选择最优 Agent

        Args:
            required_capability: 需要的能力标签
            required_skill: 需要的 Skill（可选）

        Returns:
            最优 Agent ID，如果没有合适的返回 None
        """
        # 1. 查询具有该能力的空闲 Agent
        agents = self.capability_service.query_by_capability(
            required_capability,
            status='idle'
        )

        if not agents:
            # 没有空闲 Agent，尝试查询所有具有该能力的 Agent
            agents = self.capability_service.query_by_capability(required_capability)

            if not agents:
                return None

            # 如果有繁忙的 Agent，等待
            # 实际实现中可以加入等待队列
            return None

        # 2. 如果指定了 Skill，过滤能执行该 Skill 的 Agent
        if required_skill:
            agents = [a for a in agents if required_skill in a.skills]

            if not agents:
                return None

        # 3. 计算综合评分并排序
        scored_agents = []

        for agent in agents:
            score = self._calculate_score(agent, required_capability)
            scored_agents.append((agent.agent_id, score))

        # 4. 选择最高评分
        if scored_agents:
            best = max(scored_agents, key=lambda x: x[1])
            return best[0]

        return None

    def _calculate_score(
        self,
        agent: AgentCapability,
        capability: str
    ) -> float:
        """
        计算综合评分

        评分公式：
        score = 专业度 * 0.5 + 成功率 * 100 * 0.3 + 负载得分 * 0.2

        Args:
            agent: Agent 能力信息
            capability: 需要的能力

        Returns:
            综合评分
        """
        # 专业度（0-100）
        expertise = agent.expertise_level.get(capability, 50)

        # 成功率（0-100）
        success_score = agent.success_rate * 100

        # 负载得分（空闲得高分）
        # 任务数越多，得分越低
        load_score = max(0, 100 - agent.current_tasks * 20)

        # 综合评分
        score = (
            expertise * 0.5 +
            success_score * 0.3 +
            load_score * 0.2
        )

        return score

    def select_alternative_agent(
        self,
        required_capability: str,
        exclude_agent_id: str
    ) -> Optional[str]:
        """
        选择替代 Agent（当首选 Agent 繁忙时）

        Args:
            required_capability: 需要的能力
            exclude_agent_id: 要排除的 Agent ID

        Returns:
            替代 Agent ID
        """
        agents = self.capability_service.query_by_capability(
            required_capability,
            status='idle'
        )

        # 排除指定的 Agent
        agents = [a for a in agents if a.agent_id != exclude_agent_id]

        if not agents:
            return None

        # 选择评分最高的
        scored = [(a.agent_id, self._calculate_score(a, required_capability)) for a in agents]
        return max(scored, key=lambda x: x[1])[0]


# ============================================================
# 员工 Agent 服务
# ============================================================

class EmployeeAgentService:
    """
    员工 Agent 服务

    职责：
    - 员工-Agent 绑定关系管理
    - agent_config 配置管理
    - 工作流发起（关联员工）
    - Agent 选择（基于绑定 + 能力）
    """

    def __init__(self, session: Session = None):
        self.session = session or SessionLocal()
        self.selection_service = AgentSelectionService(session=session)

    # ==================== 绑定关系管理 ====================

    def bind_agent(
        self,
        employee_id: int,
        agent_id: str
    ) -> bool:
        """
        绑定 Agent 到员工

        Args:
            employee_id: 员工 ID
            agent_id: Agent ID

        Returns:
            是否成功
        """
        employee = self.session.get(Employee, employee_id)

        if employee is None:
            return False

        # 解析现有绑定
        agent_ids = self._parse_agent_ids(employee.agent_ids)

        # 添加新绑定
        if agent_id not in agent_ids:
            agent_ids.append(agent_id)
            employee.agent_ids = json.dumps(agent_ids)

        self.session.commit()
        return True

    def unbind_agent(
        self,
        employee_id: int,
        agent_id: str
    ) -> bool:
        """
        解绑 Agent

        Args:
            employee_id: 员工 ID
            agent_id: Agent ID

        Returns:
            是否成功
        """
        employee = self.session.get(Employee, employee_id)

        if employee is None:
            return False

        # 解析现有绑定
        agent_ids = self._parse_agent_ids(employee.agent_ids)

        # 移除绑定
        if agent_id in agent_ids:
            agent_ids.remove(agent_id)
            employee.agent_ids = json.dumps(agent_ids)

        self.session.commit()
        return True

    def get_bound_agents(self, employee_id: int) -> List[str]:
        """
        获取员工绑定的 Agent ID 列表

        Args:
            employee_id: 员工 ID

        Returns:
            Agent ID 列表
        """
        employee = self.session.get(Employee, employee_id)

        if employee is None:
            return []

        return self._parse_agent_ids(employee.agent_ids)

    def get_employee_by_agent(self, agent_id: str) -> List[Employee]:
        """
        获取绑定指定 Agent 的所有员工

        Args:
            agent_id: Agent ID

        Returns:
            员工列表
        """
        from sqlalchemy import text

        # PostgreSQL JSONB 数组包含查询
        query = text("""
            SELECT id, name, email, phone, avatar, department_id,
                   manager_id, agent_ids, agent_config, user_id, status
            FROM employees
            WHERE agent_ids::jsonb @> :agent_id
        """)

        result = self.session.execute(query, {"agent_id": json.dumps([agent_id])})
        rows = result.fetchall()

        return [
            Employee(
                id=row[0],
                name=row[1],
                email=row[2],
                phone=row[3],
                avatar=row[4],
                department_id=row[5],
                manager_id=row[6],
                agent_ids=row[7],
                agent_config=row[8],
                user_id=row[9],
                status=row[10]
            )
            for row in rows
        ]

    # ==================== 配置管理 ====================

    def get_agent_config(self, employee_id: int) -> AgentConfig:
        """
        获取员工的 Agent 配置

        Args:
            employee_id: 员工 ID

        Returns:
            AgentConfig 对象
        """
        employee = self.session.get(Employee, employee_id)

        if employee is None:
            return AgentConfig()

        return AgentConfig.from_dict(employee.agent_config or {})

    def update_agent_config(
        self,
        employee_id: int,
        config: AgentConfig
    ) -> bool:
        """
        更新员工的 Agent 配置

        Args:
            employee_id: 员工 ID
            config: Agent 配置

        Returns:
            是否成功
        """
        employee = self.session.get(Employee, employee_id)

        if employee is None:
            return False

        employee.agent_config = config.to_dict()
        self.session.commit()
        return True

    def set_autonomy(
        self,
        employee_id: int,
        autonomy: str
    ) -> bool:
        """
        设置自主性级别

        Args:
            employee_id: 员工 ID
            autonomy: 级别（high / medium / low）

        Returns:
            是否成功
        """
        config = self.get_agent_config(employee_id)
        config.autonomy = autonomy
        return self.update_agent_config(employee_id, config)

    def set_report_style(
        self,
        employee_id: int,
        detail_level: str = None,
        timing: str = None
    ) -> bool:
        """
        设置汇报风格

        Args:
            employee_id: 员工 ID
            detail_level: 详细程度（summary / detail）
            timing: 汇报时机（on_complete / realtime）

        Returns:
            是否成功
        """
        config = self.get_agent_config(employee_id)

        if detail_level:
            config.report_style["detail_level"] = detail_level
        if timing:
            config.report_style["timing"] = timing

        return self.update_agent_config(employee_id, config)

    # ==================== Agent 选择 ====================

    def select_agent_for_workflow(
        self,
        employee_id: int,
        required_capability: str,
        required_skill: str = None,
        prefer_bound: bool = True
    ) -> Optional[str]:
        """
        为工作流节点选择 Agent

        选择策略：
        1. 如果 prefer_bound=True，优先从员工绑定的 Agent 中选择
        2. 如果绑定 Agent 不满足要求，从 Agent 池中选择
        3. 全自动选择，无需人工参与

        Args:
            employee_id: 员工 ID
            required_capability: 需要的能力
            required_skill: 需要的 Skill（可选）
            prefer_bound: 是否优先选择绑定的 Agent

        Returns:
            Agent ID 或 None
        """
        if prefer_bound:
            # 1. 从绑定的 Agent 中选择
            bound_agents = self.get_bound_agents(employee_id)

            for agent_id in bound_agents:
                capability = self.selection_service.capability_service.get_capability(agent_id)

                if capability:
                    # 检查能力匹配
                    if required_capability in capability.capabilities:
                        # 检查状态
                        if capability.status == 'idle':
                            # 检查 Skill
                            if required_skill and required_skill not in capability.skills:
                                continue

                            return agent_id

        # 2. 从 Agent 池中选择
        return self.selection_service.select_best_agent(
            required_capability,
            required_skill
        )

    # ==================== 辅助方法 ====================

    def _parse_agent_ids(self, agent_ids_str: str) -> List[str]:
        """解析 agent_ids JSON"""
        if not agent_ids_str:
            return []

        try:
            return json.loads(agent_ids_str)
        except:
            return []

    def close(self):
        """关闭 Session"""
        if self.session:
            self.session.close()
            self.selection_service.capability_service.close()


# ============================================================
# 工作流发起记录
# ============================================================

class WorkflowInitiationService:
    """
    工作流发起记录服务

    职责：
    - 记录员工发起的工作流
    - 关联 Agent 执行记录
    - 提供查询接口
    """

    def __init__(self, session: Session = None):
        self.session = session or SessionLocal()

    def record_initiation(
        self,
        employee_id: int,
        workflow_name: str,
        execution_id: str,
        agent_id: str,
        user_input: dict
    ) -> bool:
        """
        记录工作流发起

        Args:
            employee_id: 员工 ID
            workflow_name: 工作流名称
            execution_id: 执行 ID
            agent_id: 执行 Agent ID
            user_input: 用户输入

        Returns:
            是否成功
        """
        # 注：实际存储可以：
        # 1. 扩展 Task 表
        # 2. 创建新的 workflow_initiations 表
        # 3. 写入执行记录文件

        # 这里暂时使用扩展 Task 表的方式
        from database import Task

        task = Task(
            agent_id=agent_id,
            title=f"Workflow: {workflow_name}",
            task_type="workflow",
            status="running",
            user_id=str(employee_id),
            session_id=execution_id,
            details=json.dumps({
                "workflow_name": workflow_name,
                "user_input": user_input,
                "initiated_by_employee": employee_id
            })
        )

        self.session.add(task)
        self.session.commit()
        return True

    def get_employee_workflow_history(
        self,
        employee_id: int,
        limit: int = 20
    ) -> List[dict]:
        """
        获取员工的工作流历史

        Args:
            employee_id: 员工 ID
            limit: 返回数量限制

        Returns:
            工作流历史列表
        """
        from sqlalchemy import text

        query = text("""
            SELECT id, agent_id, title, status, created_at, completed_at, details
            FROM tasks
            WHERE user_id = :employee_id AND task_type = 'workflow'
            ORDER BY created_at DESC
            LIMIT :limit
        """)

        result = self.session.execute(query, {
            "employee_id": str(employee_id),
            "limit": limit
        })

        rows = result.fetchall()

        return [
            {
                "id": row[0],
                "agent_id": row[1],
                "title": row[2],
                "status": row[3],
                "created_at": row[4],
                "completed_at": row[5],
                "details": json.loads(row[6]) if row[6] else {}
            }
            for row in rows
        ]

    def close(self):
        """关闭 Session"""
        if self.session:
            self.session.close()


# ============================================================
# 初始化
# ============================================================

def init_employee_agent_service():
    """初始化员工 Agent 服务"""
    # 扩展 AgentProfile 表
    extend_agent_profile_table()
    print("[EmployeeAgentService] 初始化完成")


if __name__ == '__main__':
    init_employee_agent_service()