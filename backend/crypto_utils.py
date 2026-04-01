"""
加密工具模块

用于敏感信息（如 API Key）的加密存储和解密读取。
采用 AES-256-GCM 算法，提供安全的加密和认证。

使用方式:
    from crypto_utils import CryptoUtils

    crypto = CryptoUtils()
    encrypted = crypto.encrypt("sk-abc123")  # 加密
    decrypted = crypto.decrypt(encrypted)    # 解密
    masked = crypto.mask_key(encrypted)      # 脱敏显示
"""
import os
import base64
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class CryptoUtils:
    """加密工具类"""

    def __init__(self):
        """初始化加密工具，自动加载或生成密钥"""
        self.key_env_name = 'OPENCLAW_ENCRYPT_KEY'
        self._key = self._load_or_generate_key()
        self._aesgcm = AESGCM(self._key)

    def _load_or_generate_key(self) -> bytes:
        """加载或生成加密密钥"""
        key_hex = os.environ.get(self.key_env_name)

        if key_hex:
            # 从环境变量加载密钥
            try:
                return bytes.fromhex(key_hex)
            except ValueError:
                raise ValueError(f"环境变量 {self.key_env_name} 格式错误，应为 64 位十六进制字符串")

        # 生成新密钥
        key = AESGCM.generate_key(bit_length=256)
        self._save_key_to_env(key)
        return key

    def _save_key_to_env(self, key: bytes):
        """保存密钥到 .env 文件"""
        key_hex = key.hex()

        # 确定 .env 文件路径
        env_path = Path(__file__).parent / '.env'

        # 如果文件已存在，追加；否则创建
        if env_path.exists():
            with open(env_path, 'r') as f:
                content = f.read()

            # 检查是否已有密钥配置
            if self.key_env_name in content:
                # 替换现有密钥
                lines = content.split('\n')
                new_lines = []
                for line in lines:
                    if line.startswith(self.key_env_name):
                        new_lines.append(f'{self.key_env_name}={key_hex}')
                    else:
                        new_lines.append(line)
                content = '\n'.join(new_lines)
            else:
                # 追加新密钥
                content = content.rstrip('\n') + f'\n{self.key_env_name}={key_hex}\n'

            with open(env_path, 'w') as f:
                f.write(content)
        else:
            # 创建新文件
            with open(env_path, 'w') as f:
                f.write(f'# OpenClaw Admin UI 环境变量\n')
                f.write(f'# 生成时间: {self._get_timestamp()}\n')
                f.write(f'\n')
                f.write(f'{self.key_env_name}={key_hex}\n')

        # 同时设置到当前进程的环境变量
        os.environ[self.key_env_name] = key_hex

        print(f"[CryptoUtils] 加密密钥已生成并保存到: {env_path}")
        print(f"[CryptoUtils] 请妥善保管此密钥，密钥丢失将无法解密已存储的敏感信息！")

    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def encrypt(self, plaintext: str) -> str:
        """
        加密字符串

        Args:
            plaintext: 待加密的明文

        Returns:
            Base64 编码的加密数据（包含 nonce）

        Raises:
            ValueError: 如果明文为空
        """
        if not plaintext:
            raise ValueError("加密内容不能为空")

        # 生成随机 nonce（12 字节）
        nonce = os.urandom(12)

        # 加密（AES-256-GCM）
        ciphertext = self._aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)

        # 组合 nonce + ciphertext，然后 Base64 编码
        encrypted_data = nonce + ciphertext
        return base64.b64encode(encrypted_data).decode('utf-8')

    def decrypt(self, encrypted: str) -> str:
        """
        解密字符串

        Args:
            encrypted: Base64 编码的加密数据

        Returns:
            解密后的明文

        Raises:
            ValueError: 如果加密数据格式错误或解密失败
        """
        if not encrypted:
            raise ValueError("解密内容不能为空")

        try:
            # Base64 解码
            encrypted_data = base64.b64decode(encrypted)

            # 分离 nonce（前 12 字节）和 ciphertext
            nonce = encrypted_data[:12]
            ciphertext = encrypted_data[12:]

            # 解密
            plaintext = self._aesgcm.decrypt(nonce, ciphertext, None)
            return plaintext.decode('utf-8')

        except Exception as e:
            raise ValueError(f"解密失败: {str(e)}")

    def mask_key(self, encrypted_or_plain: str, is_encrypted: bool = True) -> str:
        """
        脱敏显示密钥

        Args:
            encrypted_or_plain: 加密后的数据或原始密钥
            is_encrypted: 是否为加密数据（默认 True）

        Returns:
            脱敏后的字符串，格式: 前4位****后4位
        """
        try:
            if is_encrypted:
                # 解密后再脱敏
                key = self.decrypt(encrypted_or_plain)
            else:
                key = encrypted_or_plain

            if len(key) <= 8:
                return '****'

            return key[:4] + '****' + key[-4:]

        except Exception:
            # 如果解密失败，返回固定脱敏字符串
            return '****'

    def is_encrypted(self, value: str) -> bool:
        """
        判断字符串是否为加密数据

        Args:
            value: 待判断的字符串

        Returns:
            是否为有效的加密数据格式
        """
        if not value:
            return False

        try:
            # 尝试 Base64 解码
            data = base64.b64decode(value)

            # 检查长度（至少 12 字节 nonce + 16 字节 tag + 1 字节 plaintext = 29 字节）
            if len(data) < 29:
                return False

            # 尝试解密
            self.decrypt(value)
            return True

        except Exception:
            return False


# 全局实例（单例）
_crypto_instance: CryptoUtils = None


def get_crypto() -> CryptoUtils:
    """获取加密工具全局实例"""
    global _crypto_instance
    if _crypto_instance is None:
        _crypto_instance = CryptoUtils()
    return _crypto_instance


# 便捷函数
def encrypt(plaintext: str) -> str:
    """加密字符串"""
    return get_crypto().encrypt(plaintext)


def decrypt(encrypted: str) -> str:
    """解密字符串"""
    return get_crypto().decrypt(encrypted)


def mask_key(value: str, is_encrypted: bool = True) -> str:
    """脱敏显示密钥"""
    return get_crypto().mask_key(value, is_encrypted)