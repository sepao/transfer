"""
配置管理模块
"""

import json
import os
from typing import Any, Optional


class Config:
    """配置管理器"""
    
    def __init__(self, config_file: str = "config.json"):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = config_file
        self.config = self._load_config()
    
    def _load_config(self) -> dict:
        """加载配置文件"""
        if not os.path.exists(self.config_file):
            raise FileNotFoundError(f"Config file not found: {self.config_file}")
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in config file: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键
            default: 默认值
            
        Returns:
            配置值
        """
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        设置配置值
        
        Args:
            key: 配置键
            value: 配置值
        """
        self.config[key] = value
        self._save_config()
    
    def _save_config(self) -> None:
        """保存配置文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise RuntimeError(f"Failed to save config file: {e}")
    
    def validate(self) -> bool:
        """
        验证配置是否有效
        
        Returns:
            配置是否有效
        """
        required_keys = [
            "notion_api_key",
            "feishu_app_id",
            "feishu_app_secret"
        ]
        
        for key in required_keys:
            if not self.config.get(key):
                raise ValueError(f"Missing required config: {key}")
        
        return True
