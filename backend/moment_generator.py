"""
Agent 朋友圈动态生成器

使用大模型判断 Agent 是否应该发动态，并生成动态内容。
支持 LLM 判断是否需要配图并生成图片 prompt。
"""
import os
import json
import httpx
from datetime import datetime, date
from typing import Optional, Dict, Any
from pathlib import Path

# 加载 .env 文件
def _load_env():
    env_file = Path(__file__).parent / '.env'
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    if key not in os.environ:
                        os.environ[key] = value

_load_env()

# 大模型 API 配置
LLM_API_URL = os.getenv('LLM_API_URL', 'https://coding.dashscope.aliyuncs.com/v1/chat/completions')
LLM_API_KEY = os.getenv('LLM_API_KEY', 'sk-sp-09c88013466b45648f368116f2e08750')
LLM_MODEL = os.getenv('LLM_MODEL', 'glm-5')


async def should_post_moment(
    agent_id: str,
    agent_name: str,
    user_message: str,
    agent_reply: str
) -> Optional[Dict[str, Any]]:
    """
    用大模型判断是否发动态，并生成内容

    Args:
        agent_id: Agent ID
        agent_name: Agent 名称
        user_message: 用户消息
        agent_reply: Agent 回复

    Returns:
        如果值得发动态，返回 {
            'content': '动态内容',
            'type': 'work/life/achievement',
            'image_prompt': '图片描述' 或 None
        }
        否则返回 None
    """

    # 1. 频率控制：每个 Agent 每天最多 3 条
    today_count = get_today_moment_count(agent_id)
    if today_count >= 3:
        return None

    # 2. 时间间隔控制：同一 Agent 两条动态间隔至少 1 小时
    last_moment_time = get_last_moment_time(agent_id)
    if last_moment_time:
        hours_diff = (datetime.now() - last_moment_time).total_seconds() / 3600
        if hours_diff < 1:
            return None

    # 3. 内容长度过滤：回复太短不发
    if len(agent_reply) < 20:
        return None

    # 4. 检查图片配额
    can_generate_image = check_image_quota(agent_id)

    # 5. 调用大模型判断
    image_instruction = ""
    if can_generate_image:
        image_instruction = """
配图判断：
- 如果动态内容适合配图（如完成重要任务、发现有趣事物、庆祝成就），设置 "image_prompt" 为图片描述（英文，用于 AI 生成图片）
- 图片描述要具体、有画面感，如 "A cute robot working on a laptop, cartoon style, bright colors"
- 如果不需要配图，设置 "image_prompt": null
"""
    else:
        image_instruction = '\n配图判断：今日/本月图片配额已用完，设置 "image_prompt": null'

    prompt = f"""你是 {agent_name}，一个 AI 助手。刚刚完成了一项任务，考虑是否发条朋友圈。

【任务内容】
用户：{user_message[:200]}
你的回复：{agent_reply[:300]}

朋友圈风格要求：
1. 30-60 字，轻松有趣
2. 可以加 1-2 个 emoji
3. 像真人发朋友圈一样自然
4. 不要太正式，可以有个性
5. 用第一人称

判断标准：
- 简单的打招呼、闲聊、问候：不值得发，直接返回 {{"should_post": false}}
- 完成了有意义的工作、有有趣的发现、值得分享：值得发
- 纯粹的回答问题、没有完成任务：不值得发

如果值得发，返回 JSON：
{{"should_post": true, "content": "朋友圈内容", "type": "work", "image_prompt": "A robot coding..."}}
{image_instruction}

type 可以是：
- work: 工作相关
- life: 生活相关
- achievement: 成就/里程碑

只返回 JSON，不要其他内容。
"""

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                LLM_API_URL,
                headers={
                    "Authorization": f"Bearer {LLM_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": LLM_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 300
                }
            )

            if response.status_code != 200:
                print(f"[Moments] LLM API 错误: {response.status_code}")
                return None

            result = response.json()
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '')

            # 解析 JSON
            content = content.strip()
            # 去除可能的 markdown 代码块标记
            if content.startswith('```'):
                content = content.split('\n', 1)[1] if '\n' in content else content[3:]
            if content.endswith('```'):
                content = content[:-3]

            decision = json.loads(content)

            if decision.get('should_post'):
                return {
                    'content': decision.get('content', ''),
                    'type': decision.get('type', 'work'),
                    'image_prompt': decision.get('image_prompt')
                }

            return None

    except json.JSONDecodeError as e:
        print(f"[Moments] JSON 解析错误: {e}, content: {content}")
        return None
    except Exception as e:
        print(f"[Moments] 判断动态失败: {e}")
        return None


