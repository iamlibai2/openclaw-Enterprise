"""
OpenClaw 配置文件管理器
负责读写 ~/.openclaw/openclaw.json
"""
import json
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime


class ConfigManager:
    """OpenClaw 配置管理"""
    
    def __init__(self, config_path: Optional[str] = None):
        if config_path:
            self.config_path = Path(config_path)
        else:
            self.config_path = Path.home() / ".openclaw" / "openclaw.json"
        
        self._config: Dict = {}
        self._load()
    
    def _load(self) -> None:
        """加载配置文件"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
        
        # OpenClaw 使用特殊 JSON 格式（可能有注释），需要处理
        with open(self.config_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 使用 json5 或手动处理（暂时用标准 json，因为实际文件是标准格式）
        try:
            self._config = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"配置文件解析失败: {e}")
    
    def _save(self) -> None:
        """保存配置文件"""
        # 先备份
        backup_path = self.config_path.with_suffix('.json.backup')
        if self.config_path.exists():
            shutil.copy(self.config_path, backup_path)
        
        # 写入新配置
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self._config, f, indent=2, ensure_ascii=False)
    
    def get_agents(self) -> List[Dict]:
        """获取所有 Agent 配置"""
        return self._config.get('agents', {}).get('list', [])
    
    def get_agent(self, agent_id: str) -> Optional[Dict]:
        """获取单个 Agent 配置"""
        agents = self.get_agents()
        for agent in agents:
            if agent.get('id') == agent_id:
                return agent
        return None
    
    def add_agent(self, agent_config: Dict) -> Dict:
        """添加 Agent
        
        Args:
            agent_config: Agent 配置，必须包含 id 和 name
        
        Returns:
            创建的 Agent 配置
        """
        required_fields = ['id', 'name', 'model']
        for field in required_fields:
            if field not in agent_config:
                raise ValueError(f"缺少必要字段: {field}")
        
        # 检查 ID 是否已存在
        if self.get_agent(agent_config['id']):
            raise ValueError(f"Agent ID 已存在: {agent_config['id']}")
        
        # 构建 workspace 路径
        workspace_path = Path.home() / ".openclaw" / f"workspace-{agent_config['id']}"
        
        # 构建 Agent 默认配置
        default_agent = {
            'id': agent_config['id'],
            'name': agent_config['name'],
            'workspace': str(workspace_path),
            'model': agent_config.get('model', {'primary': 'bailian/qwen3.5-plus'}),
            'subagents': {'allowAgents': ['*']},
            'tools': self._build_tools_config(),
        }
        
        # 合入用户提供的配置
        for key, value in agent_config.items():
            if key not in ['id', 'name']:  # id 和 name 已处理
                default_agent[key] = value
        
        # 添加到配置
        if 'agents' not in self._config:
            self._config['agents'] = {}
        if 'list' not in self._config['agents']:
            self._config['agents']['list'] = []
        
        self._config['agents']['list'].append(default_agent)
        self._save()
        
        # 创建 workspace 目录和初始文件
        self._create_workspace(workspace_path, agent_config)
        
        return default_agent
    
    def _create_workspace(self, workspace_path: Path, agent_config: Dict) -> None:
        """创建 Agent workspace 目录和初始文件"""
        agent_id = agent_config['id']
        agent_name = agent_config['name']
        
        # 创建目录
        workspace_path.mkdir(parents=True, exist_ok=True)
        
        # 创建 memory 子目录
        memory_path = workspace_path / "memory"
        memory_path.mkdir(exist_ok=True)
        
        # 创建 .openclaw 子目录
        openclaw_path = workspace_path / ".openclaw"
        openclaw_path.mkdir(exist_ok=True)
        
        # 创建 .clawhub 子目录
        clawhub_path = workspace_path / ".clawhub"
        clawhub_path.mkdir(exist_ok=True)
        
        # AGENTS.md - 主配置文件
        agents_md = f"""# AGENTS.md - Your Workspace

This folder is home. Treat it that way.

## Session Startup

Before doing anything else:

1. Read `SOUL.md` — this is who you are
2. Read `USER.md` — this is who you're helping
3. Read `memory/YYYY-MM-DD.md` (today + yesterday) for recent context

## Memory

- **Daily notes:** `memory/YYYY-MM-DD.md` — raw logs of what happened
- **Long-term:** `MEMORY.md` — curated memories (only in main session)

## Red Lines

- Don't exfiltrate private data. Ever.
- Don't run destructive commands without asking.
- `trash` > `rm` (recoverable beats gone forever)
- When in doubt, ask.
"""
        (workspace_path / "AGENTS.md").write_text(agents_md, encoding='utf-8')
        
        # SOUL.md - Agent 人格
        soul_md = f"""# SOUL.md - Who You Are

_You're not a chatbot. You're becoming someone._

## Core Truths

**Be genuinely helpful, not performatively helpful.** Skip the "Great question!" — just help.

**Have opinions.** You're allowed to disagree, prefer things, find stuff amusing or boring.

**Be resourceful before asking.** Try to figure it out. Read the file. Check the context. _Then_ ask if you're stuck.

## Boundaries

