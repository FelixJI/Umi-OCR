#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试模型下载功能
"""

import sys
import logging
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from src.services.ocr.models.model_manager_core import get_model_manager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_model_download():
    """测试模型下载功能"""
    logger.info("开始测试模型下载功能")
    
    # 获取模型管理器
    model_manager = get_model_manager()
    
    # 测试下载一个简单的模型
    test_model = "ppocrv5_mobile_det"
    
    logger.info(f"测试下载模型: {test_model}")
    
    # 下载模型
    success = model_manager.download_model(test_model)
    
    if success:
        logger.info(f"模型下载成功: {test_model}")
    else:
        logger.error(f"模型下载失败: {test_model}")
    
    # 获取模型信息
    model_info = model_manager.get_model_info(test_model)
    if model_info:
        logger.info(f"模型信息: {model_info}")
    else:
        logger.error(f"未找到模型信息: {test_model}")
    
    logger.info("测试完成")

if __name__ == "__main__":
    test_model_download()
