#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Umi-OCR Windows 凭证管理器

使用 Windows Credential Manager 安全存储云 API Key。

主要功能:
- 安全存储 API 密钥到 Windows Credential Manager
- 加密存储，无法直接读取明文
- 支持多提供商管理
- 凭证验证和测试

Author: Umi-OCR Team
Date: 2026-01-27
"""

from typing import Dict, Any, Optional, List
import logging

from PySide6.QtCore import QObject, Signal


# =============================================================================
# Windows API 导入
# =============================================================================

try:
    import win32cred
    from win32cred import CRED_TYPE_GENERIC, CRED_PERSIST_ENTERPRISE
    WIN32CRED_AVAILABLE = True
except ImportError:
    WIN32CRED_AVAILABLE = False
    win32cred = None
    CRED_TYPE_GENERIC = None
    CRED_PERSIST_ENTERPRISE = None

    logging.warning("win32cred 模块不可用，凭证管理功能将受限")


# =============================================================================
# 凭证管理器异常
# =============================================================================

class CredentialError(Exception):
    """凭证管理异常"""
    pass

class CredentialNotFoundError(CredentialError):
    """凭证未找到异常"""
    pass

class CredentialReadError(CredentialError):
    """凭证读取异常"""
    pass

class CredentialWriteError(CredentialError):
    """凭证写入异常"""
    pass


# =============================================================================
# Windows 凭证管理器
# =============================================================================

class CredentialManager(QObject):
    """
    Windows Credential Manager 封装

    安全存储云 API 凭证，使用 Windows 系统级别的加密存储。

    支持的提供商:
    - baidu: 百度云
    - tencent: 腾讯云
    - aliyun: 阿里云
    """

    # -------------------------------------------------------------------------
    # 信号定义
    # -------------------------------------------------------------------------

    # 凭证变更信号
    # 参数: provider (str), action (str: 'saved'/'deleted'/'updated')
    credentials_changed = Signal(str, str)

    # -------------------------------------------------------------------------
    # 类属性
    # -------------------------------------------------------------------------

    # 凭证前缀（用于标识 Umi-OCR 的凭证）
    TARGET_PREFIX = "UmiOCR_Cloud_"

    # -------------------------------------------------------------------------
    # 初始化
    # -------------------------------------------------------------------------

    def __init__(self):
        """初始化凭证管理器"""
        super().__init__()

        # 检查 Windows API 可用性
        self._check_win32cred()

    def _check_win32cred(self) -> None:
        """检查 win32cred 模块是否可用"""
        if not WIN32CRED_AVAILABLE:
            logging.warning("Windows Credential Manager API 不可用")
            logging.warning("将使用内存存储（不安全，仅供测试）")

        # 内存存储（备用方案）
        self._memory_storage: Dict[str, Dict[str, str]] = {}

    # -------------------------------------------------------------------------
    # 凭证管理接口
    # -------------------------------------------------------------------------

    def save(self, provider: str, credentials: Dict[str, str]) -> None:
        """
        保存凭证到 Windows Credential Manager

        Args:
            provider: 提供商标识（'baidu', 'tencent', 'aliyun'）
            credentials: 凭证字典
                           百度: {'api_key': '...', 'secret_key': '...'}
                           腾讯: {'secret_id': '...', 'secret_key': '...'}
                           阿里: {'access_key_id': '...', 'access_key_secret': '...'}

        Raises:
            CredentialWriteError: 凭证写入失败
        """
        target_name = self._get_target_name(provider)

        try:
            if WIN32CRED_AVAILABLE:
                # 将凭证字典转换为字符串
                credential_blob = self._serialize_credentials(credentials)

                # 构建凭证对象
                cred = {
                    "Type": CRED_TYPE_GENERIC,
                    "TargetName": target_name,
                    "CredentialBlob": credential_blob.encode('utf-8'),
                    "Persist": CRED_PERSIST_ENTERPRISE
                }

                # 写入凭证
                win32cred.CredWrite(cred)

                logging.info(f"凭证已保存: {provider}")
            else:
                # 内存存储（备用方案）
                self._memory_storage[provider] = credentials.copy()
                logging.warning(f"凭证已保存到内存（不安全）: {provider}")

            # 发送信号
            self.credentials_changed.emit(provider, 'saved')

        except Exception as e:
            logging.error(f"凭证保存失败: {provider}, {e}", exc_info=True)
            raise CredentialWriteError(f"无法保存凭证: {str(e)}")

    def load(self, provider: str) -> Optional[Dict[str, str]]:
        """
        从 Windows Credential Manager 加载凭证

        Args:
            provider: 提供商标识

        Returns:
            Optional[Dict[str, str]]: 凭证字典（未找到返回 None）
        """
        target_name = self._get_target_name(provider)

        try:
            if WIN32CRED_AVAILABLE:
                # 读取凭证
                cred = win32cred.CredRead(
                    Type=CRED_TYPE_GENERIC,
                    TargetName=target_name
                )

                if cred and cred.get('CredentialBlob'):
                    # 反序列化凭证
                    credential_blob = cred['CredentialBlob'].decode('utf-8')
                    credentials = self._deserialize_credentials(credential_blob)

                    logging.info(f"凭证已加载: {provider}")
                    return credentials
                else:
                    logging.warning(f"凭证未找到: {provider}")
                    return None
            else:
                # 从内存存储加载
                return self._memory_storage.get(provider)

        except Exception as e:
            logging.error(f"凭证加载失败: {provider}, {e}", exc_info=True)
            raise CredentialReadError(f"无法加载凭证: {str(e)}")

    def delete(self, provider: str) -> None:
        """
        从 Windows Credential Manager 删除凭证

        Args:
            provider: 提供商标识

        Raises:
            CredentialWriteError: 凭证删除失败
        """
        target_name = self._get_target_name(provider)

        try:
            if WIN32CRED_AVAILABLE:
                # 删除凭证
                result = win32cred.CredDelete(
                    Type=CRED_TYPE_GENERIC,
                    TargetName=target_name
                )

                if result:
                    logging.info(f"凭证已删除: {provider}")
                    self.credentials_changed.emit(provider, 'deleted')
                else:
                    logging.warning(f"凭证未找到，无法删除: {provider}")
            else:
                # 从内存存储删除
                if provider in self._memory_storage:
                    del self._memory_storage[provider]
                    logging.warning(f"凭证已从内存删除: {provider}")

        except Exception as e:
            logging.error(f"凭证删除失败: {provider}, {e}", exc_info=True)
            raise CredentialWriteError(f"无法删除凭证: {str(e)}")

    def exists(self, provider: str) -> bool:
        """
        检查凭证是否存在

        Args:
            provider: 提供商标识

        Returns:
            bool: 凭证是否存在
        """
        try:
            credentials = self.load(provider)
            return credentials is not None
        except CredentialError:
            return False

    def list_providers(self) -> List[str]:
        """
        列出所有已配置的提供商

        Returns:
            List[str]: 提供商列表
        """
        providers = []

        try:
            if WIN32CRED_AVAILABLE:
                # 枚举所有凭证
                count = win32cred.CredEnumerate(
                    Filter=self.TARGET_PREFIX,
                    Flags=0
                )

                for i in range(count):
                    cred = win32cred.CredRead(
                        Type=CRED_TYPE_GENERIC,
                        TargetName=f"{self.TARGET_PREFIX}{i}"
                    )
                    if cred:
                        # 从目标名称提取提供商标识
                        target_name = cred.get('TargetName', '')
                        if target_name.startswith(self.TARGET_PREFIX):
                            provider = target_name[len(self.TARGET_PREFIX):]
                            providers.append(provider)
            else:
                # 从内存存储列表
                providers = list(self._memory_storage.keys())

        except Exception as e:
            logging.error(f"枚举凭证失败: {e}", exc_info=True)

        return providers

    def clear_all(self) -> None:
        """
        清除所有 Umi-OCR 凭证

        警告：此操作将删除所有云 OCR 的 API 密钥
        """
        providers = self.list_providers()
        for provider in providers:
            try:
                self.delete(provider)
            except Exception as e:
                logging.error(f"清除凭证失败: {provider}, {e}", exc_info=True)

        logging.info(f"已清除 {len(providers)} 个凭证")

    # -------------------------------------------------------------------------
    # 辅助方法
    # -------------------------------------------------------------------------

    def _get_target_name(self, provider: str) -> str:
        """
        生成目标名称

        Args:
            provider: 提供商标识

        Returns:
            str: 目标名称（如 "UmiOCR_Cloud_baidu"）
        """
        return f"{self.TARGET_PREFIX}{provider}"

    def _serialize_credentials(self, credentials: Dict[str, str]) -> str:
        """
        序列化凭证为字符串

        使用 JSON 格式，支持跨平台兼容

        Args:
            credentials: 凭证字典

        Returns:
            str: 序列化后的字符串
        """
        import json
        return json.dumps(credentials, ensure_ascii=False)

    def _deserialize_credentials(self, data: str) -> Dict[str, str]:
        """
        从字符串反序列化凭证

        Args:
            data: 序列化字符串

        Returns:
            Dict[str, str]: 凭证字典
        """
        import json
        return json.loads(data)

    def validate_credentials(self, provider: str, credentials: Dict[str, str]) -> List[str]:
        """
        验证凭证格式和完整性

        Args:
            provider: 提供商标识
            credentials: 凭证字典

        Returns:
            List[str]: 错误信息列表（空表示无错误）
        """
        errors = []

        # 验证必填字段
        required_fields = self._get_required_fields(provider)
        for field in required_fields:
            if field not in credentials or not credentials[field]:
                errors.append(f"缺少必要字段: {field}")

        # 验证字段格式
        if 'api_key' in credentials:
            api_key = credentials['api_key']
            if len(api_key) < 10:
                errors.append("API Key 长度过短（至少10个字符）")

        if 'secret_key' in credentials:
            secret_key = credentials['secret_key']
            if len(secret_key) < 10:
                errors.append("Secret Key 长度过短（至少10个字符）")

        if 'secret_id' in credentials:
            secret_id = credentials['secret_id']
            if len(secret_id) < 10:
                errors.append("SecretId 长度过短（至少10个字符）")

        if 'access_key_id' in credentials:
            access_key_id = credentials['access_key_id']
            if len(access_key_id) < 10:
                errors.append("AccessKeyId 长度过短（至少10个字符）")

        if 'access_key_secret' in credentials:
            access_key_secret = credentials['access_key_secret']
            if len(access_key_secret) < 10:
                errors.append("AccessKeySecret 长度过短（至少10个字符）")

        return errors

    def _get_required_fields(self, provider: str) -> List[str]:
        """
        获取提供商的必填字段

        Args:
            provider: 提供商标识

        Returns:
            List[str]: 必填字段列表
        """
        required_fields_map = {
            'baidu': ['api_key', 'secret_key'],
            'tencent': ['secret_id', 'secret_key'],
            'aliyun': ['access_key_id', 'access_key_secret']
        }

        return required_fields_map.get(provider, [])

    def test_connection(self, provider: str, test_func: Callable) -> bool:
        """
        测试凭证连接

        Args:
            provider: 提供商标识
            test_func: 测试函数（应发起真实的 API 请求）

        Returns:
            bool: 连接测试是否成功
        """
        try:
            # 调用测试函数
            result = test_func()
            if result:
                logging.info(f"凭证连接测试成功: {provider}")
                return True
            else:
                logging.warning(f"凭证连接测试失败: {provider}")
                return False

        except Exception as e:
            logging.error(f"凭证连接测试异常: {provider}, {e}", exc_info=True)
            return False

    @staticmethod
    def is_available() -> bool:
        """
        检查 Credential Manager 是否可用

        Returns:
            bool: Windows Credential Manager 是否可用
        """
        return WIN32CRED_AVAILABLE


# =============================================================================
# 日志记录器
# =============================================================================

logger = logging.getLogger(__name__)
