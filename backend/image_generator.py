"""
火山引擎文生图模块

使用 OpenAI 兼容 SDK 调用火山引擎文生图 API
"""
from openai import OpenAI
from typing import Dict, List, Optional
import base64
import time
import os
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
                    if key not in os.environ:  # 不覆盖已有环境变量
                        os.environ[key] = value

_load_env()


class ImageGenerator:
    """火山引擎文生图生成器"""

    def __init__(self, api_key: str, base_url: str = "https://ark.cn-beijing.volces.com/api/v3", model: str = "doubao-seedream-5-0-260128", capabilities: dict = None):
        """
        初始化图片生成器

        Args:
            api_key: 火山引擎 API Key
            base_url: API 基础 URL
            model: 模型 ID
            capabilities: 模型能力配置
        """
        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key
        )
        self.model = model
        self.capabilities = capabilities or {
            "sizes": ["2k", "4k"],
            "maxImages": 4,
            "watermark": False
        }

    def generate(
        self,
        prompt: str,
        size: str = "2k",
        n: int = 1,
        response_format: str = "url"
    ) -> Dict:
        """
        文生图 - 根据提示词生成图片

        Args:
            prompt: 提示词
            size: 图片尺寸，支持 "2k", "4k"
            n: 生成数量，1-4
            response_format: 返回格式，"url" 或 "b64_json"

        Returns:
            {
                "images": [{"url": "...", "b64_json": "..."}],
                "created": timestamp
            }
        """
        # 尺寸格式校验：火山引擎要求至少 3686400 像素
        valid_sizes = self.capabilities.get('sizes', ["2k", "4k"])
        if size not in valid_sizes:
            size = valid_sizes[0]

        # 获取 watermark 配置
        watermark = self.capabilities.get('watermark', False)

        response = self.client.images.generate(
            model=self.model,
            prompt=prompt,
            size=size,
            n=n,
            response_format=response_format,
            extra_body={"watermark": watermark}
        )

        images = []
        for img in response.data:
            image_data = {}
            if hasattr(img, 'url') and img.url:
                image_data['url'] = img.url
            if hasattr(img, 'b64_json') and img.b64_json:
                image_data['b64_json'] = img.b64_json
            images.append(image_data)

        return {
            "images": images,
            "created": response.created if hasattr(response, 'created') else int(time.time())
        }

    def image_to_image(
        self,
        prompt: str,
        image_urls: List[str],
        size: str = "1K",
        n: int = 1
    ) -> Dict:
        """
        图生图 - 根据参考图和提示词生成图片

        Args:
            prompt: 提示词
            image_urls: 参考图片 URL 列表
            size: 图片尺寸
            n: 生成数量

        Returns:
            生成结果
        """
        # 图生图需要使用 image 参数
        response = self.client.images.generate(
            model=self.model,
            prompt=prompt,
            image=image_urls[0] if len(image_urls) == 1 else image_urls,
            size=size,
            n=n
        )

        images = []
        for img in response.data:
            image_data = {}
            if hasattr(img, 'url') and img.url:
                image_data['url'] = img.url
            if hasattr(img, 'b64_json') and img.b64_json:
                image_data['b64_json'] = img.b64_json
            images.append(image_data)

        return {
            "images": images,
            "created": response.created if hasattr(response, 'created') else int(time.time())
        }


# 全局实例
_image_generator: Optional[ImageGenerator] = None


def get_image_generator() -> ImageGenerator:
    """从数据库配置和环境变量获取图片生成器实例"""
    global _image_generator
    if _image_generator is None:
        import os
        import json

        # 使用 SQLAlchemy 查询
        from db_session import SessionLocal
        from sqlalchemy import text

        db_session = SessionLocal()

        try:
            result = db_session.execute(
                text("SELECT * FROM model_providers WHERE name = :name AND enabled = true"),
                {'name': 'volcengine'}
            )
            row = result.fetchone()

            if not row:
                raise ValueError("数据库中未找到启用的 volcengine provider")

            # 获取列名
            columns = list(result.keys())
            provider_dict = dict(zip(columns, row))

            # 从环境变量读取 API Key
            api_key_env = provider_dict.get('api_key_env')
            if not api_key_env:
                raise ValueError("未配置 api_key_env")

            api_key = os.environ.get(api_key_env)

            if not api_key:
                raise ValueError(
                    f"请设置环境变量 {api_key_env}，"
                    f"例如: export {api_key_env}='your-api-key'"
                )

            base_url = provider_dict.get('api_base')

            # 解析模型配置
            config_json = provider_dict.get('config_json')
            config = json.loads(config_json) if config_json else {}
            models = config.get('models', [])

            if not models:
                raise ValueError("volcengine provider 未配置模型")

            # 使用第一个模型
            model_config = models[0]
            model_id = model_config.get('id', 'doubao-seedream-5-0-260128')
            capabilities = model_config.get('capabilities', {
                "sizes": ["2k", "4k"],
                "maxImages": 4,
                "watermark": False
            })

            _image_generator = ImageGenerator(api_key, base_url, model_id, capabilities)

        finally:
            db_session.close()

    return _image_generator