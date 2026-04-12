"""
Tests for workflow file I/O operations.
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from workflow import (
    Workflow,
    WorkflowNode,
    WorkflowEdge,
    WorkflowIO,
    ExecutionIO,
    OutputIO,
    Execution,
    NodeExecution
)


class TestWorkflowIO:
    """测试工作流文件读写"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        dirpath = tempfile.mkdtemp()
        yield dirpath
        shutil.rmtree(dirpath)

    @pytest.fixture
    def workflow_io(self, temp_dir):
        """创建 WorkflowIO 实例"""
        return WorkflowIO(base_path=temp_dir)

    def test_create_workflow(self, workflow_io, temp_dir):
        """测试创建工作流文件"""
        workflow = Workflow(
            id="wf_001",
            name="测试工作流",
            nodes=[
                WorkflowNode(id="node_1", name="搜索", type="skill", skill="baidu-search", input={"query": "${user_input.topic}"}),
                WorkflowNode(id="node_2", name="生成", type="skill", skill="article-generator", input={"material": "${node_1.output.results}"}),
            ],
            edges=[
                WorkflowEdge(from_node="node_1", to_node="node_2")
            ]
        )

        filepath = workflow_io.create("test-workflow", workflow, description="这是一个测试工作流")

        # 验证文件创建成功
        assert Path(filepath).exists()
        assert "test-workflow" in filepath

        # 验证内容
        content = Path(filepath).read_text(encoding='utf-8')
        assert "# 测试工作流" in content
        assert "这是一个测试工作流" in content
        assert "<!-- WORKFLOW_DEFINITION" in content

    def test_read_workflow(self, workflow_io):
        """测试读取工作流"""
        # 先创建
        workflow = Workflow(
            id="wf_002",
            name="读取测试",
            nodes=[
                WorkflowNode(id="n1", name="步骤1", type="skill", skill="test-skill", input={}),
            ],
            edges=[]
        )
        workflow_io.create("read-test", workflow)

        # 再读取
        content, read_workflow = workflow_io.read("read-test")

        assert read_workflow.id == "wf_002"
        assert read_workflow.name == "读取测试"
        assert len(read_workflow.nodes) == 1
        assert read_workflow.nodes[0].id == "n1"
        assert "# 读取测试" in content

    def test_update_json_block(self, workflow_io):
        """测试更新 JSON 块"""
        # 创建初始工作流
        workflow = Workflow(
            id="wf_003",
            name="更新测试",
            nodes=[WorkflowNode(id="n1", name="步骤1", type="skill", skill="test", input={})],
            edges=[]
        )
        workflow_io.create("update-test", workflow, description="原始描述")

        # 更新工作流
        workflow.nodes.append(WorkflowNode(id="n2", name="步骤2", type="skill", skill="test2", input={}))
        workflow.edges.append(WorkflowEdge(from_node="n1", to_node="n2"))

        workflow_io.update_json("update-test", workflow)

        # 验证更新
        _, updated = workflow_io.read("update-test")
        assert len(updated.nodes) == 2
        assert len(updated.edges) == 1

        # 验证 Markdown 部分保留
        content = (workflow_io.base_path / "update-test" / "workflow.md").read_text(encoding='utf-8')
        assert "原始描述" in content

    def test_list_workflows(self, workflow_io):
        """测试列出所有工作流"""
        # 创建多个工作流
        for i in range(3):
            workflow = Workflow(
                id=f"wf_{i}",
                name=f"工作流{i}",
                nodes=[WorkflowNode(id="n1", name="步骤", type="skill", skill="test", input={})],
                edges=[]
            )
            workflow_io.create(f"workflow-{i}", workflow)

        workflows = workflow_io.list_all()

        assert len(workflows) == 3
        names = [w['name'] for w in workflows]
        assert "workflow-0" in names
        assert "workflow-1" in names
        assert "workflow-2" in names

    def test_validate_workflow(self, workflow_io):
        """测试验证工作流"""
        # 有效工作流
        workflow = Workflow(
            id="wf_valid",
            name="有效工作流",
            nodes=[
                WorkflowNode(id="n1", name="步骤1", type="skill", skill="test", input={}),
                WorkflowNode(id="n2", name="步骤2", type="skill", skill="test", input={}),
            ],
            edges=[WorkflowEdge(from_node="n1", to_node="n2")]
        )
        workflow_io.create("valid-wf", workflow)

        is_valid, error = workflow_io.validate("valid-wf")
        assert is_valid
        assert error == ""

        # 无效工作流（边指向不存在的节点）
        workflow_invalid = Workflow(
            id="wf_invalid",
            name="无效工作流",
            nodes=[WorkflowNode(id="n1", name="步骤1", type="skill", skill="test", input={})],
            edges=[WorkflowEdge(from_node="n1", to_node="n_not_exist")]
        )
        workflow_io.create("invalid-wf", workflow_invalid)

        is_valid, error = workflow_io.validate("invalid-wf")
        assert not is_valid
        assert "不存在" in error

    def test_delete_workflow(self, workflow_io):
        """测试删除工作流"""
        workflow = Workflow(
            id="wf_del",
            name="待删除",
            nodes=[],
            edges=[]
        )
        workflow_io.create("to-delete", workflow)

        assert workflow_io.exists("to-delete")

        workflow_io.delete("to-delete")

        assert not workflow_io.exists("to-delete")


