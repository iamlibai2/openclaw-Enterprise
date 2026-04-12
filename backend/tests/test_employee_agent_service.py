"""
EmployeeAgentService 测试

测试员工-Agent 功能：
- 绑定关系管理
- Agent 配置管理
- Agent 能力注册
- Agent 选择机制
"""

import pytest
import json
from datetime import datetime

from employee_agent_service import (
    EmployeeAgentService,
    AgentCapabilityService,
    AgentSelectionService,
    WorkflowInitiationService,
    AgentConfig,
    AgentCapability
)

from database import (
    SessionLocal, Employee, AgentProfile, Task,
    Base, engine
)


# ============================================================
# 测试 fixtures
# ============================================================

@pytest.fixture
def session():
    """创建测试 Session"""
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def employee_agent_service(session):
    """创建 EmployeeAgentService"""
    service = EmployeeAgentService(session=session)
    yield service
    # 不关闭 session，由 session fixture 关闭


@pytest.fixture
def capability_service(session):
    """创建 AgentCapabilityService"""
    service = AgentCapabilityService(session=session)
    yield service


@pytest.fixture
def test_employee(session):
    """创建测试员工"""
    employee = Employee(
        name="测试员工",
        email="test@example.com",
        status="active",
        agent_ids=json.dumps([]),
        agent_config={
            "autonomy": "high",
            "report_style": {"detail_level": "summary", "timing": "on_complete"},
            "learning": {"remember_feedback": True, "auto_improve": True}
        }
    )
    session.add(employee)
    session.commit()
    session.refresh(employee)
    yield employee
    # 清理
    session.delete(employee)
    session.commit()


@pytest.fixture
def test_agent_profile(session):
    """创建测试 Agent Profile"""
    profile = AgentProfile(
        agent_id="test_agent",
        capabilities=["数据分析", "写作"],
        skills=["data-analyzer", "writer"],
        expertise_level={"数据分析": 90, "写作": 80},
        status="idle",
        current_tasks=0,
        success_rate=0.95
    )
    session.add(profile)
    session.commit()
    session.refresh(profile)
    yield profile
    # 清理
    session.delete(profile)
    session.commit()


# ============================================================
# AgentConfig 测试
# ============================================================

