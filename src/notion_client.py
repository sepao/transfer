"""
Notion API 集成模块
用于读取 Notion 页面内容并转换为 Markdown 格式
"""

import requests
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import re

logger = logging.getLogger(__name__)


def normalize_notion_id(page_id: str) -> str:
    """
    将 Notion 页面 ID 转换为标准 UUID 格式
    
    Notion 页面 ID 可能有两种格式：
    - 无连字符：2ef23f59ade080429292ef494b71833a（32 个字符）
    - 有连字符：2ef23f59-ade0-8042-9292-ef494b71833a（36 个字符）
    
    此函数将无连字符的格式转换为有连字符的格式
    
    Args:
        page_id: Notion 页面 ID
        
    Returns:
        标准格式的 UUID
    """
    # 移除所有连字符
    clean_id = page_id.replace("-", "")
    
    # 检查是否是有效的 32 字符十六进制字符串 (case-insensitive)
    if len(clean_id) != 32 or not re.match(r'^[a-fA-F0-9]{32}$', clean_id):
        # 如果不是有效的格式，直接返回原始 ID（可能已经是正确格式）
        return page_id
    
    # 转换为标准 UUID 格式：8-4-4-4-12
    formatted_id = f"{clean_id[0:8]}-{clean_id[8:12]}-{clean_id[12:16]}-{clean_id[16:20]}-{clean_id[20:32]}"
    logger.info(f"Normalized Notion ID from {page_id} to {formatted_id}")
    return formatted_id


