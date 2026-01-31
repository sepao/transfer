"""
Qwen 优化版命令处理器
特点：
1. 超强容错 - 支持各种拼写变体
2. 简洁输出 - 纯文本，无 emoji
3. 智能解析 - 自动识别意图
"""

import os
import sys
import re
import glob
from typing import Optional
from difflib import SequenceMatcher

# 添加父项目路径
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from src.sync_engine import SyncEngine
from src.config import Config


class QwenHandler:
    """Qwen 优化版处理器"""

    def __init__(self, config_file: str = "config.json"):
        """初始化"""
        self.config = Config(config_file)
        self.engine = SyncEngine(
            notion_api_key=self.config.get("notion_api_key"),
            feishu_app_id=self.config.get("feishu_app_id"),
            feishu_app_secret=self.config.get("feishu_app_secret"),
            markdown_dir=self.config.get("markdown_dir", "./markdown_files"),
            mapping_file=self.config.get("mapping_file", "sync_mapping.json")
        )

        # 设置用户令牌
        user_token = self.config.get("feishu_user_access_token")
        if user_token:
            refresh_token = self.config.get("feishu_refresh_token")
            self.engine.feishu.set_user_token(user_token, refresh_token)

        self.markdown_dir = self.config.get("markdown_dir", "./markdown_files")

    def list_files(self) -> str:
        """列出文件"""
        md_files = glob.glob(os.path.join(self.markdown_dir, "**/*.md"), recursive=True)

        if not md_files:
            return "没有找到文件"

        result = f"共 {len(md_files)} 个文件:\n"
        for i, f in enumerate(md_files[:30], 1):
            name = os.path.basename(f)
            result += f"{i}. {name}\n"

        if len(md_files) > 30:
            result += f"...还有 {len(md_files) - 30} 个\n"

        return result

    def sync_file(self, filename: str) -> str:
        """同步单个文件"""
        md_files = glob.glob(os.path.join(self.markdown_dir, "**/*.md"), recursive=True)

        # 模糊匹配：名称包含关键词
        matched = [f for f in md_files if filename.lower() in os.path.basename(f).lower()]

        # 如果没找到，尝试更宽松的匹配
        if not matched:
            matched = self._fuzzy_match(filename, md_files)

        if not matched:
            return f"没找到文件: {filename}"

        if len(matched) > 1:
            names = [os.path.basename(f) for f in matched[:5]]
            return f"找到多个文件，请更精确:\n" + "\n".join(names)

        filepath = matched[0]
        name = os.path.basename(filepath)

        try:
            feishu_token, status = self.engine.sync_markdown_to_feishu(filepath)
            return f"同步成功\n文件: {name}\n飞书: {feishu_token}"
        except Exception as e:
            return f"同步失败: {str(e)[:100]}"

    def sync_all(self) -> str:
        """同步全部文件"""
        md_files = glob.glob(os.path.join(self.markdown_dir, "**/*.md"), recursive=True)

        if not md_files:
            return "没有找到文件"

        success = 0
        fail = 0
        results = []

        for filepath in md_files:
            name = os.path.basename(filepath)
            try:
                self.engine.sync_markdown_to_feishu(filepath)
                results.append(f"OK: {name}")
                success += 1
            except Exception as e:
                results.append(f"FAIL: {name}")
                fail += 1

        summary = f"完成: {success} 成功, {fail} 失败\n"
        return summary + "\n".join(results)

    def _fuzzy_match(self, query: str, files: list) -> list:
        """模糊匹配文件名"""
        query = query.lower()
        scored = []
        for f in files:
            name = os.path.basename(f).lower()
            # 计算相似度
            ratio = SequenceMatcher(None, query, name).ratio()
            if ratio > 0.4:  # 40% 以上相似度
                scored.append((f, ratio))

        # 按相似度排序
        scored.sort(key=lambda x: x[1], reverse=True)
        return [f for f, _ in scored[:5]]


# 全局处理器实例
_handler: Optional[QwenHandler] = None


