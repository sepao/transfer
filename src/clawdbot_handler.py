"""
ClawdBot 集成模块
让你可以通过 Discord 发指令同步本地 Markdown 到飞书
"""

import os
import glob
from pathlib import Path
from typing import List, Dict, Optional
import json

from .sync_engine import SyncEngine
from .config import Config


class ClawdBotHandler:
    """ClawdBot 指令处理器"""

    def __init__(self, config_file: str = "config.json"):
        """初始化处理器"""
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

    def list_files(self, limit: int = 20) -> str:
        """列出所有可同步的 Markdown 文件"""
        md_files = glob.glob(os.path.join(self.markdown_dir, "**/*.md"), recursive=True)

        if not md_files:
            return "📂 没有找到 Markdown 文件"

        result = f"📂 **可同步的 Markdown 文件 ({len(md_files)} 个):**\n"
        for i, f in enumerate(md_files[:limit], 1):
            # 显示相对路径
            rel_path = os.path.relpath(f, self.markdown_dir)
            result += f"{i}. `{rel_path}`\n"

        if len(md_files) > limit:
            result += f"... 还有 {len(md_files) - limit} 个文件\n"

        return result

    def sync_file(self, filename: str) -> str:
        """
        同步指定的 Markdown 文件到飞书

        Args:
            filename: 文件名（支持部分匹配）
        """
        # 查找匹配的文件
        md_files = glob.glob(os.path.join(self.markdown_dir, "**/*.md"), recursive=True)

        matched = [f for f in md_files if filename.lower() in os.path.basename(f).lower()]

        if not matched:
            return f"❌ 没有找到匹配 `{filename}` 的文件"

        if len(matched) > 1:
            paths = [os.path.relpath(f, self.markdown_dir) for f in matched]
            return f"⚠️ 找到多个匹配文件，请更精确指定:\n" + "\n".join(f"- `{p}`" for p in paths[:10])

        filepath = matched[0]
        name = os.path.basename(filepath)

        try:
            feishu_token, status = self.engine.sync_markdown_to_feishu(filepath)
            return f"✅ 同步成功!\n📄 文件: `{name}`\n🔗 飞书文档: `{feishu_token}`"
        except Exception as e:
            return f"❌ 同步失败: {str(e)}"

    def sync_all(self) -> str:
        """同步所有 Markdown 文件到飞书"""
        md_files = glob.glob(os.path.join(self.markdown_dir, "**/*.md"), recursive=True)

        if not md_files:
            return "📂 没有找到 Markdown 文件"

        results = []
        success_count = 0
        fail_count = 0

        for filepath in md_files:
            name = os.path.basename(filepath)
            try:
                feishu_token, _ = self.engine.sync_markdown_to_feishu(filepath)
                results.append(f"✅ `{name}`")
                success_count += 1
            except Exception as e:
                results.append(f"❌ `{name}`: {str(e)[:50]}")
                fail_count += 1

        summary = f"📊 **同步完成:** {success_count} 成功, {fail_count} 失败\n\n"
        return summary + "\n".join(results)

    def get_status(self) -> str:
        """获取当前同步状态"""
        mappings = self.engine.mapping.get_all_mappings()

        if not mappings:
            return "📋 暂无同步记录"

        result = "📋 **同步记录:**\n"
        for notion_id, info in mappings.items():
            feishu = info.get('feishu_token', 'N/A')
            md = info.get('md_file', 'N/A')
            last = info.get('last_sync', 'N/A')[:16] if info.get('last_sync') else 'N/A'
            result += f"- 飞书: `{feishu[:20]}...` | 时间: {last}\n"

        return result


# 便捷函数，供 ClawdBot 直接调用
_handler: Optional[ClawdBotHandler] = None

def _get_handler() -> ClawdBotHandler:
    global _handler
    if _handler is None:
        # 尝试找到 config.json
        config_paths = [
            "config.json",
            os.path.join(os.path.dirname(__file__), "..", "config.json"),
            "/Users/clairesun/Downloads/notion-feishu-sync/config.json"
        ]
        for path in config_paths:
            if os.path.exists(path):
                _handler = ClawdBotHandler(path)
                break
        else:
            raise FileNotFoundError("找不到 config.json")
    return _handler


def list_files() -> str:
    """列出所有可同步的文件"""
    return _get_handler().list_files()


def sync_file(filename: str) -> str:
    """同步指定文件到飞书"""
    return _get_handler().sync_file(filename)


def sync_all() -> str:
    """同步所有文件到飞书"""
    return _get_handler().sync_all()


def get_status() -> str:
    """获取同步状态"""
    return _get_handler().get_status()


# 命令映射表，方便 ClawdBot 识别
COMMANDS = {
    "list": list_files,
    "ls": list_files,
    "列表": list_files,
    "sync": sync_file,
    "同步": sync_file,
    "sync_all": sync_all,
    "全部同步": sync_all,
    "status": get_status,
    "状态": get_status,
}


def handle_command(cmd: str, *args) -> str:
    """
    处理 ClawdBot 命令

    用法示例:
        handle_command("list")           -> 列出文件
        handle_command("sync", "api")    -> 同步包含 "api" 的文件
        handle_command("sync_all")       -> 同步所有文件
        handle_command("status")         -> 查看状态
    """
    cmd = cmd.lower().strip()

    if cmd in ["help", "帮助", "?"]:
        return """📖 **飞书同步命令:**
- `list` / `ls` - 列出所有 Markdown 文件
- `sync <文件名>` - 同步指定文件到飞书
- `sync_all` - 同步所有文件到飞书
- `status` - 查看同步状态"""

    if cmd in COMMANDS:
        func = COMMANDS[cmd]
        if cmd in ["sync", "同步"] and args:
            return func(args[0])
        elif cmd in ["sync", "同步"]:
            return "⚠️ 请指定文件名，如: `sync api-guide`"
        return func()

    return f"❓ 未知命令: `{cmd}`\n输入 `help` 查看帮助"


if __name__ == "__main__":
    # 测试
    print(handle_command("help"))
    print(handle_command("list"))