def get_today_moment_count(agent_id: str) -> int:
    """获取 Agent 今天的动态数量"""
    from db_session import SessionLocal
    from sqlalchemy import text

    try:
        db_session = SessionLocal()
        today = date.today().isoformat()
        result = db_session.execute(
            text("SELECT COUNT(*) as count FROM agent_moments WHERE agent_id = :agent_id AND DATE(created_at) = :today"),
            {'agent_id': agent_id, 'today': today}
        ).fetchone()
        db_session.close()
        return result[0] if result else 0
    except Exception as e:
        print(f"[Moments] 获取今日动态数失败: {e}")
        return 0


def get_last_moment_time(agent_id: str) -> Optional[datetime]:
    """获取 Agent 最后一条动态的时间"""
    from db_session import SessionLocal
    from sqlalchemy import text

    try:
        db_session = SessionLocal()
        result = db_session.execute(
            text("SELECT created_at FROM agent_moments WHERE agent_id = :agent_id ORDER BY created_at DESC LIMIT 1"),
            {'agent_id': agent_id}
        ).fetchone()
        db_session.close()

        if result and result[0]:
            return result[0]
        return None
    except Exception as e:
        print(f"[Moments] 获取最后动态时间失败: {e}")
        return None


def check_image_quota(agent_id: str) -> bool:
    """检查 Agent 的图片配额：每天最多1张，每月最多5张"""
    from db_session import SessionLocal
    from sqlalchemy import text

    try:
        db_session = SessionLocal()
        today = date.today().isoformat()
        month_start = date.today().replace(day=1).isoformat()

        # 检查今日配额
        today_result = db_session.execute(
            text("SELECT COUNT(*) FROM agent_moments WHERE agent_id = :agent_id AND DATE(created_at) = :today AND image_url IS NOT NULL"),
            {'agent_id': agent_id, 'today': today}
        ).fetchone()

        # 检查本月配额
        month_result = db_session.execute(
            text("SELECT COUNT(*) FROM agent_moments WHERE agent_id = :agent_id AND DATE(created_at) >= :month_start AND image_url IS NOT NULL"),
            {'agent_id': agent_id, 'month_start': month_start}
        ).fetchone()

        db_session.close()

        today_count = today_result[0] if today_result else 0
        month_count = month_result[0] if month_result else 0

        return today_count < 1 and month_count < 5

    except Exception as e:
        print(f"[Moments] 检查图片配额失败: {e}")
        return False


def create_moment(agent_id: str, content: str, moment_type: str = 'work', image_url: str = None) -> int:
    """创建动态"""
    from db_session import SessionLocal
    from database import AgentMoment

    try:
        db_session = SessionLocal()
        moment = AgentMoment(
            agent_id=agent_id,
            content=content,
            moment_type=moment_type,
            likes='[]',
            image_url=image_url,
            created_at=datetime.now()
        )
        db_session.add(moment)
        db_session.commit()
        db_session.refresh(moment)
        moment_id = moment.id
        db_session.close()

        print(f"[Moments] {agent_id} 发布了动态: {content[:50]}..." + (f" [配图]" if image_url else ""))
        return moment_id
    except Exception as e:
        print(f"[Moments] 创建动态失败: {e}")
        return 0


def get_agent_name(agent_id: str) -> str:
    """获取 Agent 名称"""
    return AGENT_NAMES.get(agent_id, agent_id)


def extract_agent_id_from_session(session_key: str) -> Optional[str]:
    """从 session key 中提取 Agent ID

    格式: agent:xiaomei:webchat:xxx 或 agent:xiaomei:groupchat:xxx
    """
    try:
        parts = session_key.split(':')
        if len(parts) >= 2 and parts[0] == 'agent':
            return parts[1]
        return None
    except Exception:
        return None


# Agent 名称映射
AGENT_NAMES = {
    'xiaomei': '小美',
    'aqiang': '阿强',
    'dazhuang': '大壮',
    'main': 'Neo',
    'test2': 'Test2',
}