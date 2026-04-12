"""
LLM Service for Orchestration Agent

提供一个简单的 LLM 调用接口，用于编排 Agent 的意图解析和工作流生成。
"""

import os
import json
import asyncio
import aiohttp
from typing import Optional, Dict, Any


class LLMService:
    """LLM 调用服务"""

    def __init__(
        self,
        api_base: str = None,
        api_key: str = None,
        model: str = None
    ):
        """
        初始化 LLM 服务

        Args:
            api_base: API 地址（OpenAI-compatible）
            api_key: API Key
            model: 模型名称
        """
        # 从环境变量或参数获取配置
        self.api_base = api_base or os.getenv('LLM_API_BASE', 'https://api.deepseek.com/v1')
        self.api_key = api_key or os.getenv('LLM_API_KEY', '')
        self.model = model or os.getenv('LLM_MODEL', 'deepseek-chat')

        # 如果没有配置，尝试从数据库读取
        self._load_from_db = not (self.api_key and self.model)

    def _get_db_config(self) -> Dict:
        """从数据库获取模型配置"""
        try:
            from db_session import SessionLocal
            from database import ModelProvider

            db = SessionLocal()
            # 获取第一个启用的模型提供商
            provider = db.query(ModelProvider).filter(
                ModelProvider.enabled == True
            ).first()

            if provider:
                return {
                    'api_base': provider.base_url,
                    'api_key': provider.api_key,
                    'model': provider.models[0] if provider.models else 'gpt-4'
                }
            db.close()
        except Exception:
            pass

        return {}

    async def call(self, prompt: str, system_prompt: str = None) -> str:
        """
        调用 LLM

        Args:
            prompt: 用户输入
            system_prompt: 系统提示（可选）

        Returns:
            LLM 响应文本
        """
        # 如果需要从数据库加载配置
        if self._load_from_db:
            config = self._get_db_config()
            if config:
                self.api_base = config['api_base']
                self.api_key = config['api_key']
                self.model = config['model']
                self._load_from_db = False

        # 如果仍然没有配置，返回错误
        if not self.api_key:
            raise ValueError("LLM API Key 未配置。请设置环境变量 LLM_API_KEY 或在数据库中配置模型提供商。")

        # 构建请求
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2000
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # 调用 API
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_base}/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        raise ValueError(f"LLM API 错误: {resp.status} - {text}")

                    data = await resp.json()
                    return data['choices'][0]['message']['content']
        except asyncio.TimeoutError:
            raise ValueError("LLM API 调用超时")
        except Exception as e:
            raise ValueError(f"LLM 调用失败: {str(e)}")


def create_llm_caller(llm_service: LLMService = None) -> callable:
    """
    创建编排 Agent 可用的 LLM caller 函数

    Args:
        llm_service: LLM 服务实例

    Returns:
        async callable，签名为 async (prompt: str) -> str
    """
    service = llm_service or LLMService()

    async def caller(prompt: str) -> str:
        return await service.call(prompt)

    return caller