"""
同步引擎模块
管理 Notion、飞书和本地 Markdown 之间的双向同步
"""

import json
import os
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import logging

from .notion_client import NotionClient
from .feishu_client import FeishuClient
from .markdown_handler import MarkdownHandler

logger = logging.getLogger(__name__)


class SyncMapping:
    """同步映射管理"""
    
    def __init__(self, mapping_file: str = "sync_mapping.json"):
        """
        初始化映射管理器
        
        Args:
            mapping_file: 映射文件路径
        """
        self.mapping_file = mapping_file
        self.mappings = self._load_mappings()
    
    def _load_mappings(self) -> Dict[str, Any]:
        """加载映射关系"""
        if os.path.exists(self.mapping_file):
            try:
                with open(self.mapping_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error loading mapping file: {e}")
                return {}
        return {}
    
    def _save_mappings(self) -> None:
        """保存映射关系"""
        try:
            with open(self.mapping_file, 'w', encoding='utf-8') as f:
                json.dump(self.mappings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving mapping file: {e}")
    
    def add_mapping(self, notion_id: str, feishu_token: str, md_file: str = "") -> None:
        """
        添加映射关系
        
        Args:
            notion_id: Notion 页面 ID
            feishu_token: 飞书文档 token
            md_file: 本地 Markdown 文件路径
        """
        if notion_id not in self.mappings:
            self.mappings[notion_id] = {}
        
        self.mappings[notion_id]["feishu_token"] = feishu_token
        if md_file:
            self.mappings[notion_id]["md_file"] = md_file
        self.mappings[notion_id]["last_sync"] = datetime.now().isoformat()
        
        self._save_mappings()
        logger.info(f"Added mapping for Notion page {notion_id}")
    
    def get_mapping(self, notion_id: str) -> Optional[Dict[str, str]]:
        """
        获取映射关系
        
        Args:
            notion_id: Notion 页面 ID
            
        Returns:
            映射信息
        """
        return self.mappings.get(notion_id)
    
    def get_all_mappings(self) -> Dict[str, Any]:
        """获取所有映射关系"""
        return self.mappings
    
    def remove_mapping(self, notion_id: str) -> None:
        """
        移除映射关系
        
        Args:
            notion_id: Notion 页面 ID
        """
        if notion_id in self.mappings:
            del self.mappings[notion_id]
            self._save_mappings()
            logger.info(f"Removed mapping for Notion page {notion_id}")


class SyncEngine:
    """同步引擎"""
    
    def __init__(self, 
                 notion_api_key: str,
                 feishu_app_id: str,
                 feishu_app_secret: str,
                 markdown_dir: str = "./markdown_files",
                 mapping_file: str = "sync_mapping.json"):
        """
        初始化同步引擎
        
        Args:
            notion_api_key: Notion API 密钥
            feishu_app_id: 飞书应用 ID
            feishu_app_secret: 飞书应用密钥
            markdown_dir: Markdown 文件目录
            mapping_file: 映射文件路径
        """
        self.notion = NotionClient(notion_api_key)
        self.feishu = FeishuClient(feishu_app_id, feishu_app_secret)
        self.markdown = MarkdownHandler(markdown_dir)
        self.mapping = SyncMapping(mapping_file)
    
    def sync_notion_to_feishu(self, notion_page_id: str, 
                              feishu_folder_token: str = "",
                              create_md: bool = False) -> Tuple[str, str, str]:
        """
        同步 Notion 页面到飞书
        
        Args:
            notion_page_id: Notion 页面 ID
            feishu_folder_token: 飞书文件夹 token（可选）
            create_md: 是否同时创建本地 Markdown 文件
            
        Returns:
            (feishu_token, md_file, status_message)
        """
        try:
            logger.info(f"Starting sync from Notion page {notion_page_id} to Feishu")
            
            # 获取 Notion 页面内容
            page_title = self.notion.get_page_title(notion_page_id)
            page_markdown = self.notion.page_to_markdown(notion_page_id)
            
            # 检查是否已存在映射
            existing_mapping = self.mapping.get_mapping(notion_page_id)
            
            if existing_mapping and existing_mapping.get("feishu_token"):
                # 更新现有飞书文档
                feishu_token = existing_mapping["feishu_token"]
                self.feishu.update_document(feishu_token, page_markdown)
                logger.info(f"Updated existing Feishu document: {feishu_token}")
                status = f"Updated Feishu document: {feishu_token}"
            else:
                # 创建新的飞书文档
                doc_data = self.feishu.create_document(feishu_folder_token, page_title, page_markdown)
                # Feishu API may return 'objToken', 'token', or 'document_id'
                feishu_token = doc_data.get("objToken") or doc_data.get("token") or doc_data.get("document_id")
                logger.info(f"Created new Feishu document: {feishu_token}")
                status = f"Created new Feishu document: {feishu_token}"
            
            # 如果需要，创建本地 Markdown 文件
            md_file = ""
            if create_md:
                md_file = self.markdown.create_from_content(page_title, page_markdown)
                logger.info(f"Created Markdown file: {md_file}")
            
            # 更新映射
            self.mapping.add_mapping(notion_page_id, feishu_token, md_file)
            
            return feishu_token, md_file, status
        
        except Exception as e:
            logger.error(f"Error syncing Notion to Feishu: {e}")
            raise
    
    def sync_markdown_to_feishu(self, md_file: str, 
                                feishu_folder_token: str = "",
                                notion_page_id: str = "") -> Tuple[str, str]:
        """
        同步本地 Markdown 文件到飞书
        
        Args:
            md_file: Markdown 文件路径
            feishu_folder_token: 飞书文件夹 token（可选）
            notion_page_id: 关联的 Notion 页面 ID（可选）
            
        Returns:
            (feishu_token, status_message)
        """
        try:
            logger.info(f"Starting sync from Markdown file {md_file} to Feishu")
            
            # 读取 Markdown 文件
            content = self.markdown.read_file(md_file)
            
            # 从文件名提取标题
            title = os.path.splitext(os.path.basename(md_file))[0]
            
            # 创建飞书文档
            doc_data = self.feishu.create_document(feishu_folder_token, title, content)
            # Feishu API may return 'objToken', 'token', or 'document_id'
            feishu_token = doc_data.get("objToken") or doc_data.get("token") or doc_data.get("document_id")
            
            logger.info(f"Created Feishu document from Markdown: {feishu_token}")
            
            # 如果提供了 Notion 页面 ID，更新映射
            if notion_page_id:
                self.mapping.add_mapping(notion_page_id, feishu_token, md_file)
            
            status = f"Created Feishu document from Markdown: {feishu_token}"
            return feishu_token, status
        
        except Exception as e:
            logger.error(f"Error syncing Markdown to Feishu: {e}")
            raise
    
    def sync_feishu_to_markdown(self, feishu_token: str, 
                                md_file: str = "",
                                notion_page_id: str = "") -> Tuple[str, str]:
        """
        同步飞书文档到本地 Markdown
        
        Args:
            feishu_token: 飞书文档 token
            md_file: 本地 Markdown 文件路径（如果为空则自动生成）
            notion_page_id: 关联的 Notion 页面 ID（可选）
            
        Returns:
            (md_file, status_message)
        """
        try:
            logger.info(f"Starting sync from Feishu document {feishu_token} to Markdown")
            
            # 获取飞书文档内容
            content = self.feishu.get_document_content(feishu_token)
            
            # 如果没有提供文件路径，自动生成
            if not md_file:
                doc_info = self.feishu.get_document(feishu_token)
                title = doc_info.get("title", "untitled")
                md_file = self.markdown.create_from_content(title, content)
            else:
                # 写入到指定文件
                self.markdown.write_file(md_file, content)
            
            logger.info(f"Created/Updated Markdown file: {md_file}")
            
            # 如果提供了 Notion 页面 ID，更新映射
            if notion_page_id:
                self.mapping.add_mapping(notion_page_id, feishu_token, md_file)
            
            status = f"Synced to Markdown file: {md_file}"
            return md_file, status
        
        except Exception as e:
            logger.error(f"Error syncing Feishu to Markdown: {e}")
            raise
    
    def sync_feishu_to_notion(self, feishu_token: str, 
                              notion_page_id: str) -> str:
        """
        同步飞书文档到 Notion 页面
        
        Args:
            feishu_token: 飞书文档 token
            notion_page_id: Notion 页面 ID
            
        Returns:
            状态信息
        """
        try:
            logger.info(f"Starting sync from Feishu document {feishu_token} to Notion page {notion_page_id}")
            
            # 获取飞书文档内容
            content = self.feishu.get_document_content(feishu_token)
            
            # 将 Markdown 转换为 Notion 块
            from .notion_client import markdown_to_notion_blocks
            blocks = markdown_to_notion_blocks(content)
            
            # 追加到 Notion 页面
            self.notion.append_blocks(notion_page_id, blocks)
            
            logger.info(f"Updated Notion page {notion_page_id} from Feishu")
            status = f"Updated Notion page from Feishu document"
            
            return status
        
        except Exception as e:
            logger.error(f"Error syncing Feishu to Notion: {e}")
            raise
    
    def sync_markdown_to_notion(self, md_file: str, 
                                notion_page_id: str) -> str:
        """
        同步本地 Markdown 文件到 Notion 页面
        
        Args:
            md_file: Markdown 文件路径
            notion_page_id: Notion 页面 ID
            
        Returns:
            状态信息
        """
        try:
            logger.info(f"Starting sync from Markdown file {md_file} to Notion page {notion_page_id}")
            
            # 读取 Markdown 文件
            content = self.markdown.read_file(md_file)
            
            # 将 Markdown 转换为 Notion 块
            from .notion_client import markdown_to_notion_blocks
            blocks = markdown_to_notion_blocks(content)
            
            # 追加到 Notion 页面
            self.notion.append_blocks(notion_page_id, blocks)
            
            logger.info(f"Updated Notion page {notion_page_id} from Markdown")
            status = f"Updated Notion page from Markdown file"
            
            return status
        
        except Exception as e:
            logger.error(f"Error syncing Markdown to Notion: {e}")
            raise
    
    def get_sync_status(self, notion_page_id: str) -> Dict[str, Any]:
        """
        获取同步状态
        
        Args:
            notion_page_id: Notion 页面 ID
            
        Returns:
            同步状态信息
        """
        mapping = self.mapping.get_mapping(notion_page_id)
        
        if not mapping:
            return {
                "status": "not_synced",
                "message": "This Notion page has not been synced yet"
            }
        
        return {
            "status": "synced",
            "feishu_token": mapping.get("feishu_token"),
            "md_file": mapping.get("md_file"),
            "last_sync": mapping.get("last_sync")
        }
