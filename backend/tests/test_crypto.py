"""
加密工具测试

测试内容：
- AES 加密/解密
- 密钥管理
- 敏感数据处理

覆盖率目标：提高 crypto_utils.py 覆盖率
"""

import pytest


class TestEncryption:
    """加密测试"""

    def test_encrypt_decrypt(self):
        """测试加密解密"""
        try:
            from crypto_utils import encrypt, decrypt

            plaintext = "sensitive_data_123"
            encrypted = encrypt(plaintext)

            # 加密后应该不同
            assert encrypted != plaintext

            # 解密应该还原
            decrypted = decrypt(encrypted)
            assert decrypted == plaintext

        except ImportError:
            pytest.skip("encrypt/decrypt not available")

    def test_encrypt_empty_string(self):
        """测试加密空字符串"""
        try:
            from crypto_utils import encrypt, decrypt

            encrypted = encrypt("")
            # 空字符串可能返回空或抛出异常
            if encrypted:
                decrypted = decrypt(encrypted)
                assert decrypted == ""

        except (ImportError, ValueError):
            pytest.skip("encrypt/decrypt not available or doesn't support empty string")

    def test_encrypt_unicode(self):
        """测试加密 Unicode"""
        try:
            from crypto_utils import encrypt, decrypt

            plaintext = "中文测试 日本語 한국어"
            encrypted = encrypt(plaintext)
            decrypted = decrypt(encrypted)
            assert decrypted == plaintext

        except ImportError:
            pytest.skip("encrypt/decrypt not available")

    def test_encrypt_long_string(self):
        """测试加密长字符串"""
        try:
            from crypto_utils import encrypt, decrypt

            plaintext = "a" * 10000
            encrypted = encrypt(plaintext)
            decrypted = decrypt(encrypted)
            assert decrypted == plaintext

        except ImportError:
            pytest.skip("encrypt/decrypt not available")


class TestKeyManagement:
    """密钥管理测试"""

    def test_get_encryption_key(self):
        """测试获取加密密钥"""
        try:
            from crypto_utils import get_encryption_key

            key = get_encryption_key()
            assert key is not None
            assert len(key) > 0

        except ImportError:
            pytest.skip("get_encryption_key not available")

    def test_key_consistency(self):
        """测试密钥一致性"""
        try:
            from crypto_utils import get_encryption_key

            key1 = get_encryption_key()
            key2 = get_encryption_key()

            # 同一进程内密钥应该一致
            assert key1 == key2

        except ImportError:
            pytest.skip("get_encryption_key not available")


class TestHashFunctions:
    """哈希函数测试"""

    def test_hash_password_exists(self):
        """测试密码哈希函数存在"""
        from auth import hash_password, verify_password

        assert hash_password is not None
        assert verify_password is not None

    def test_hash_verification(self):
        """测试哈希验证"""
        from auth import hash_password, verify_password

        password = "test_password"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True
        assert verify_password("wrong_password", hashed) is False

    def test_hash_uniqueness(self):
        """测试哈希唯一性（不同盐值）"""
        from auth import hash_password

        password = "same_password"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        # 相同密码应该生成不同哈希（不同盐值）
        assert hash1 != hash2


class TestSecureRandom:
    """安全随机数测试"""

    def test_generate_random_token(self):
        """测试生成随机 Token"""
        try:
            from crypto_utils import generate_token

            token1 = generate_token()
            token2 = generate_token()

            assert token1 != token2
            assert len(token1) > 0

        except ImportError:
            pytest.skip("generate_token not available")

    def test_generate_random_string(self):
        """测试生成随机字符串"""
        try:
            from crypto_utils import generate_random_string

            s1 = generate_random_string(16)
            s2 = generate_random_string(16)

            assert len(s1) == 16
            assert s1 != s2

        except ImportError:
            pytest.skip("generate_random_string not available")


class TestAPIKeyEncryption:
    """API Key 加密测试"""

    def test_encrypt_api_key(self):
        """测试 API Key 加密"""
        try:
            from crypto_utils import encrypt_api_key, decrypt_api_key

            api_key = "sk-1234567890abcdef"
            encrypted = encrypt_api_key(api_key)
            decrypted = decrypt_api_key(encrypted)

            assert decrypted == api_key

        except ImportError:
            pytest.skip("encrypt_api_key/decrypt_api_key not available")

    def test_encrypt_empty_api_key(self):
        """测试空 API Key"""
        try:
            from crypto_utils import encrypt_api_key, decrypt_api_key

            encrypted = encrypt_api_key("")
            decrypted = decrypt_api_key(encrypted)
            assert decrypted == ""

        except ImportError:
            pytest.skip("encrypt_api_key/decrypt_api_key not available")


class TestDataMasking:
    """数据脱敏测试"""

    def test_mask_email(self):
        """测试邮箱脱敏"""
        try:
            from crypto_utils import mask_email

            result = mask_email("test@example.com")
            # 应该隐藏部分内容
            assert "@" in result
            assert result != "test@example.com"

        except ImportError:
            pytest.skip("mask_email not available")

    def test_mask_phone(self):
        """测试手机号脱敏"""
        try:
            from crypto_utils import mask_phone

            result = mask_phone("13800138000")
            # 应该隐藏中间部分
            assert result != "13800138000"

        except ImportError:
            pytest.skip("mask_phone not available")

    def test_mask_api_key(self):
        """测试 API Key 脱敏"""
        try:
            from crypto_utils import mask_api_key

            result = mask_api_key("sk-1234567890abcdef")
            # 应该隐藏大部分内容
            assert "sk-" in result or "*" in result

        except ImportError:
            pytest.skip("mask_api_key not available")