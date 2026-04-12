"""
Workflow file I/O operations.
Handles reading and writing workflow files in Markdown + JSON format.
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, List

from .models import Workflow, Execution, NodeExecution


class WorkflowIO:
    """工作流文件读写"""

    MARKER_START = "<!-- WORKFLOW_DEFINITION"
    MARKER_END = "WORKFLOW_DEFINITION -->"

    def __init__(self, base_path: str = None):
        """
        初始化

        Args:
            base_path: 工作流存储根目录，默认为 backend/data/workflows
        """
        if base_path:
            self.base_path = Path(base_path)
        else:
            # 默认存储路径
            self.base_path = Path(__file__).parent.parent / "data" / "workflows"

        # 确保目录存在
        self.base_path.mkdir(parents=True, exist_ok=True)

    # Skill 描述映射
    SKILL_DESCRIPTIONS = {
        'baidu-search': '使用百度搜索，根据关键词搜索相关资料。',
        'article-generator': '根据输入素材，生成指定风格的文章。',
        'wordpress-publish': '发布文章到 WordPress 平台。',
        'wechat-publisher': '发布内容到微信公众号。',
        'formatter': '将内容排版为指定格式。',
        'data-analyzer': '分析数据并生成报告。',
        'email-sender': '发送电子邮件通知。',
    }

    def create(
        self,
        name: str,
        workflow: Workflow,
        description: str = "",
        meta: dict = None
    ) -> str:
        """
        创建工作流文件

        Args:
            name: 工作流名称（用于目录名）
            workflow: 工作流数据
            description: 工作流描述
            meta: 额外元信息

        Returns:
            文件路径
        """
        workflow_dir = self.base_path / name
        workflow_dir.mkdir(parents=True, exist_ok=True)

        filepath = workflow_dir / "workflow.md"

        # 组装 Markdown 内容
        now = datetime.now().strftime('%Y-%m-%d %H:%M')

        # 自动推断 userInputSchema（如果为空）
        inferred_schema = self._infer_input_schema(workflow)
        if inferred_schema and not workflow.user_input_schema:
            workflow.user_input_schema = inferred_schema

        # 组装使用说明
        use_instructions = self._generate_use_instructions(workflow)

        content = f"""# {workflow.name}

创建时间: {now}
状态: ready

## 目标

{description or '待补充'}

## 使用说明

{use_instructions}

---

{self._encode_json_block(workflow.to_dict())}

## 步骤说明

