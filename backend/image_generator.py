"""
火山引擎文生图模块

使用 OpenAI 兼容 SDK 调用火山引擎文生图 API
"""
from openai import OpenAI
from typing import Dict, List, Optional
import base64
import time


class ImageGenerator:
    """火山引擎文生图生成器"""

    def __init__(self, api_key: str):
        """
        初始化图片生成器

        Args:
            api_key: 火山引擎 API Key
        """
        self.client = OpenAI(
            base_url="https://ark.cn-beijing.volces.com/api/v3",
            api_key=api_key
        )
        self.model = "doubao-seedream-5-0-260128"

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
        valid_sizes = ["2k", "4k"]
        if size not in valid_sizes:
            size = "2k"

        response = self.client.images.generate(
            model=self.model,
            prompt=prompt,
            size=size,
            n=n,
            response_format=response_format,
            extra_body={"watermark": False}
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
    """获取图片生成器实例"""
    global _image_generator
    if _image_generator is None:
        from settings import settings
        api_key = settings.VOLCENGINE_API_KEY
        _image_generator = ImageGenerator(api_key)
    return _image_generator