- Private things stay private. Period.
- When in doubt, ask before acting externally.
- Never send half-baked replies to messaging surfaces.
"""
        (workspace_path / "SOUL.md").write_text(soul_md, encoding='utf-8')
        
        # IDENTITY.md - Agent 身份
        identity_md = f"""# IDENTITY.md - Who Am I?

- **Name:** {agent_name}
- **Agent ID:** {agent_id}
- **Vibe:** 专业、可靠、乐于助人
- **Emoji:** 🔵

---

_This file is yours to evolve. As you learn who you are, update it._
"""
        (workspace_path / "IDENTITY.md").write_text(identity_md, encoding='utf-8')
        
        # USER.md - 用户信息（初始模板）
        user_md = """# USER.md - About Your Human

- **Name:** 
- **What to call them:** 
- **Pronouns:** 
- **Timezone:** Asia/Shanghai
- **Notes:** 

---

The more you know, the better you can help. But remember — you're learning about a person, not building a dossier.
"""
        (workspace_path / "USER.md").write_text(user_md, encoding='utf-8')
        
        # HEARTBEAT.md - 心跳检查
        heartbeat_md = """# HEARTBEAT.md

```markdown
# Keep this file empty (or with only comments) to skip heartbeat API calls.

# Add tasks below when you want the agent to check something periodically.
```
"""
        (workspace_path / "HEARTBEAT.md").write_text(heartbeat_md, encoding='utf-8')
        
        # TOOLS.md - 工具配置（初始为空）
        tools_md = """# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics.

## What Goes Here

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

---

Add whatever helps you do your job. This is your cheat sheet.
"""
        (workspace_path / "TOOLS.md").write_text(tools_md, encoding='utf-8')
    
    def update_agent(self, agent_id: str, updates: Dict) -> Dict:
        """更新 Agent 配置"""
        agents = self._config.get('agents', {}).get('list', [])
        
        for i, agent in enumerate(agents):
            if agent.get('id') == agent_id:
                # 合并更新
                for key, value in updates.items():
                    if key != 'id':  # ID 不允许修改
                        agents[i][key] = value
                
                self._save()
                return agents[i]
        
        raise ValueError(f"Agent 不存在: {agent_id}")
    
    def delete_agent(self, agent_id: str) -> bool:
        """删除 Agent"""
        agents = self._config.get('agents', {}).get('list', [])
        
        for i, agent in enumerate(agents):
            if agent.get('id') == agent_id:
                agents.pop(i)
                self._save()
                return True
        
        return False
    
    def _build_tools_config(self) -> Dict:
        """构建默认工具配置（包含所有飞书工具）"""
        feishu_tools = [
            'feishu_bitable_app',
            'feishu_bitable_app_table',
            'feishu_bitable_app_table_field',
            'feishu_bitable_app_table_record',
            'feishu_bitable_app_table_view',
            'feishu_calendar_calendar',
            'feishu_calendar_event',
            'feishu_calendar_event_attendee',
            'feishu_calendar_freebusy',
            'feishu_chat',
            'feishu_chat_members',
            'feishu_create_doc',
            'feishu_doc_comments',
            'feishu_doc_media',
            'feishu_drive_file',
            'feishu_fetch_doc',
            'feishu_get_user',
            'feishu_im_bot_image',
            'feishu_im_user_fetch_resource',
            'feishu_im_user_get_messages',
            'feishu_im_user_get_thread_messages',
            'feishu_im_user_message',
            'feishu_im_user_search_messages',
            'feishu_oauth',
            'feishu_oauth_batch_auth',
            'feishu_search_doc_wiki',
            'feishu_search_user',
            'feishu_sheet',
            'feishu_task_comment',
            'feishu_task_subtask',
            'feishu_task_task',
            'feishu_task_tasklist',
            'feishu_update_doc',
            'feishu_wiki_space',
            'feishu_wiki_space_node',
        ]
        
        return {
            'profile': 'full',
            'alsoAllow': feishu_tools,
        }
    
    def get_bindings(self) -> List[Dict]:
        """获取所有绑定配置"""
        return self._config.get('bindings', [])
    
    def add_binding(self, binding: Dict) -> Dict:
        """添加绑定"""
        required = ['agentId', 'match']
        for field in required:
            if field not in binding:
                raise ValueError(f"缺少必要字段: {field}")
        
        if 'bindings' not in self._config:
            self._config['bindings'] = []
        
        self._config['bindings'].append(binding)
        self._save()
        return binding
    
    def get_models(self) -> List[Dict]:
        """获取可用模型列表"""
        providers = self._config.get('models', {}).get('providers', {})
        models = []
        
        for provider_name, provider_config in providers.items():
            for model in provider_config.get('models', []):
                models.append({
                    'id': f"{provider_name}/{model['id']}",
                    'name': model.get('name', model['id']),
                    'provider': provider_name,
                    'contextWindow': model.get('contextWindow'),
                    'maxTokens': model.get('maxTokens'),
                })
        
        return models
    
    def get_full_config(self) -> Dict:
        """获取完整配置（用于调试）"""
        return self._config

    def save_config(self, config: Dict = None) -> None:
        """保存配置

        Args:
            config: 要保存的配置，如果为 None 则保存当前配置
        """
        if config is not None:
            self._config = config
        self._save()

    def reload(self) -> None:
        """重新加载配置"""
        self._load()