def _get_handler() -> QwenHandler:
    """获取处理器单例"""
    global _handler
    if _handler is None:
        config_paths = [
            "config.json",
            os.path.join(parent_dir, "config.json"),
            "/Users/clairesun/Downloads/notion-feishu-sync/config.json"
        ]
        for path in config_paths:
            if os.path.exists(path):
                _handler = QwenHandler(path)
                break
        else:
            raise FileNotFoundError("找不到 config.json")
    return _handler


# ============================================================
# 命令识别 - 超强容错
# ============================================================

# "全部同步" 的各种写法（精确匹配）
ALL_EXACT = {
    "全部", "quanbu", "all", "同步全部", "syncall", "sync_all",
    "全部同步", "同步所有", "所有", "suoyou", "quan", "全",
    "tongbuquanbu", "allsync", "同步全", "全同步", "a"
}

# "列表" 的各种写法（精确匹配）
LIST_EXACT = {
    "列表", "liebiao", "list", "ls", "文件", "wenjian",
    "查看", "chakan", "show", "dir", "目录", "mulu", "l"
}

# "帮助" 的各种写法（精确匹配）
HELP_EXACT = {
    "帮助", "bangzhu", "help", "h", "?", "？", "怎么用", "用法"
}


def normalize(text: str) -> str:
    """
    标准化输入
    - 转小写
    - 去除多余空格和标点
    - 处理常见打字错误
    """
    text = text.lower().strip()
    # 去除标点（保留 ?）
    text = re.sub(r'[.,;:!，。；：！\-_=+]', ' ', text)
    # 合并空格
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def identify_command(raw_input: str) -> tuple:
    """
    智能识别命令意图

    Returns:
        (command_type, argument)
        command_type: 'all' | 'list' | 'help' | 'sync'
    """
    text = normalize(raw_input)

    # 空输入
    if not text:
        return ('help', None)

    # 精确匹配 "全部"
    if text in ALL_EXACT:
        return ('all', None)

    # 精确匹配 "列表"
    if text in LIST_EXACT:
        return ('list', None)

    # 精确匹配 "帮助"
    if text in HELP_EXACT:
        return ('help', None)

    # 检查是否以 "同步" 开头
    sync_prefixes = ["同步 ", "同步", "sync ", "sync", "tongbu ", "tongbu", "s "]
    for prefix in sync_prefixes:
        if text.startswith(prefix):
            # 提取文件名
            arg = text[len(prefix):].strip()
            if arg:
                return ('sync', arg)
            # 如果只是 "sync" 没有参数，提示需要文件名
            return ('sync', None)

    # 检查是否包含 "全部" 关键词（宽松匹配）
    if any(kw in text for kw in ["全部", "所有", "全"]):
        return ('all', None)

    # 默认：把整个输入当作文件名（最大容错）
    return ('sync', text)


def handle_command(raw_input: str) -> str:
    """
    处理命令 - Qwen 优化版

    支持各种写法：
        - "全部" / "all" / "a" / "quanbu" / "同步全部"
        - "列表" / "list" / "l" / "ls" / "liebiao"
        - "同步 xxx" / "sync xxx" / "xxx"（直接输入文件名）
        - "帮助" / "help" / "?"
    """
    cmd_type, arg = identify_command(raw_input)

    try:
        if cmd_type == 'help':
            return """命令说明:
1. 全部 - 同步所有文件
2. 列表 - 查看所有文件
3. 文件名 - 同步指定文件

示例:
- 全部
- 列表
- api
- 同步 models"""

        elif cmd_type == 'all':
            return _get_handler().sync_all()

        elif cmd_type == 'list':
            return _get_handler().list_files()

        elif cmd_type == 'sync':
            if not arg:
                return "请指定文件名"
            return _get_handler().sync_file(arg)

        else:
            return f"未知命令: {raw_input}\n输入 帮助 查看用法"

    except Exception as e:
        return f"执行出错: {str(e)[:100]}"


if __name__ == "__main__":
    # 测试
    print("=== 测试命令识别 ===")
    test_inputs = [
        "全部",
        "quanbu",
        "all",
        "列表",
        "list",
        "ls",
        "同步 api",
        "sync api",
        "api",
        "帮助",
        "help",
        "?",
    ]
    for inp in test_inputs:
        cmd_type, arg = identify_command(inp)
        print(f"'{inp}' -> ({cmd_type}, {arg})")
