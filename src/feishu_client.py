"""
飞书 Lark API 集成模块
用于创建、更新和读取飞书文档
"""

import requests
import json
from typing import Dict, List, Optional, Any
import logging
import time
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading

logger = logging.getLogger(__name__)


class FeishuClient:
    """飞书 API 客户端"""

    def __init__(self, app_id: str, app_secret: str, user_access_token: str = None):
        """
        初始化飞书客户端

        Args:
            app_id: 应用 ID
            app_secret: 应用密钥
            user_access_token: 用户访问令牌（可选，用于以用户身份操作）
        """
        self.app_id = app_id
        self.app_secret = app_secret
        # Use consistent API endpoints (feishu.cn for China users)
        self.base_url = "https://open.feishu.cn/open-apis"
        self.auth_url = "https://open.feishu.cn/open-apis"
        self.access_token = None
        self.token_expire_time = 0
        # User OAuth token
        self.user_access_token = user_access_token
        self.user_token_expire_time = 0
        self.refresh_token = None
    
    def _get_tenant_access_token(self) -> str:
        """
        获取租户级别的 access token
        
        Returns:
            access_token
        """
        # 如果 token 还未过期，直接返回
        if self.access_token and time.time() < self.token_expire_time:
            return self.access_token
        
        url = f"{self.auth_url}/auth/v3/tenant_access_token/internal"
        data = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        
        try:
            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            if result.get("code") != 0:
                raise Exception(f"Failed to get access token: {result.get('msg')}")
            
            self.access_token = result.get("tenant_access_token")
            # token 有效期通常是 2 小时，这里设置为 1.9 小时以确保安全
            expire_time = result.get("expire", 7200)
            self.token_expire_time = time.time() + (expire_time - 300)  # 提前 5 分钟刷新
            
            logger.info(f"Successfully obtained access token, expires in {expire_time} seconds")
            return self.access_token
        
        except Exception as e:
            logger.error(f"Error getting access token: {e}")
            raise
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头（优先使用用户令牌）"""
        # 优先使用用户访问令牌
        if self.user_access_token and time.time() < self.user_token_expire_time:
            token = self.user_access_token
        else:
            token = self._get_tenant_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8"
        }

    def authorize_user(self, redirect_uri: str = "http://localhost:8080/callback") -> Dict[str, Any]:
        """
        启动 OAuth 用户授权流程

        Args:
            redirect_uri: 回调 URL

        Returns:
            包含 user_access_token 和 refresh_token 的字典
        """
        # 授权码存储
        auth_code = {"code": None}

        # 创建简单的 HTTP 服务器来接收回调
        class CallbackHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                query = parse_qs(urlparse(self.path).query)
                if "code" in query:
                    auth_code["code"] = query["code"][0]
                    self.send_response(200)
                    self.send_header("Content-type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write("✅ 授权成功！请返回终端继续操作。<br>Authorization successful! You can close this window.".encode())
                else:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write("❌ 授权失败".encode())

            def log_message(self, format, *args):
                pass  # 禁用日志输出

        # 解析 redirect_uri 获取端口
        parsed = urlparse(redirect_uri)
        port = parsed.port or 8080

        # 构建授权 URL
        auth_url = (
            f"https://open.feishu.cn/open-apis/authen/v1/authorize"
            f"?app_id={self.app_id}"
            f"&redirect_uri={redirect_uri}"
            f"&scope=docx:document drive:drive"
        )

        logger.info(f"Opening browser for authorization...")
        print(f"\n🔐 请在浏览器中完成授权...")
        print(f"如果浏览器没有自动打开，请手动访问：\n{auth_url}\n")

        # 启动服务器
        server = HTTPServer(("localhost", port), CallbackHandler)
        server.timeout = 120  # 2 分钟超时

        # 打开浏览器
        webbrowser.open(auth_url)

        # 等待回调
        while auth_code["code"] is None:
            server.handle_request()

        server.server_close()

        if not auth_code["code"]:
            raise Exception("Authorization failed: no code received")

        # 用授权码换取用户访问令牌
        return self._exchange_code_for_token(auth_code["code"])

    def _exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """
        用授权码换取用户访问令牌

        Args:
            code: 授权码

        Returns:
            包含 token 信息的字典
        """
        url = f"{self.auth_url}/authen/v1/oidc/access_token"

        # 需要先获取 app_access_token
        app_token = self._get_tenant_access_token()

        headers = {
            "Authorization": f"Bearer {app_token}",
            "Content-Type": "application/json; charset=utf-8"
        }

        data = {
            "grant_type": "authorization_code",
            "code": code
        }

        response = requests.post(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        result = response.json()

        if result.get("code") != 0:
            raise Exception(f"Failed to exchange code for token: {result.get('msg')}")

        token_data = result.get("data", {})
        self.user_access_token = token_data.get("access_token")
        self.refresh_token = token_data.get("refresh_token")
        expire_in = token_data.get("expires_in", 7200)
        self.user_token_expire_time = time.time() + expire_in - 300

        logger.info(f"Successfully obtained user access token, expires in {expire_in} seconds")
        print(f"✅ 用户授权成功！")

        return {
            "user_access_token": self.user_access_token,
            "refresh_token": self.refresh_token,
            "expires_in": expire_in
        }

    def set_user_token(self, user_access_token: str, refresh_token: str = None, expires_in: int = 7200):
        """
        设置用户访问令牌

        Args:
            user_access_token: 用户访问令牌
            refresh_token: 刷新令牌
            expires_in: 过期时间（秒）
        """
        self.user_access_token = user_access_token
        self.refresh_token = refresh_token
        self.user_token_expire_time = time.time() + expires_in - 300
        logger.info("User access token set successfully")
    
    def create_document(self, folder_token: str, title: str, content: str = "") -> Dict[str, Any]:
        """
        创建新文档 (使用 DocX API)

        Args:
            folder_token: 文件夹 token（如果为空，则在根目录创建）
            title: 文档标题
            content: 文档内容（Markdown 格式）

        Returns:
            包含 document_id, token, revision 等的字典
        """
        try:
            # 使用新版 DocX API 创建文档
            url = f"{self.base_url}/docx/v1/documents"
            headers = self._get_headers()

            payload = {
                "title": title,
            }
            if folder_token:
                payload["folder_token"] = folder_token

            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()

            if result.get("code") != 0:
                raise Exception(f"Failed to create document: {result.get('msg')}")

            doc_data = result.get("data", {}).get("document", {})
            document_id = doc_data.get("document_id")
            logger.info(f"Successfully created document: {document_id}")

            # 如果有内容，追加到文档
            if content and document_id:
                # 等待文档创建完成
                time.sleep(1)
                self._append_content_to_document(document_id, content)

            # Return with objToken for compatibility
            doc_data["objToken"] = document_id
            return doc_data

        except Exception as e:
            logger.error(f"Error creating document: {e}")
            raise

    def _append_content_to_document(self, document_id: str, content: str) -> None:
        """
        向文档追加内容

        Args:
            document_id: 文档 ID
            content: Markdown 格式的内容
        """
        try:
            headers = self._get_headers()

            # 将 Markdown 转换为 DocX blocks
            blocks = self._markdown_to_docx_blocks(content)

            if not blocks:
                return

            # Feishu API 限制每次最多 50 个 blocks，需要分批处理
            BATCH_SIZE = 50
            total_blocks = len(blocks)
            current_index = 0

            for i in range(0, total_blocks, BATCH_SIZE):
                batch = blocks[i:i + BATCH_SIZE]

                # 追加 blocks 到文档
                url = f"{self.base_url}/docx/v1/documents/{document_id}/blocks/{document_id}/children"

                payload = {
                    "children": batch,
                    "index": current_index
                }

                response = requests.post(url, headers=headers, json=payload, timeout=30)

                if response.status_code != 200:
                    logger.warning(f"Failed to append content batch (HTTP {response.status_code}): {response.text}")
                    return

                result = response.json()

                if result.get("code") != 0:
                    logger.warning(f"Failed to append content batch: {result.get('msg')}")
                    return

                # 更新索引位置
                current_index += len(batch)
                logger.info(f"Appended batch {i // BATCH_SIZE + 1} ({len(batch)} blocks) to document {document_id}")

            logger.info(f"Successfully appended all {total_blocks} blocks to document {document_id}")

        except Exception as e:
            logger.warning(f"Error appending content to document: {e}")
    
    def update_document(self, doc_token: str, content: str, title: str = "") -> None:
        """
        更新文档内容 (使用 DocX API)

        Args:
            doc_token: 文档 token
            content: 新的文档内容（Markdown 格式）
            title: 文档标题（可选）
        """
        try:
            headers = self._get_headers()

            # DocX API 不支持直接更新全部内容，需要先删除后追加
            # 这里简化处理：直接追加内容到文档末尾
            if content:
                self._append_content_to_document(doc_token, content)

            logger.info(f"Successfully updated document: {doc_token}")

        except Exception as e:
            logger.error(f"Error updating document: {e}")
            raise
    
    def get_document(self, doc_token: str) -> Dict[str, Any]:
        """
        获取文档信息 (使用 DocX API)

        Args:
            doc_token: 文档 token

        Returns:
            文档信息
        """
        try:
            url = f"{self.base_url}/docx/v1/documents/{doc_token}"
            headers = self._get_headers()

            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            result = response.json()

            if result.get("code") != 0:
                raise Exception(f"Failed to get document: {result.get('msg')}")

            doc_data = result.get("data", {}).get("document", {})
            logger.info(f"Successfully retrieved document: {doc_token}")

            return doc_data

        except Exception as e:
            logger.error(f"Error getting document: {e}")
            raise
    
    def get_document_content(self, doc_token: str) -> str:
        """
        获取文档内容（Markdown 格式）(使用 DocX API)

        Args:
            doc_token: 文档 token

        Returns:
            文档内容（Markdown 格式）
        """
        try:
            # 使用 DocX API 获取文档的所有 blocks
            url = f"{self.base_url}/docx/v1/documents/{doc_token}/blocks"
            headers = self._get_headers()

            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            result = response.json()

            if result.get("code") != 0:
                logger.warning(f"Get document content warning: {result.get('msg')}")
                return ""

            # 获取所有 blocks
            items = result.get("data", {}).get("items", [])

            # 将 DocX blocks 转换为 Markdown
            markdown = self._docx_blocks_to_markdown(items)

            logger.info(f"Successfully retrieved document content: {doc_token}")
            return markdown

        except Exception as e:
            logger.error(f"Error getting document content: {e}")
            return ""

    def _markdown_to_docx_blocks(self, markdown: str) -> List[Dict[str, Any]]:
        """
        将 Markdown 转换为 DocX blocks

        Args:
            markdown: Markdown 字符串

        Returns:
            DocX blocks 列表
        """
        blocks = []
        lines = markdown.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i]

            # 跳过空行
            if not line.strip():
                i += 1
                continue

            # 标题 1
            if line.startswith("# "):
                blocks.append({
                    "block_type": 3,  # heading1
                    "heading1": {
                        "elements": [{"text_run": {"content": line[2:]}}]
                    }
                })
            # 标题 2
            elif line.startswith("## "):
                blocks.append({
                    "block_type": 4,  # heading2
                    "heading2": {
                        "elements": [{"text_run": {"content": line[3:]}}]
                    }
                })
            # 标题 3
            elif line.startswith("### "):
                blocks.append({
                    "block_type": 5,  # heading3
                    "heading3": {
                        "elements": [{"text_run": {"content": line[4:]}}]
                    }
                })
            # 代码块
            elif line.startswith("```"):
                code_lines = []
                language = line[3:].strip() or "plaintext"
                i += 1
                while i < len(lines) and not lines[i].startswith("```"):
                    code_lines.append(lines[i])
                    i += 1
                blocks.append({
                    "block_type": 14,  # code
                    "code": {
                        "elements": [{"text_run": {"content": "\n".join(code_lines)}}],
                        "language": self._get_code_language_id(language)
                    }
                })
            # 无序列表
            elif line.startswith("- "):
                blocks.append({
                    "block_type": 12,  # bullet
                    "bullet": {
                        "elements": [{"text_run": {"content": line[2:]}}]
                    }
                })
            # 无序列表 (asterisk)
            elif line.startswith("* "):
                blocks.append({
                    "block_type": 12,  # bullet
                    "bullet": {
                        "elements": [{"text_run": {"content": line[2:]}}]
                    }
                })
            # 有序列表
            elif line.startswith("1. "):
                blocks.append({
                    "block_type": 13,  # ordered
                    "ordered": {
                        "elements": [{"text_run": {"content": line[3:]}}]
                    }
                })
            # 分割线
            elif line.strip() in ["---", "***", "___"]:
                blocks.append({
                    "block_type": 22,  # divider
                    "divider": {}
                })
            # 引用
            elif line.startswith("> "):
                blocks.append({
                    "block_type": 17,  # quote
                    "quote": {
                        "elements": [{"text_run": {"content": line[2:]}}]
                    }
                })
            # 段落
            else:
                blocks.append({
                    "block_type": 2,  # text
                    "text": {
                        "elements": [{"text_run": {"content": line}}]
                    }
                })

            i += 1

        return blocks

    def _get_code_language_id(self, language: str) -> int:
        """获取代码语言 ID"""
        language_map = {
            "plaintext": 1, "abap": 2, "ada": 3, "apache": 4, "apex": 5,
            "bash": 22, "shell": 22, "c": 6, "c++": 7, "cpp": 7,
            "c#": 8, "csharp": 8, "css": 9, "go": 18, "golang": 18,
            "html": 19, "java": 21, "javascript": 22, "js": 22,
            "json": 23, "kotlin": 24, "markdown": 27, "md": 27,
            "php": 30, "python": 33, "py": 33, "ruby": 35, "rb": 35,
            "rust": 36, "sql": 38, "swift": 39, "typescript": 40, "ts": 40,
            "xml": 42, "yaml": 43, "yml": 43
        }
        return language_map.get(language.lower(), 1)

    def _docx_blocks_to_markdown(self, blocks: List[Dict[str, Any]]) -> str:
        """
        将 DocX blocks 转换为 Markdown

        Args:
            blocks: DocX blocks 列表

        Returns:
            Markdown 字符串
        """
        markdown_lines = []

        for block in blocks:
            block_type = block.get("block_type")

            if block_type == 2:  # text/paragraph
                text_data = block.get("text", {})
                text = self._extract_docx_text(text_data.get("elements", []))
                if text:
                    markdown_lines.append(text)

            elif block_type == 3:  # heading1
                heading_data = block.get("heading1", {})
                text = self._extract_docx_text(heading_data.get("elements", []))
                markdown_lines.append(f"# {text}")

            elif block_type == 4:  # heading2
                heading_data = block.get("heading2", {})
                text = self._extract_docx_text(heading_data.get("elements", []))
                markdown_lines.append(f"## {text}")

            elif block_type == 5:  # heading3
                heading_data = block.get("heading3", {})
                text = self._extract_docx_text(heading_data.get("elements", []))
                markdown_lines.append(f"### {text}")

            elif block_type == 12:  # bullet
                bullet_data = block.get("bullet", {})
                text = self._extract_docx_text(bullet_data.get("elements", []))
                markdown_lines.append(f"- {text}")

            elif block_type == 13:  # ordered
                ordered_data = block.get("ordered", {})
                text = self._extract_docx_text(ordered_data.get("elements", []))
                markdown_lines.append(f"1. {text}")

            elif block_type == 14:  # code
                code_data = block.get("code", {})
                text = self._extract_docx_text(code_data.get("elements", []))
                language = self._get_code_language_name(code_data.get("language", 1))
                markdown_lines.append(f"```{language}\n{text}\n```")

            elif block_type == 17:  # quote
                quote_data = block.get("quote", {})
                text = self._extract_docx_text(quote_data.get("elements", []))
                markdown_lines.append(f"> {text}")

            elif block_type == 22:  # divider
                markdown_lines.append("---")

        return "\n".join(markdown_lines)

    def _extract_docx_text(self, elements: List[Dict[str, Any]]) -> str:
        """从 DocX elements 中提取文本"""
        text_parts = []
        for element in elements:
            text_run = element.get("text_run", {})
            content = text_run.get("content", "")
            if content:
                text_parts.append(content)
        return "".join(text_parts)

    def _get_code_language_name(self, language_id: int) -> str:
        """获取代码语言名称"""
        language_map = {
            1: "plaintext", 6: "c", 7: "cpp", 8: "csharp", 9: "css",
            18: "go", 19: "html", 21: "java", 22: "javascript",
            23: "json", 24: "kotlin", 27: "markdown", 30: "php",
            33: "python", 35: "ruby", 36: "rust", 38: "sql",
            39: "swift", 40: "typescript", 42: "xml", 43: "yaml"
        }
        return language_map.get(language_id, "plaintext")
    
    def _markdown_to_feishu_content(self, title: str, markdown: str) -> Dict[str, Any]:
        """
        将 Markdown 转换为飞书文档结构
        
        Args:
            title: 文档标题
            markdown: Markdown 字符串
            
        Returns:
            飞书文档结构
        """
        # 标题部分
        title_content = {
            "elements": [
                {
                    "type": "textRun",
                    "textRun": {
                        "text": title,
                        "style": {}
                    }
                }
            ]
        }
        
        # 正文部分
        blocks = self._markdown_to_blocks(markdown)
        
        body_content = {
            "blocks": blocks
        }
        
        return {
            "title": title_content,
            "body": body_content
        }
    
    def _markdown_to_blocks(self, markdown: str) -> List[Dict[str, Any]]:
        """
        将 Markdown 转换为飞书块
        
        Args:
            markdown: Markdown 字符串
            
        Returns:
            飞书块列表
        """
        blocks = []
        lines = markdown.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # 跳过空行
            if not line.strip():
                i += 1
                continue
            
            # 标题 1
            if line.startswith("# "):
                blocks.append(self._create_heading_block(line[2:], 1))
            # 标题 2
            elif line.startswith("## "):
                blocks.append(self._create_heading_block(line[3:], 2))
            # 标题 3
            elif line.startswith("### "):
                blocks.append(self._create_heading_block(line[4:], 3))
            # 代码块
            elif line.startswith("```"):
                code_lines = []
                language = line[3:].strip() or "plaintext"
                i += 1
                while i < len(lines) and not lines[i].startswith("```"):
                    code_lines.append(lines[i])
                    i += 1
                
                blocks.append(self._create_code_block("\n".join(code_lines), language))
            # 无序列表
            elif line.startswith("- "):
                blocks.append(self._create_list_block(line[2:], "bullet"))
            # 有序列表 (numbered list starts with "1. ")
            elif line.startswith("1. "):
                blocks.append(self._create_list_block(line[3:], "number"))
            # 无序列表 (bullet list with "* ")
            elif line.startswith("* "):
                blocks.append(self._create_list_block(line[2:], "bullet"))
            # 分割线
            elif line.strip() in ["---", "***", "___"]:
                blocks.append(self._create_divider_block())
            # 引用
            elif line.startswith("> "):
                blocks.append(self._create_quote_block(line[2:]))
            # 段落
            else:
                blocks.append(self._create_paragraph_block(line))
            
            i += 1
        
        return blocks
    
    def _create_paragraph_block(self, text: str) -> Dict[str, Any]:
        """创建段落块"""
        return {
            "type": "paragraph",
            "paragraph": {
                "elements": [
                    {
                        "type": "textRun",
                        "textRun": {
                            "text": text,
                            "style": {}
                        }
                    }
                ]
            }
        }
    
    def _create_heading_block(self, text: str, level: int) -> Dict[str, Any]:
        """创建标题块"""
        heading_types = {
            1: "heading1",
            2: "heading2",
            3: "heading3"
        }

        heading_type = heading_types.get(level, "heading1")

        return {
            "type": heading_type,
            heading_type: {
                "elements": [
                    {
                        "type": "textRun",
                        "textRun": {
                            "text": text,
                            "style": {}
                        }
                    }
                ]
            }
        }
    
    def _create_list_block(self, text: str, list_type: str) -> Dict[str, Any]:
        """创建列表块"""
        block_type = "bulletedListItem" if list_type == "bullet" else "numberedListItem"
        
        return {
            "type": block_type,
            block_type: {
                "elements": [
                    {
                        "type": "textRun",
                        "textRun": {
                            "text": text,
                            "style": {}
                        }
                    }
                ]
            }
        }
    
    def _create_code_block(self, code: str, language: str = "plaintext") -> Dict[str, Any]:
        """创建代码块"""
        return {
            "type": "code",
            "code": {
                "language": language,
                "body": {
                    "blocks": [
                        {
                            "type": "paragraph",
                            "paragraph": {
                                "elements": [
                                    {
                                        "type": "textRun",
                                        "textRun": {
                                            "text": code,
                                            "style": {}
                                        }
                                    }
                                ]
                            }
                        }
                    ]
                }
            }
        }
    
    def _create_quote_block(self, text: str) -> Dict[str, Any]:
        """创建引用块"""
        return {
            "type": "paragraph",
            "paragraph": {
                "elements": [
                    {
                        "type": "textRun",
                        "textRun": {
                            "text": text,
                            "style": {}
                        }
                    }
                ],
                "style": {
                    "quote": True
                }
            }
        }
    
    def _create_divider_block(self) -> Dict[str, Any]:
        """创建分割线块"""
        return {
            "type": "divider",
            "divider": {}
        }
    
    def _feishu_content_to_markdown(self, doc_content: Dict[str, Any]) -> str:
        """
        将飞书文档结构转换为 Markdown
        
        Args:
            doc_content: 飞书文档内容
            
        Returns:
            Markdown 字符串
        """
        markdown_lines = []
        
        # 处理标题
        title = doc_content.get("title", {})
        if title:
            title_text = self._extract_text_from_elements(title.get("elements", []))
            if title_text:
                markdown_lines.append(f"# {title_text}\n")
        
        # 处理正文
        body = doc_content.get("body", {})
        blocks = body.get("blocks", [])
        
        for block in blocks:
            markdown_lines.append(self._block_to_markdown(block))
        
        return "\n".join(markdown_lines)
    
    def _block_to_markdown(self, block: Dict[str, Any]) -> str:
        """
        将单个块转换为 Markdown
        
        Args:
            block: 飞书块
            
        Returns:
            Markdown 字符串
        """
        block_type = block.get("type")
        
        if block_type == "paragraph":
            paragraph = block.get("paragraph", {})
            text = self._extract_text_from_elements(paragraph.get("elements", []))
            style = paragraph.get("style", {})
            
            if style.get("quote"):
                return f"> {text}"
            elif style.get("headingLevel"):
                level = style.get("headingLevel", 1)
                return f"{'#' * level} {text}"
            else:
                return text
        
        elif block_type == "heading1":
            heading = block.get("heading1", {})
            text = self._extract_text_from_elements(heading.get("elements", []))
            return f"# {text}"
        
        elif block_type == "heading2":
            heading = block.get("heading2", {})
            text = self._extract_text_from_elements(heading.get("elements", []))
            return f"## {text}"
        
        elif block_type == "heading3":
            heading = block.get("heading3", {})
            text = self._extract_text_from_elements(heading.get("elements", []))
            return f"### {text}"
        
        elif block_type == "bulletedListItem":
            item = block.get("bulletedListItem", {})
            text = self._extract_text_from_elements(item.get("elements", []))
            return f"- {text}"
        
        elif block_type == "numberedListItem":
            item = block.get("numberedListItem", {})
            text = self._extract_text_from_elements(item.get("elements", []))
            return f"1. {text}"
        
        elif block_type == "code":
            code = block.get("code", {})
            language = code.get("language", "plaintext")
            code_body = code.get("body", {})
            code_text = self._extract_text_from_blocks(code_body.get("blocks", []))
            return f"```{language}\n{code_text}\n```"
        
        elif block_type == "divider":
            return "---"
        
        else:
            return ""
    
    def _extract_text_from_elements(self, elements: List[Dict[str, Any]]) -> str:
        """
        从元素列表中提取文本
        
        Args:
            elements: 元素列表
            
        Returns:
            提取的文本
        """
        text_parts = []
        
        for element in elements:
            if element.get("type") == "textRun":
                text_run = element.get("textRun", {})
                text = text_run.get("text", "")
                text_parts.append(text)
        
        return "".join(text_parts)
    
    def _extract_text_from_blocks(self, blocks: List[Dict[str, Any]]) -> str:
        """
        从块列表中提取文本
        
        Args:
            blocks: 块列表
            
        Returns:
            提取的文本
        """
        text_parts = []
        
        for block in blocks:
            if block.get("type") == "paragraph":
                paragraph = block.get("paragraph", {})
                text = self._extract_text_from_elements(paragraph.get("elements", []))
                text_parts.append(text)
        
        return "\n".join(text_parts)
    
    def list_documents(self, folder_token: str = "") -> List[Dict[str, Any]]:
        """
        列出文件夹中的文档
        
        Args:
            folder_token: 文件夹 token
            
        Returns:
            文档列表
        """
        try:
            # 这是一个简化的实现
            # 实际实现需要调用飞书的文件列表 API
            logger.info("Listing documents is not fully implemented yet")
            return []
        
        except Exception as e:
            logger.error(f"Error listing documents: {e}")
            return []
