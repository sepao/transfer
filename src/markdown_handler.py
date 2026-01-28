"""
本地 Markdown 文件处理模块
用于读写本地 MD 文件
"""

import os
from typing import Optional
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class MarkdownHandler:
    """Markdown 文件处理器"""
    
    def __init__(self, base_dir: str = "./markdown_files"):
        """
        初始化 Markdown 处理器
        
        Args:
            base_dir: Markdown 文件的基础目录
        """
        self.base_dir = base_dir
        self._ensure_dir_exists(base_dir)
    
    def _ensure_dir_exists(self, directory: str) -> None:
        """
        确保目录存在
        
        Args:
            directory: 目录路径
        """
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    def read_file(self, file_path: str) -> str:
        """
        读取 Markdown 文件
        
        Args:
            file_path: 文件路径（相对于 base_dir 或绝对路径）
            
        Returns:
            文件内容
        """
        # 如果是相对路径，则相对于 base_dir
        if not os.path.isabs(file_path):
            file_path = os.path.join(self.base_dir, file_path)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            raise
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            raise
    
    def write_file(self, file_path: str, content: str) -> None:
        """
        写入 Markdown 文件
        
        Args:
            file_path: 文件路径（相对于 base_dir 或绝对路径）
            content: 文件内容
        """
        # 如果是相对路径，则相对于 base_dir
        if not os.path.isabs(file_path):
            file_path = os.path.join(self.base_dir, file_path)
        
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"Successfully wrote to file: {file_path}")
        except Exception as e:
            logger.error(f"Error writing to file {file_path}: {e}")
            raise
    
    def append_file(self, file_path: str, content: str) -> None:
        """
        追加内容到 Markdown 文件
        
        Args:
            file_path: 文件路径
            content: 要追加的内容
        """
        # 如果是相对路径，则相对于 base_dir
        if not os.path.isabs(file_path):
            file_path = os.path.join(self.base_dir, file_path)
        
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"Successfully appended to file: {file_path}")
        except Exception as e:
            logger.error(f"Error appending to file {file_path}: {e}")
            raise
    
    def file_exists(self, file_path: str) -> bool:
        """
        检查文件是否存在
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件是否存在
        """
        if not os.path.isabs(file_path):
            file_path = os.path.join(self.base_dir, file_path)
        
        return os.path.exists(file_path)
    
    def get_file_size(self, file_path: str) -> int:
        """
        获取文件大小
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件大小（字节）
        """
        if not os.path.isabs(file_path):
            file_path = os.path.join(self.base_dir, file_path)
        
        try:
            return os.path.getsize(file_path)
        except Exception as e:
            logger.error(f"Error getting file size: {e}")
            return 0
    
    def get_file_modification_time(self, file_path: str) -> float:
        """
        获取文件修改时间
        
        Args:
            file_path: 文件路径
            
        Returns:
            修改时间戳
        """
        if not os.path.isabs(file_path):
            file_path = os.path.join(self.base_dir, file_path)
        
        try:
            return os.path.getmtime(file_path)
        except Exception as e:
            logger.error(f"Error getting file modification time: {e}")
            return 0
    
    def list_files(self, directory: str = "", extension: str = ".md") -> list:
        """
        列出目录中的文件
        
        Args:
            directory: 子目录（相对于 base_dir）
            extension: 文件扩展名
            
        Returns:
            文件列表
        """
        if directory:
            search_dir = os.path.join(self.base_dir, directory)
        else:
            search_dir = self.base_dir
        
        try:
            files = []
            for root, dirs, filenames in os.walk(search_dir):
                for filename in filenames:
                    if filename.endswith(extension):
                        full_path = os.path.join(root, filename)
                        relative_path = os.path.relpath(full_path, self.base_dir)
                        files.append(relative_path)
            
            return files
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return []
    
    def delete_file(self, file_path: str) -> None:
        """
        删除文件
        
        Args:
            file_path: 文件路径
        """
        if not os.path.isabs(file_path):
            file_path = os.path.join(self.base_dir, file_path)
        
        try:
            os.remove(file_path)
            logger.info(f"Successfully deleted file: {file_path}")
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            raise
    
    def get_full_path(self, file_path: str) -> str:
        """
        获取文件的完整路径
        
        Args:
            file_path: 文件路径（相对或绝对）
            
        Returns:
            完整路径
        """
        if not os.path.isabs(file_path):
            return os.path.join(self.base_dir, file_path)
        return file_path
    
    def normalize_filename(self, filename: str) -> str:
        """
        规范化文件名
        
        Args:
            filename: 原始文件名
            
        Returns:
            规范化后的文件名
        """
        # 移除不安全的字符
        unsafe_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        for char in unsafe_chars:
            filename = filename.replace(char, '_')
        
        # 确保有 .md 扩展名
        if not filename.endswith('.md'):
            filename += '.md'
        
        return filename
    
    def create_from_content(self, title: str, content: str, subdirectory: str = "") -> str:
        """
        从内容创建新的 Markdown 文件
        
        Args:
            title: 文件标题（将作为文件名）
            content: 文件内容
            subdirectory: 子目录
            
        Returns:
            创建的文件的相对路径
        """
        # 规范化文件名
        filename = self.normalize_filename(title)
        
        # 构建文件路径
        if subdirectory:
            file_path = os.path.join(subdirectory, filename)
        else:
            file_path = filename
        
        # 写入文件
        self.write_file(file_path, content)
        
        return file_path
