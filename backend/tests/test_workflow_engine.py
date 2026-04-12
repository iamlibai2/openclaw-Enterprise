"""
Tests for workflow execution engine.
"""

import pytest
import tempfile
import shutil
from datetime import datetime

from workflow import (
    Workflow,
    WorkflowNode,
    WorkflowEdge,
    WorkflowIO,
    ExecutionIO,
    OutputIO,
    WorkflowEngine,
    MockSkillInvoker
)


class TestWorkflowEngine:
    """测试工作流执行引擎"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        dirpath = tempfile.mkdtemp()
        yield dirpath
        shutil.rmtree(dirpath)

    @pytest.fixture
    def workflow_io(self, temp_dir):
        return WorkflowIO(base_path=temp_dir)

    @pytest.fixture
    def execution_io(self, temp_dir):
        return ExecutionIO(base_path=temp_dir)

    @pytest.fixture
    def output_io(self, temp_dir):
        return OutputIO(base_path=temp_dir)

    @pytest.fixture
    def mock_invoker(self):
        """创建模拟 Skill 调用器"""
        return MockSkillInvoker(responses={
            "baidu-search": {
                "results": [
                    {"title": "AI发展趋势", "content": "AI在2026年..."},
                    {"title": "AI应用", "content": "AI应用场景..."},
                ],
                "count": 2
            },
            "article-generator": {
                "article": "这是一篇关于AI的文章..."
            },
            "formatter": {
                "formatted": "<div>排版后的内容</div>"
            }
        })

    @pytest.fixture
    def engine(self, workflow_io, execution_io, output_io, mock_invoker):
        """创建执行引擎"""
        return WorkflowEngine(
            workflow_io=workflow_io,
            execution_io=execution_io,
            output_io=output_io,
            skill_invoker=mock_invoker
        )

    @pytest.mark.asyncio
    async def test_execute_simple_workflow(self, engine, workflow_io):
        """测试执行简单工作流"""
        # 创建工作流
        workflow = Workflow(
            id="wf_001",
            name="简单工作流",
            nodes=[
                WorkflowNode(
                    id="node_1",
                    name="搜索",
                    type="skill",
                    skill="baidu-search",
                    input={"query": "${user_input.topic}"}
                )
            ],
            edges=[]
        )
        workflow_io.create("simple-workflow", workflow)

        # 执行
        result = await engine.execute("simple-workflow", {"topic": "AI"})

        assert result is not None
        assert "results" in result
        assert len(result["results"]) == 2

    @pytest.mark.asyncio
    async def test_execute_chain_workflow(self, engine, workflow_io):
        """测试执行链式工作流"""
        # 创建工作流
        workflow = Workflow(
            id="wf_002",
            name="链式工作流",
            nodes=[
                WorkflowNode(
                    id="node_1",
                    name="搜索",
                    type="skill",
                    skill="baidu-search",
                    input={"query": "${user_input.topic}"}
                ),
                WorkflowNode(
                    id="node_2",
                    name="生成文章",
                    type="skill",
                    skill="article-generator",
                    input={"material": "${node_1.output.results}"}
                ),
                WorkflowNode(
                    id="node_3",
                    name="排版",
                    type="skill",
                    skill="formatter",
                    input={"content": "${node_2.output.article}"}
                )
            ],
            edges=[
                WorkflowEdge(from_node="node_1", to_node="node_2"),
                WorkflowEdge(from_node="node_2", to_node="node_3")
            ]
        )
        workflow_io.create("chain-workflow", workflow)

        # 执行
        result = await engine.execute("chain-workflow", {"topic": "AI发展趋势"})

        assert result is not None
        assert "formatted" in result

        # 验证节点输出正确传递
        assert engine.get_node_output("node_1")["count"] == 2
        assert "article" in engine.get_node_output("node_2")

    @pytest.mark.asyncio
    async def test_variable_binding_user_input(self, engine, workflow_io, mock_invoker):
        """测试变量绑定 - 用户输入"""
        workflow = Workflow(
            id="wf_003",
            name="测试用户输入",
            nodes=[
                WorkflowNode(
                    id="n1",
                    name="测试",
                    type="skill",
                    skill="test-skill",
                    input={"param1": "${user_input.value1}", "param2": "${user_input.value2}"}
                )
            ],
            edges=[]
        )
        workflow_io.create("test-user-input", workflow)

        await engine.execute("test-user-input", {"value1": "hello", "value2": "world"})

        # 验证调用参数
        call = mock_invoker.calls[-1]
        assert call["input"]["param1"] == "hello"
        assert call["input"]["param2"] == "world"

    @pytest.mark.asyncio
    async def test_variable_binding_node_output(self, engine, workflow_io, mock_invoker):
        """测试变量绑定 - 节点输出"""
        workflow = Workflow(
            id="wf_004",
            name="测试节点输出",
            nodes=[
                WorkflowNode(
                    id="n1",
                    name="步骤1",
                    type="skill",
                    skill="skill-1",
                    input={"q": "test"}
                ),
                WorkflowNode(
                    id="n2",
                    name="步骤2",
                    type="skill",
                    skill="skill-2",
                    input={"data": "${n1.output.results}"}
                )
            ],
            edges=[WorkflowEdge(from_node="n1", to_node="n2")]
        )
        workflow_io.create("test-node-output", workflow)

        # 设置第一个 skill 的响应
        mock_invoker.responses["skill-1"] = {"results": ["item1", "item2"]}
        mock_invoker.responses["skill-2"] = {"processed": True}

        await engine.execute("test-node-output", {})

        # 验证第二个节点收到了第一个节点的输出
        calls = [c for c in mock_invoker.calls if c["skill_id"] == "skill-2"]
        assert len(calls) == 1
        assert calls[0]["input"]["data"] == ["item1", "item2"]

    @pytest.mark.asyncio
    async def test_variable_binding_nested_field(self, engine, workflow_io, mock_invoker):
        """测试变量绑定 - 嵌套字段"""
        workflow = Workflow(
            id="wf_005",
            name="测试嵌套字段",
            nodes=[
                WorkflowNode(
                    id="n1",
                    name="步骤1",
                    type="skill",
                    skill="skill-1",
                    input={}
                ),
                WorkflowNode(
                    id="n2",
                    name="步骤2",
                    type="skill",
                    skill="skill-2",
                    input={"title": "${n1.output.data.title}"}
                )
            ],
            edges=[WorkflowEdge(from_node="n1", to_node="n2")]
        )
        workflow_io.create("test-nested", workflow)

        mock_invoker.responses["skill-1"] = {
            "data": {
                "title": "测试标题",
                "content": "测试内容"
            }
        }
        mock_invoker.responses["skill-2"] = {"ok": True}

        await engine.execute("test-nested", {})

        calls = [c for c in mock_invoker.calls if c["skill_id"] == "skill-2"]
        assert calls[0]["input"]["title"] == "测试标题"

    @pytest.mark.asyncio
    async def test_fixed_value_input(self, engine, workflow_io, mock_invoker):
        """测试固定值输入"""
        workflow = Workflow(
            id="wf_006",
            name="测试固定值",
            nodes=[
                WorkflowNode(
                    id="n1",
                    name="测试",
                    type="skill",
                    skill="test-skill",
                    input={
                        "string_val": "固定字符串",
                        "number_val": 123,
                        "bool_val": True,
                        "var_val": "${user_input.value}"
                    }
                )
            ],
            edges=[]
        )
        workflow_io.create("test-fixed", workflow)

        await engine.execute("test-fixed", {"value": "动态值"})

        call = mock_invoker.calls[-1]
        assert call["input"]["string_val"] == "固定字符串"
        assert call["input"]["number_val"] == 123
        assert call["input"]["bool_val"] is True
        assert call["input"]["var_val"] == "动态值"

    @pytest.mark.asyncio
    async def test_execution_record_created(self, engine, workflow_io, execution_io):
        """测试执行记录创建"""
        workflow = Workflow(
            id="wf_007",
            name="测试执行记录",
            nodes=[
                WorkflowNode(
                    id="n1",
                    name="步骤",
                    type="skill",
                    skill="baidu-search",
                    input={"query": "test"}
                )
            ],
            edges=[]
        )
        workflow_io.create("test-record", workflow)

        await engine.execute("test-record", {})

        # 验证执行记录
        records = execution_io.list_all("test-record")
        assert len(records) == 1
        assert records[0]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_node_output_saved(self, engine, workflow_io, output_io):
        """测试节点输出保存"""
        workflow = Workflow(
            id="wf_008",
            name="测试输出保存",
            nodes=[
                WorkflowNode(
                    id="n1",
                    name="搜索",
                    type="skill",
                    skill="baidu-search",
                    input={"query": "test"}
                )
            ],
            edges=[]
        )
        workflow_io.create("test-output", workflow)

        await engine.execute("test-output", {})

        # 验证输出文件
        outputs = output_io.list_outputs("test-output", engine.current_execution.execution_id)
        assert "n1" in outputs

        # 验证输出内容
        saved = output_io.load("test-output", engine.current_execution.execution_id, "n1")
        assert "results" in saved

    @pytest.mark.asyncio
    async def test_callbacks(self, engine, workflow_io, mock_invoker):
        """测试回调函数"""
        workflow = Workflow(
            id="wf_009",
            name="测试回调",
            nodes=[
                WorkflowNode(
                    id="n1",
                    name="步骤",
                    type="skill",
                    skill="test-skill",
                    input={}
                )
            ],
            edges=[]
        )
        workflow_io.create("test-callback", workflow)

        # 设置回调
        start_calls = []
        complete_calls = []

        async def on_start(node_id):
            start_calls.append(node_id)

        async def on_complete(node_id, output):
            complete_calls.append((node_id, output))

        engine.on_node_start = on_start
        engine.on_node_complete = on_complete

        await engine.execute("test-callback", {})

        assert len(start_calls) == 1
        assert start_calls[0] == "n1"
        assert len(complete_calls) == 1
        assert complete_calls[0][0] == "n1"

    @pytest.mark.asyncio
    async def test_error_handling(self, engine, workflow_io):
        """测试错误处理"""
        workflow = Workflow(
            id="wf_010",
            name="测试错误",
            nodes=[
                WorkflowNode(
                    id="n1",
                    name="步骤1",
                    type="skill",
                    skill="ok-skill",
                    input={}
                ),
                WorkflowNode(
                    id="n2",
                    name="步骤2",
                    type="skill",
                    skill="error-skill",  # 会失败的 skill
                    input={"data": "${n1.output.data}"}
                ),
                WorkflowNode(
                    id="n3",
                    name="步骤3",
                    type="skill",
                    skill="should-not-run",
                    input={}
                )
            ],
            edges=[
                WorkflowEdge(from_node="n1", to_node="n2"),
                WorkflowEdge(from_node="n2", to_node="n3")
            ]
        )
        workflow_io.create("test-error", workflow)

        # 配置 skill invoker：第一个成功，第二个抛异常
        async def failing_invoker(skill_id, input_data):
            if skill_id == "error-skill":
                raise ValueError("模拟错误")
            return {"data": "ok"}

        engine.skill_invoker = failing_invoker

        # 执行应该失败
        with pytest.raises(ValueError, match="模拟错误"):
            await engine.execute("test-error", {})

        # 验证执行状态
        assert engine.current_execution.status == "failed"
        assert len(engine.node_outputs) == 1  # 只有第一个节点成功
        assert "n1" in engine.node_outputs


class TestExpressionParser:
    """测试表达式解析"""

    @pytest.fixture
    def engine(self):
        return WorkflowEngine()

    def test_parse_user_input(self, engine):
        """测试解析用户输入"""
        engine.user_input = {"topic": "AI", "style": "正式"}

        assert engine._evaluate_expression("${user_input.topic}") == "AI"
        assert engine._evaluate_expression("${user_input.style}") == "正式"

    def test_parse_node_output(self, engine):
        """测试解析节点输出"""
        engine.node_outputs = {
            "node_1": {"results": [1, 2, 3], "count": 3}
        }

        assert engine._evaluate_expression("${node_1.output.results}") == [1, 2, 3]
        assert engine._evaluate_expression("${node_1.output.count}") == 3

    def test_parse_nested_field(self, engine):
        """测试解析嵌套字段"""
        engine.node_outputs = {
            "n1": {
                "data": {
                    "title": "标题",
                    "meta": {"author": "张三"}
                }
            }
        }

        assert engine._evaluate_expression("${n1.output.data.title}") == "标题"
        assert engine._evaluate_expression("${n1.output.data.meta.author}") == "张三"

    def test_parse_fixed_value(self, engine):
        """测试固定值"""
        assert engine._evaluate_expression("固定字符串") == "固定字符串"
        assert engine._evaluate_expression(123) == 123
        assert engine._evaluate_expression(True) is True
        assert engine._evaluate_expression(["a", "b"]) == ["a", "b"]

    def test_parse_nonexistent_field(self, engine):
        """测试不存在的字段"""
        engine.node_outputs = {"n1": {"data": {}}}

        # 不存在的字段返回 None
        result = engine._evaluate_expression("${n1.output.data.nonexistent}")
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])