class TestAgentConfig:
    """AgentConfig 数据类测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = AgentConfig()
        assert config.autonomy == "high"
        assert config.report_style["detail_level"] == "summary"
        assert config.learning["remember_feedback"] == True

    def test_to_dict(self):
        """测试转换为字典"""
        config = AgentConfig(autonomy="medium")
        data = config.to_dict()
        assert data["autonomy"] == "medium"
        assert "report_style" in data
        assert "learning" in data

    def test_from_dict(self):
        """测试从字典创建"""
        data = {
            "autonomy": "low",
            "report_style": {"detail_level": "detail", "timing": "realtime"},
            "learning": {"remember_feedback": False, "auto_improve": False}
        }
        config = AgentConfig.from_dict(data)
        assert config.autonomy == "low"
        assert config.report_style["detail_level"] == "detail"
        assert config.learning["remember_feedback"] == False

    def test_from_empty_dict(self):
        """测试从空字典创建"""
        config = AgentConfig.from_dict({})
        assert config.autonomy == "high"  # 默认值


# ============================================================
# AgentCapability 测试
# ============================================================

class TestAgentCapability:
    """AgentCapability 数据类测试"""

    def test_default_capability(self):
        """测试默认能力"""
        cap = AgentCapability(agent_id="test", name="Test Agent")
        assert cap.capabilities == []
        assert cap.status == "idle"
        assert cap.success_rate == 0.95

    def test_to_dict(self):
        """测试转换为字典"""
        cap = AgentCapability(
            agent_id="test",
            name="Test",
            capabilities=["数据分析"],
            skills=["data-analyzer"],
            expertise_level={"数据分析": 90}
        )
        data = cap.to_dict()
        assert data["agent_id"] == "test"
        assert data["capabilities"] == ["数据分析"]
        assert data["expertise_level"]["数据分析"] == 90


# ============================================================
# AgentCapabilityService 测试
# ============================================================

class TestAgentCapabilityService:
    """Agent 能力注册服务测试"""

    def test_register_capability(self, capability_service, session):
        """测试注册能力"""
        success = capability_service.register_capability(
            "new_agent",
            ["搜索", "写作"],
            ["baidu-search", "writer"],
            {"搜索": 85, "写作": 90}
        )
        assert success == True

        # 验证数据
        profile = session.get(AgentProfile, "new_agent")
        assert profile is not None
        assert profile.capabilities == ["搜索", "写作"]
        assert profile.skills == ["baidu-search", "writer"]

        # 清理
        session.delete(profile)
        session.commit()

    def test_get_capability(self, capability_service, test_agent_profile):
        """测试获取能力"""
        cap = capability_service.get_capability("test_agent")
        assert cap is not None
        assert cap.agent_id == "test_agent"
        assert "数据分析" in cap.capabilities
        assert cap.expertise_level["数据分析"] == 90

    def test_get_capability_not_found(self, capability_service):
        """测试获取不存在的能力"""
        cap = capability_service.get_capability("nonexistent_agent")
        assert cap is None

    def test_update_status(self, capability_service, test_agent_profile, session):
        """测试更新状态"""
        success = capability_service.update_status("test_agent", "busy", 2)
        assert success == True

        # 验证
        profile = session.get(AgentProfile, "test_agent")
        assert profile.status == "busy"
        assert profile.current_tasks == 2

        # 恢复状态
        capability_service.update_status("test_agent", "idle", 0)

    def test_update_success_rate(self, capability_service, test_agent_profile, session):
        """测试更新成功率"""
        old_rate = test_agent_profile.success_rate

        # 成功执行
        capability_service.update_success_rate("test_agent", True)

        profile = session.get(AgentProfile, "test_agent")
        # 成功率应该增加（移动平均）
        assert profile.success_rate >= old_rate


# ============================================================
# AgentSelectionService 测试
# ============================================================

class TestAgentSelectionService:
    """Agent 自动选择服务测试"""

    def test_select_best_agent(self, capability_service, test_agent_profile):
        """测试选择最优 Agent"""
        selection_service = AgentSelectionService(capability_service=capability_service)

        agent_id = selection_service.select_best_agent("数据分析")
        assert agent_id == "test_agent"

    def test_select_with_skill_filter(self, capability_service, test_agent_profile):
        """测试 Skill 过滤"""
        selection_service = AgentSelectionService(capability_service=capability_service)

        # 需要 data-analyzer skill
        agent_id = selection_service.select_best_agent("数据分析", "data-analyzer")
        assert agent_id == "test_agent"

        # 需要 nonexistent skill
        agent_id = selection_service.select_best_agent("数据分析", "nonexistent_skill")
        assert agent_id is None

    def test_select_no_capability_match(self, capability_service, test_agent_profile):
        """测试能力不匹配"""
        selection_service = AgentSelectionService(capability_service=capability_service)

        agent_id = selection_service.select_best_agent("不存在的能力")
        assert agent_id is None

    def test_calculate_score(self, capability_service, test_agent_profile):
        """测试评分计算"""
        selection_service = AgentSelectionService(capability_service=capability_service)

        cap = capability_service.get_capability("test_agent")
        score = selection_service._calculate_score(cap, "数据分析")

        # 专业度 90 * 0.5 + 成功率 95 * 0.3 + 负载 100 * 0.2
        # = 45 + 28.5 + 20 = 93.5
        assert score >= 90
        assert score <= 100


# ============================================================
# EmployeeAgentService 测试
# ============================================================

class TestEmployeeAgentService:
    """员工 Agent 服务测试"""

    def test_bind_agent(self, employee_agent_service, test_employee, session):
        """测试绑定 Agent"""
        success = employee_agent_service.bind_agent(test_employee.id, "agent1")
        assert success == True

        # 验证绑定
        employee = session.get(Employee, test_employee.id)
        agent_ids = json.loads(employee.agent_ids)
        assert "agent1" in agent_ids

    def test_bind_multiple_agents(self, employee_agent_service, test_employee, session):
        """测试绑定多个 Agent"""
        employee_agent_service.bind_agent(test_employee.id, "agent1")
        employee_agent_service.bind_agent(test_employee.id, "agent2")

        employee = session.get(Employee, test_employee.id)
        agent_ids = json.loads(employee.agent_ids)
        assert len(agent_ids) == 2
        assert "agent1" in agent_ids
        assert "agent2" in agent_ids

    def test_unbind_agent(self, employee_agent_service, test_employee, session):
        """测试解绑 Agent"""
        # 先绑定
        employee_agent_service.bind_agent(test_employee.id, "agent1")
        employee_agent_service.bind_agent(test_employee.id, "agent2")

        # 解绑
        employee_agent_service.unbind_agent(test_employee.id, "agent1")

        employee = session.get(Employee, test_employee.id)
        agent_ids = json.loads(employee.agent_ids)
        assert "agent1" not in agent_ids
        assert "agent2" in agent_ids

    def test_get_bound_agents(self, employee_agent_service, test_employee, session):
        """测试获取绑定 Agent"""
        employee_agent_service.bind_agent(test_employee.id, "agent1")
        employee_agent_service.bind_agent(test_employee.id, "agent2")

        agent_ids = employee_agent_service.get_bound_agents(test_employee.id)
        assert len(agent_ids) == 2
        assert "agent1" in agent_ids

    def test_get_agent_config(self, employee_agent_service, test_employee):
        """测试获取 Agent 配置"""
        config = employee_agent_service.get_agent_config(test_employee.id)
        assert config.autonomy == "high"
        assert config.report_style["detail_level"] == "summary"

    def test_update_agent_config(self, employee_agent_service, test_employee, session):
        """测试更新 Agent 配置"""
        new_config = AgentConfig(
            autonomy="medium",
            report_style={"detail_level": "detail", "timing": "realtime"}
        )

        success = employee_agent_service.update_agent_config(test_employee.id, new_config)
        assert success == True

        employee = session.get(Employee, test_employee.id)
        assert employee.agent_config["autonomy"] == "medium"
        assert employee.agent_config["report_style"]["detail_level"] == "detail"

    def test_set_autonomy(self, employee_agent_service, test_employee, session):
        """测试设置自主性"""
        success = employee_agent_service.set_autonomy(test_employee.id, "low")
        assert success == True

        employee = session.get(Employee, test_employee.id)
        assert employee.agent_config["autonomy"] == "low"

    def test_select_agent_for_workflow_prefer_bound(
        self,
        employee_agent_service,
        capability_service,
        test_employee,
        test_agent_profile,
        session
    ):
        """测试工作流 Agent 选择（优先绑定）"""
        # 绑定 test_agent
        employee_agent_service.bind_agent(test_employee.id, "test_agent")

        # 选择数据分析 Agent
        agent_id = employee_agent_service.select_agent_for_workflow(
            test_employee.id,
            "数据分析",
            prefer_bound=True
        )

        # 应该选择绑定的 test_agent
        assert agent_id == "test_agent"

    def test_select_agent_for_workflow_from_pool(
        self,
        employee_agent_service,
        capability_service,
        test_employee,
        test_agent_profile
    ):
        """测试工作流 Agent 选择（从池中）"""
        # 不绑定任何 Agent

        # 选择数据分析 Agent
        agent_id = employee_agent_service.select_agent_for_workflow(
            test_employee.id,
            "数据分析",
            prefer_bound=False
        )

        # 应该从池中选择 test_agent
        assert agent_id == "test_agent"


# ============================================================
# 运行测试
# ============================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v'])