class TestExecutionIO:
    """测试执行记录读写"""

    @pytest.fixture
    def temp_dir(self):
        dirpath = tempfile.mkdtemp()
        yield dirpath
        shutil.rmtree(dirpath)

    @pytest.fixture
    def execution_io(self, temp_dir):
        return ExecutionIO(base_path=temp_dir)

    def test_create_execution(self, execution_io, temp_dir):
        """测试创建执行记录"""
        execution = Execution(
            execution_id="exec_001",
            workflow_id="wf_001",
            workflow_name="测试工作流",
            status="completed",
            user_input={"topic": "AI"},
            node_executions=[
                NodeExecution(node_id="n1", status="completed", duration=3.5),
                NodeExecution(node_id="n2", status="completed", duration=10.2),
            ]
        )

        filepath = execution_io.create("test-workflow", execution)

        assert Path(filepath).exists()
        content = Path(filepath).read_text(encoding='utf-8')
        assert "# 执行记录" in content
        assert "AI" in content

    def test_read_execution(self, execution_io):
        """测试读取执行记录"""
        execution = Execution(
            execution_id="exec_002",
            workflow_id="wf_002",
            workflow_name="读取测试",
            status="completed",
            user_input={"query": "test"}
        )
        execution_io.create("read-test", execution)

        # 找到创建的文件
        exec_files = execution_io.list_all("read-test")
        assert len(exec_files) == 1

        _, read_exec = execution_io.read("read-test", exec_files[0]['filename'])
        assert read_exec.execution_id == "exec_002"
        assert read_exec.user_input["query"] == "test"


class TestOutputIO:
    """测试节点输出读写"""

    @pytest.fixture
    def temp_dir(self):
        dirpath = tempfile.mkdtemp()
        yield dirpath
        shutil.rmtree(dirpath)

    @pytest.fixture
    def output_io(self, temp_dir):
        return OutputIO(base_path=temp_dir)

    def test_save_and_load_output(self, output_io):
        """测试保存和读取节点输出"""
        output_data = {
            "results": [
                {"title": "文章1", "content": "内容1"},
                {"title": "文章2", "content": "内容2"},
            ],
            "count": 2
        }

        filepath = output_io.save("test-workflow", "exec_001", "node_1", output_data)

        assert Path(filepath).exists()

        loaded = output_io.load("test-workflow", "exec_001", "node_1")
        assert loaded["count"] == 2
        assert len(loaded["results"]) == 2

    def test_list_outputs(self, output_io):
        """测试列出输出文件"""
        output_io.save("test-wf", "exec_1", "node_1", {"data": 1})
        output_io.save("test-wf", "exec_1", "node_2", {"data": 2})
        output_io.save("test-wf", "exec_1", "node_3", {"data": 3})

        outputs = output_io.list_outputs("test-wf", "exec_1")

        assert len(outputs) == 3
        assert "node_1" in outputs
        assert "node_2" in outputs
        assert "node_3" in outputs


class TestWorkflowModel:
    """测试工作流模型"""

    def test_get_execution_order(self):
        """测试拓扑排序"""
        workflow = Workflow(
            id="wf_001",
            name="测试",
            nodes=[
                WorkflowNode(id="n1", name="1", type="skill", skill="test", input={}),
                WorkflowNode(id="n2", name="2", type="skill", skill="test", input={}),
                WorkflowNode(id="n3", name="3", type="skill", skill="test", input={}),
                WorkflowNode(id="n4", name="4", type="skill", skill="test", input={}),
            ],
            edges=[
                WorkflowEdge(from_node="n1", to_node="n2"),
                WorkflowEdge(from_node="n2", to_node="n3"),
                WorkflowEdge(from_node="n3", to_node="n4"),
            ]
        )

        order = workflow.get_execution_order()

        assert order == ["n1", "n2", "n3", "n4"]

    def test_get_execution_order_parallel(self):
        """测试并行节点的拓扑排序"""
        workflow = Workflow(
            id="wf_002",
            name="并行测试",
            nodes=[
                WorkflowNode(id="n1", name="开始", type="skill", skill="test", input={}),
                WorkflowNode(id="n2", name="分支1", type="skill", skill="test", input={}),
                WorkflowNode(id="n3", name="分支2", type="skill", skill="test", input={}),
                WorkflowNode(id="n4", name="合并", type="skill", skill="test", input={}),
            ],
            edges=[
                WorkflowEdge(from_node="n1", to_node="n2"),
                WorkflowEdge(from_node="n1", to_node="n3"),
                WorkflowEdge(from_node="n2", to_node="n4"),
                WorkflowEdge(from_node="n3", to_node="n4"),
            ]
        )

        order = workflow.get_execution_order()

        # n1 必须在最前，n4 必须在最后
        assert order[0] == "n1"
        assert order[-1] == "n4"
        assert "n2" in order
        assert "n3" in order


if __name__ == "__main__":
    pytest.main([__file__, "-v"])