class NotionClient:
    """Notion API 客户端"""
    
    def __init__(self, api_key: str):
        """
        初始化 Notion 客户端
        
        Args:
            api_key: Notion API 密钥
        """
        self.api_key = api_key
        self.base_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }
    
    def get_page(self, page_id: str) -> Dict[str, Any]:
        """
        获取页面信息
        
        Args:
            page_id: 页面 ID
            
        Returns:
            页面对象
        """
        # 规范化页面 ID 格式
        page_id = normalize_notion_id(page_id)
        url = f"{self.base_url}/pages/{page_id}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def get_page_title(self, page_id: str) -> str:
        """
        获取页面标题
        
        Args:
            page_id: 页面 ID
            
        Returns:
            页面标题
        """
        page = self.get_page(page_id)
        
        # 尝试从 properties 中获取标题
        properties = page.get("properties", {})
        for prop_name, prop_value in properties.items():
            if prop_value.get("type") == "title":
                title_list = prop_value.get("title", [])
                if title_list:
                    return "".join([t.get("plain_text", "") for t in title_list])
        
        return "Untitled"
    
    def get_block_children(self, block_id: str, start_cursor: Optional[str] = None) -> Dict[str, Any]:
        """
        获取块的子块
        
        Args:
            block_id: 块 ID（可以是页面 ID）
            start_cursor: 分页游标
            
        Returns:
            包含子块的响应
        """
        # 规范化块 ID 格式
        block_id = normalize_notion_id(block_id)
        url = f"{self.base_url}/blocks/{block_id}/children"
        params = {
            "page_size": 100
        }
        if start_cursor:
            params["start_cursor"] = start_cursor
        
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()
    
    def get_all_blocks(self, block_id: str) -> List[Dict[str, Any]]:
        """
        获取块的所有子块（处理分页）
        
        Args:
            block_id: 块 ID
            
        Returns:
            所有子块列表
        """
        all_blocks = []
        start_cursor = None
        
        while True:
            response = self.get_block_children(block_id, start_cursor)
            all_blocks.extend(response.get("results", []))
            
            if not response.get("has_more"):
                break
            
            start_cursor = response.get("next_cursor")
        
        return all_blocks
    
    def block_to_markdown(self, block: Dict[str, Any], indent: int = 0) -> str:
        """
        将单个块转换为 Markdown
        
        Args:
            block: 块对象
            indent: 缩进级别
            
        Returns:
            Markdown 字符串
        """
        block_type = block.get("type")
        block_data = block.get(block_type, {})
        markdown = ""
        indent_str = "  " * indent
        
        try:
            if block_type == "paragraph":
                text = self._extract_rich_text(block_data.get("rich_text", []))
                if text:
                    markdown = f"{indent_str}{text}\n"
            
            elif block_type == "heading_1":
                text = self._extract_rich_text(block_data.get("rich_text", []))
                markdown = f"# {text}\n"
            
            elif block_type == "heading_2":
                text = self._extract_rich_text(block_data.get("rich_text", []))
                markdown = f"## {text}\n"
            
            elif block_type == "heading_3":
                text = self._extract_rich_text(block_data.get("rich_text", []))
                markdown = f"### {text}\n"
            
            elif block_type == "bulleted_list_item":
                text = self._extract_rich_text(block_data.get("rich_text", []))
                markdown = f"{indent_str}- {text}\n"
            
            elif block_type == "numbered_list_item":
                text = self._extract_rich_text(block_data.get("rich_text", []))
                markdown = f"{indent_str}1. {text}\n"
            
            elif block_type == "to_do":
                text = self._extract_rich_text(block_data.get("rich_text", []))
                checked = "✓" if block_data.get("checked") else "☐"
                markdown = f"{indent_str}- [{checked}] {text}\n"
            
            elif block_type == "toggle":
                text = self._extract_rich_text(block_data.get("rich_text", []))
                markdown = f"{indent_str}> **{text}**\n"
            
            elif block_type == "quote":
                text = self._extract_rich_text(block_data.get("rich_text", []))
                markdown = f"{indent_str}> {text}\n"
            
            elif block_type == "code":
                text = self._extract_rich_text(block_data.get("rich_text", []))
                language = block_data.get("language", "")
                markdown = f"```{language}\n{text}\n```\n"
            
            elif block_type == "divider":
                markdown = "---\n"
            
            elif block_type == "image":
                image_data = block_data.get("file") or block_data.get("external", {})
                url = image_data.get("url", "")
                if url:
                    markdown = f"![image]({url})\n"
            
            elif block_type == "video":
                video_data = block_data.get("file") or block_data.get("external", {})
                url = video_data.get("url", "")
                if url:
                    markdown = f"[Video]({url})\n"
            
            elif block_type == "link_preview":
                url = block_data.get("url", "")
                if url:
                    markdown = f"[Link]({url})\n"
            
            elif block_type == "table":
                # 表格需要特殊处理，这里简化处理
                markdown = "[Table - 需要手动转换]\n"
            
            # 处理有子块的情况
            if block.get("has_children"):
                try:
                    children = self.get_all_blocks(block.get("id"))
                    for child in children:
                        child_md = self.block_to_markdown(child, indent + 1)
                        markdown += child_md
                except Exception as e:
                    logger.warning(f"Failed to get children for block {block.get('id')}: {e}")
        
        except Exception as e:
            logger.error(f"Error converting block to markdown: {e}")
        
        return markdown
    
    def _extract_rich_text(self, rich_text_list: List[Dict[str, Any]]) -> str:
        """
        从富文本列表中提取纯文本
        
        Args:
            rich_text_list: 富文本对象列表
            
        Returns:
            提取的文本
        """
        text_parts = []
        
        for text_obj in rich_text_list:
            plain_text = text_obj.get("plain_text", "")
            
            # 应用格式
            if text_obj.get("annotations", {}).get("bold"):
                plain_text = f"**{plain_text}**"
            if text_obj.get("annotations", {}).get("italic"):
                plain_text = f"*{plain_text}*"
            if text_obj.get("annotations", {}).get("strikethrough"):
                plain_text = f"~~{plain_text}~~"
            if text_obj.get("annotations", {}).get("code"):
                plain_text = f"`{plain_text}`"
            
            # 处理链接
            href = text_obj.get("href")
            if href:
                plain_text = f"[{plain_text}]({href})"
            
            text_parts.append(plain_text)
        
        return "".join(text_parts)
    
    def page_to_markdown(self, page_id: str) -> str:
        """
        将整个页面转换为 Markdown
        
        Args:
            page_id: 页面 ID
            
        Returns:
            Markdown 字符串
        """
        try:
            # 获取页面标题
            title = self.get_page_title(page_id)
            markdown = f"# {title}\n\n"
            
            # 获取所有块
            blocks = self.get_all_blocks(page_id)
            
            # 转换每个块
            for block in blocks:
                block_md = self.block_to_markdown(block)
                markdown += block_md
            
            return markdown
        
        except Exception as e:
            logger.error(f"Error converting page to markdown: {e}")
            raise
    
    def create_page(self, parent_id: str, title: str, content: str) -> str:
        """
        创建新页面
        
        Args:
            parent_id: 父块/数据库 ID
            title: 页面标题
            content: 页面内容（Markdown）
            
        Returns:
            新页面的 ID
        """
        # 这是一个简化的实现，实际创建需要根据 Notion 的块结构来构建
        url = f"{self.base_url}/pages"
        
        data = {
            "parent": {
                "type": "page_id",
                "page_id": parent_id
            },
            "properties": {
                "title": {
                    "title": [
                        {
                            "text": {
                                "content": title
                            }
                        }
                    ]
                }
            }
        }
        
        response = requests.post(url, headers=self.headers, json=data)
        response.raise_for_status()
        result = response.json()
        
        return result.get("id")
    
    def append_blocks(self, page_id: str, blocks: List[Dict[str, Any]]) -> None:
        """
        向页面添加块
        
        Args:
            page_id: 页面 ID
            blocks: 块列表
        """
        url = f"{self.base_url}/blocks/{page_id}/children"
        
        data = {
            "children": blocks
        }
        
        response = requests.patch(url, headers=self.headers, json=data)
        response.raise_for_status()


def markdown_to_notion_blocks(markdown: str) -> List[Dict[str, Any]]:
    """
    将 Markdown 转换为 Notion 块
    
    Args:
        markdown: Markdown 字符串
        
    Returns:
        Notion 块列表
    """
    blocks = []
    lines = markdown.split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        if not line.strip():
            i += 1
            continue
        
        # 标题
        if line.startswith("# "):
            blocks.append({
                "object": "block",
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [{"type": "text", "text": {"content": line[2:]}}]
                }
            })
        elif line.startswith("## "):
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": line[3:]}}]
                }
            })
        elif line.startswith("### "):
            blocks.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{"type": "text", "text": {"content": line[4:]}}]
                }
            })
        # 列表项
        elif line.startswith("- "):
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": line[2:]}}]
                }
            })
        elif line.startswith("1. "):
            blocks.append({
                "object": "block",
                "type": "numbered_list_item",
                "numbered_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": line[3:]}}]
                }
            })
        # 段落
        else:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": line}}]
                }
            })
        
        i += 1
    
    return blocks