"""

        # 添加步骤说明（自动生成）
        for i, node in enumerate(workflow.nodes, 1):
            step_desc = self._get_step_description(node)
            content += f"### 第{i}步：{node.name}\n\n{step_desc}\n\n"

        filepath.write_text(content, encoding='utf-8')
        return str(filepath)

    def _infer_input_schema(self, workflow: Workflow) -> dict:
        """从节点 input 配置推断 userInputSchema"""
        schema = {}
        from .models import InputParam

        for node in workflow.nodes:
            for key, expr in node.input.items():
                # 匹配 ${user_input.xxx}
                if isinstance(expr, str) and expr.startswith('${user_input.'):
                    param_name = expr[13:-1]  # 提取 xxx
                    if param_name not in schema:
                        # 根据参数名推断类型
                        param_type = 'string'
                        param_desc = self._get_param_description(param_name)

                        schema[param_name] = InputParam(
                            type=param_type,
                            description=param_desc
                        )

        return schema

    def _get_param_description(self, param_name: str) -> str:
        """根据参数名生成描述"""
        param_desc_map = {
            'topic': '搜索主题/文章主题',
            'query': '搜索关键词',
            'style': '文章风格',
            'length': '文章长度',
            'platform': '发布平台',
            'title': '标题',
            'content': '内容',
        }
        return param_desc_map.get(param_name, param_name)

    def _generate_use_instructions(self, workflow: Workflow) -> str:
        """生成使用说明"""
        if not workflow.user_input_schema:
            return "直接执行工作流即可。"

        instructions = "执行工作流时需提供以下参数：\n"
        for param_name, param in workflow.user_input_schema.items():
            if hasattr(param, 'description'):
                desc = param.description
            elif isinstance(param, dict):
                desc = param.get('description', param_name)
            else:
                desc = param_name
            instructions += f"- **{param_name}**: {desc}\n"

        return instructions

    def _get_step_description(self, node) -> str:
        """根据节点信息生成步骤描述"""
        from .models import WorkflowNode

        if not isinstance(node, WorkflowNode):
            return "待补充说明。"

        # 优先使用预定义的 Skill 描述
        if node.skill and node.skill in self.SKILL_DESCRIPTIONS:
            base_desc = self.SKILL_DESCRIPTIONS[node.skill]
        elif node.agent_id:
            base_desc = f"调用 Agent [{node.agent_id}] 执行任务。"
        else:
            base_desc = f"执行 {node.type} 类型操作。"

        # 补充输入参数说明
        if node.input:
            input_desc = "输入参数："
            for key, val in node.input.items():
                if isinstance(val, str):
                    if val.startswith('${user_input.'):
                        param = val[13:-1]
                        input_desc += f"\n  - {key}: 用户提供的 {param}"
                    elif val.startswith('${'):
                        # 引用上游节点
                        ref = val[2:-1]
                        input_desc += f"\n  - {key}: 来自 {ref}"
                    else:
                        input_desc += f"\n  - {key}: {val}"
                else:
                    input_desc += f"\n  - {key}: {val}"
            return base_desc + "\n" + input_desc

        return base_desc

    def read(self, name: str) -> Tuple[str, Workflow]:
        """
        读取工作流

        Args:
            name: 工作流名称

        Returns:
            (markdown内容, Workflow对象)
        """
        filepath = self.base_path / name / "workflow.md"

        if not filepath.exists():
            raise FileNotFoundError(f"工作流不存在: {name}")

        content = filepath.read_text(encoding='utf-8')
        data = self._decode_json_block(content)

        if not data:
            raise ValueError(f"工作流 JSON 块无效: {name}")

        workflow = Workflow.from_dict(data)
        return content, workflow

    def update_json(self, name: str, workflow: Workflow) -> None:
        """
        更新 JSON 块，保留 Markdown 部分

        Args:
            name: 工作流名称
            workflow: 新的工作流数据
        """
        content, _ = self.read(name)
        new_content = self._replace_json_block(content, workflow.to_dict())

        filepath = self.base_path / name / "workflow.md"
        filepath.write_text(new_content, encoding='utf-8')

    def update_markdown_section(self, name: str, section: str, content: str) -> None:
        """
        更新 Markdown 某个段落，保留 JSON 块

        Args:
            name: 工作流名称
            section: 段落标题（如 "目标", "使用说明"）
            content: 新的段落内容
        """
        old_content, _ = self.read(name)

        # 查找段落位置
        pattern = rf"(## {re.escape(section)}\n)"
        match = re.search(pattern, old_content)

        if not match:
            # 段落不存在，在 JSON 块前添加
            json_start = old_content.find(self.MARKER_START)
            if json_start != -1:
                new_section = f"\n## {section}\n\n{content}\n\n"
                new_content = old_content[:json_start] + new_section + old_content[json_start:]
            else:
                new_content = old_content + f"\n\n## {section}\n\n{content}\n"
        else:
            # 找到下一个 ## 或 JSON 块的位置
            start = match.end()
            next_section = old_content.find("\n## ", start)
            json_pos = old_content.find("\n" + self.MARKER_START, start)

            if next_section == -1:
                next_section = len(old_content)
            if json_pos == -1:
                json_pos = len(old_content)

            end = min(next_section, json_pos)

            # 替换段落内容
            new_content = old_content[:start] + f"\n{content}\n\n" + old_content[end:]

        filepath = self.base_path / name / "workflow.md"
        filepath.write_text(new_content, encoding='utf-8')

    def list_all(self) -> List[dict]:
        """
        列出所有工作流

        Returns:
            工作流列表，每项包含 name, path, created_at
        """
        result = []

        if not self.base_path.exists():
            return result

        for item in self.base_path.iterdir():
            if item.is_dir() and (item / "workflow.md").exists():
                try:
                    _, workflow = self.read(item.name)
                    stat = (item / "workflow.md").stat()
                    result.append({
                        'name': item.name,
                        'display_name': workflow.name,
                        'created_at': datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M'),
                        'node_count': len(workflow.nodes)
                    })
                except Exception as e:
                    result.append({
                        'name': item.name,
                        'display_name': item.name,
                        'error': str(e)
                    })

        return sorted(result, key=lambda x: x.get('created_at', ''), reverse=True)

    def delete(self, name: str) -> bool:
        """
        删除工作流

        Args:
            name: 工作流名称

        Returns:
            是否成功
        """
        import shutil

        workflow_dir = self.base_path / name
        if workflow_dir.exists():
            shutil.rmtree(workflow_dir)
            return True
        return False

    def exists(self, name: str) -> bool:
        """检查工作流是否存在"""
        return (self.base_path / name / "workflow.md").exists()

    def validate(self, name: str) -> Tuple[bool, str]:
        """
        验证工作流是否有效

        Returns:
            (是否有效, 错误信息)
        """
        try:
            content, workflow = self.read(name)

            if not workflow.id:
                return False, "缺少 id"
            if not workflow.name:
                return False, "缺少 name"
            if not workflow.nodes:
                return False, "节点列表为空"

            # 检查节点 ID 唯一性
            node_ids = [n.id for n in workflow.nodes]
            if len(node_ids) != len(set(node_ids)):
                return False, "存在重复的节点 ID"

            # 检查边的节点是否存在
            for edge in workflow.edges:
                if edge.from_node not in node_ids:
                    return False, f"边的起始节点不存在: {edge.from_node}"
                if edge.to_node not in node_ids:
                    return False, f"边的目标节点不存在: {edge.to_node}"

            return True, ""

        except FileNotFoundError:
            return False, f"工作流不存在: {name}"
        except Exception as e:
            return False, str(e)

    # ==================== 内部方法 ====================

    def _encode_json_block(self, data: dict) -> str:
        """将数据编码为 JSON 块"""
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        return f"{self.MARKER_START}\n{json_str}\n{self.MARKER_END}"

    def _decode_json_block(self, content: str) -> Optional[dict]:
        """从内容中提取 JSON 块"""
        start = content.find(self.MARKER_START)
        end = content.find(self.MARKER_END)

        if start == -1 or end == -1:
            return None

        json_str = content[start + len(self.MARKER_START):end].strip()

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON 解析失败: {e}")

    def _replace_json_block(self, content: str, new_data: dict) -> str:
        """替换 JSON 块，保留其他内容"""
        new_block = self._encode_json_block(new_data)

        start = content.find(self.MARKER_START)
        end = content.find(self.MARKER_END)

        if start == -1:
            # 没有 JSON 块，追加到末尾
            return content + "\n\n---\n\n" + new_block + "\n"

        return content[:start] + new_block + content[end + len(self.MARKER_END):]


class ExecutionIO:
    """执行记录文件读写"""

    MARKER_START = "<!-- EXECUTION_DATA"
    MARKER_END = "EXECUTION_DATA -->"

    def __init__(self, base_path: str = None):
        if base_path:
            self.base_path = Path(base_path)
        else:
            self.base_path = Path(__file__).parent.parent / "data" / "workflows"

    def create(
        self,
        workflow_name: str,
        execution: Execution
    ) -> str:
        """创建执行记录文件"""
        exec_dir = self.base_path / workflow_name / "executions"
        exec_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M')
        filename = f"{timestamp}.md"
        filepath = exec_dir / filename

        # 组装内容
        duration = ""
        if execution.started_at and execution.completed_at:
            secs = (execution.completed_at - execution.started_at).total_seconds()
            duration = f"耗时: {int(secs)}秒"

        content = f"""# 执行记录: {datetime.now().strftime('%Y-%m-%d %H:%M')}

工作流: {execution.workflow_name}
状态: {self._status_text(execution.status)}
{duration}

## 用户输入

"""

        # 用户输入
        for key, val in execution.user_input.items():
            content += f"- {key}: {val}\n"

        content += f"\n---\n\n{self._encode_json_block(execution.to_dict())}\n\n"

        # 执行过程
        content += "## 执行过程\n\n"
        for ne in execution.node_executions:
            status_icon = "✅" if ne.status == "completed" else ("❌" if ne.status == "failed" else "⏳")
            duration_str = f"({int(ne.duration)}秒)" if ne.duration else ""
            content += f"### {ne.node_id}: {ne.status} {status_icon} {duration_str}\n\n"
            if ne.error:
                content += f"错误: {ne.error}\n\n"

        # 最终结果
        if execution.final_output:
            content += "## 最终结果\n\n"
            content += self._format_output(execution.final_output)

        filepath.write_text(content, encoding='utf-8')
        return str(filepath)

    def read(self, workflow_name: str, filename: str) -> Tuple[str, Execution]:
        """读取执行记录"""
        filepath = self.base_path / workflow_name / "executions" / filename

        if not filepath.exists():
            raise FileNotFoundError(f"执行记录不存在: {filename}")

        content = filepath.read_text(encoding='utf-8')
        data = self._decode_json_block(content)

        if not data:
            raise ValueError(f"执行记录 JSON 块无效: {filename}")

        # 解析节点执行记录，处理 camelCase 到 snake_case 的转换
        node_executions = []
        for ne in data.get('nodeExecutions', []):
            node_executions.append(NodeExecution(
                node_id=ne['nodeId'],
                status=ne['status'],
                duration=ne.get('duration', 0),
                output_file=ne.get('outputFile'),
                error=ne.get('error'),
                started_at=datetime.fromisoformat(ne['startedAt']) if ne.get('startedAt') else None,
                completed_at=datetime.fromisoformat(ne['completedAt']) if ne.get('completedAt') else None
            ))

        execution = Execution(
            execution_id=data['executionId'],
            workflow_id=data['workflowId'],
            workflow_name=data.get('workflowName', workflow_name),
            status=data['status'],
            user_input=data.get('userInput', {}),
            node_executions=node_executions,
            final_output=data.get('finalOutput'),
            started_at=datetime.fromisoformat(data['startedAt']) if data.get('startedAt') else None,
            completed_at=datetime.fromisoformat(data['completedAt']) if data.get('completedAt') else None
        )

        return content, execution

    def list_all(self, workflow_name: str) -> List[dict]:
        """列出某个工作流的所有执行记录"""
        exec_dir = self.base_path / workflow_name / "executions"

        if not exec_dir.exists():
            return []

        result = []
        for item in sorted(exec_dir.iterdir(), reverse=True):
            if item.suffix == '.md':
                try:
                    _, execution = self.read(workflow_name, item.name)
                    result.append({
                        'filename': item.name,
                        'execution_id': execution.execution_id,
                        'status': execution.status,
                        'started_at': execution.started_at.strftime('%Y-%m-%d %H:%M') if execution.started_at else None,
                    })
                except:
                    pass

        return result

    def _encode_json_block(self, data: dict) -> str:
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        return f"{self.MARKER_START}\n{json_str}\n{self.MARKER_END}"

    def _decode_json_block(self, content: str) -> Optional[dict]:
        start = content.find(self.MARKER_START)
        end = content.find(self.MARKER_END)

        if start == -1 or end == -1:
            return None

        json_str = content[start + len(self.MARKER_START):end].strip()

        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return None

    def _status_text(self, status: str) -> str:
        mapping = {
            'running': '执行中',
            'completed': '完成',
            'failed': '失败'
        }
        return mapping.get(status, status)

    def _format_output(self, output: dict, indent: int = 0) -> str:
        """格式化输出内容"""
        result = ""
        prefix = "  " * indent

        if isinstance(output, dict):
            for key, val in output.items():
                if isinstance(val, (dict, list)):
                    result += f"{prefix}- {key}:\n{self._format_output(val, indent + 1)}"
                else:
                    result += f"{prefix}- {key}: {val}\n"
        elif isinstance(output, list):
            for i, item in enumerate(output[:5]):  # 最多显示5个
                if isinstance(item, dict):
                    result += f"{prefix}{i+1}. {item.get('title', item.get('name', str(item)[:50]))}\n"
                else:
                    result += f"{prefix}- {str(item)[:100]}\n"
            if len(output) > 5:
                result += f"{prefix}... 共 {len(output)} 项\n"
        else:
            result = f"{prefix}{str(output)[:500]}\n"

        return result


class OutputIO:
    """节点输出文件读写"""

    def __init__(self, base_path: str = None):
        if base_path:
            self.base_path = Path(base_path)
        else:
            self.base_path = Path(__file__).parent.parent / "data" / "workflows"

    def save(self, workflow_name: str, execution_id: str, node_id: str, output: any) -> str:
        """
        保存节点输出到 JSON 文件

        Args:
            workflow_name: 工作流名称
            execution_id: 执行 ID
            node_id: 节点 ID
            output: 输出数据

        Returns:
            文件路径
        """
        output_dir = self.base_path / workflow_name / "outputs" / execution_id
        output_dir.mkdir(parents=True, exist_ok=True)

        filepath = output_dir / f"{node_id}.json"
        filepath.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')

        return str(filepath)

    def load(self, workflow_name: str, execution_id: str, node_id: str) -> Optional[any]:
        """
        读取节点输出

        Returns:
            输出数据，不存在则返回 None
        """
        filepath = self.base_path / workflow_name / "outputs" / execution_id / f"{node_id}.json"

        if not filepath.exists():
            return None

        return json.loads(filepath.read_text(encoding='utf-8'))

    def list_outputs(self, workflow_name: str, execution_id: str) -> List[str]:
        """列出某次执行的所有输出文件"""
        output_dir = self.base_path / workflow_name / "outputs" / execution_id

        if not output_dir.exists():
            return []

        return [f.stem for f in output_dir.glob("*.json")]