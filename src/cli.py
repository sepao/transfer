"""
命令行界面模块
提供一键同步的命令行工具
"""

import click
import json
import os
import sys
from pathlib import Path
import logging
from typing import Optional

from .sync_engine import SyncEngine
from .config import Config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CLIContext:
    """CLI 上下文"""
    
    def __init__(self):
        self.config = None
        self.engine = None
    
    def load_config(self, config_file: str = "config.json"):
        """加载配置"""
        try:
            self.config = Config(config_file)
            self._init_engine()
        except FileNotFoundError:
            # 如果配置文件不存在，不抛出异常，让命令自己处理
            self.config = None
            self.engine = None
    
    def _init_engine(self):
        """初始化同步引擎"""
        if not self.config:
            raise RuntimeError("Config not loaded")

        self.engine = SyncEngine(
            notion_api_key=self.config.get("notion_api_key"),
            feishu_app_id=self.config.get("feishu_app_id"),
            feishu_app_secret=self.config.get("feishu_app_secret"),
            markdown_dir=self.config.get("markdown_dir", "./markdown_files"),
            mapping_file=self.config.get("mapping_file", "sync_mapping.json")
        )

        # 如果配置了用户令牌，使用用户令牌
        user_token = self.config.get("feishu_user_access_token")
        if user_token:
            refresh_token = self.config.get("feishu_refresh_token")
            self.engine.feishu.set_user_token(user_token, refresh_token)
            logger.info("Using user access token for Feishu API")
    
    def ensure_config(self):
        """确保配置已加载"""
        if not self.config or not self.engine:
            raise RuntimeError("Config not loaded. Please run 'python main.py init' first.")


# 创建全局上下文
ctx = CLIContext()


@click.group()
@click.option('--config', default='config.json', help='配置文件路径')
def cli(config):
    """Notion 飞书 Markdown 三方同步工具"""
    ctx.load_config(config)


@cli.command()
def init():
    """初始化配置文件"""
    config_file = "config.json"
    
    if os.path.exists(config_file):
        if not click.confirm(f"{config_file} already exists. Overwrite?"):
            return
    
    click.echo("Please provide the following information:")
    
    notion_api_key = click.prompt("Notion API Key", hide_input=True)
    feishu_app_id = click.prompt("Feishu App ID")
    feishu_app_secret = click.prompt("Feishu App Secret", hide_input=True)
    markdown_dir = click.prompt("Markdown Directory", default="./markdown_files")
    
    config_data = {
        "notion_api_key": notion_api_key,
        "feishu_app_id": feishu_app_id,
        "feishu_app_secret": feishu_app_secret,
        "markdown_dir": markdown_dir,
        "mapping_file": "sync_mapping.json"
    }
    
    try:
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        click.echo(f"✓ Config file created: {config_file}")
        click.echo("⚠️  Please keep your API keys safe!")
    except Exception as e:
        click.echo(f"✗ Error creating config file: {e}", err=True)


@cli.command()
def auth():
    """通过 OAuth 授权获取用户令牌（文档将归属于你）"""
    ctx.ensure_config()

    try:
        click.echo("Starting OAuth authorization flow...")
        click.echo("A browser window will open for you to authorize the app.\n")

        # 获取用户令牌
        token_data = ctx.engine.feishu.authorize_user()

        # 保存到配置文件
        config_file = "config.json"
        with open(config_file, 'r') as f:
            config = json.load(f)

        config["feishu_user_access_token"] = token_data["user_access_token"]
        if token_data.get("refresh_token"):
            config["feishu_refresh_token"] = token_data["refresh_token"]

        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        click.echo(f"\n✓ User token saved to {config_file}")
        click.echo("Documents will now be created under YOUR account!")

    except Exception as e:
        click.echo(f"✗ Authorization failed: {e}", err=True)
        sys.exit(1)


@cli.group()
def sync():
    """同步命令"""
    ctx.ensure_config()


@sync.command()
@click.argument('notion_page_id')
@click.option('--folder-token', default='', help='飞书文件夹 token (默认使用配置文件中的值)')
@click.option('--create-md', is_flag=True, help='同时创建本地 Markdown 文件')
def notion_to_feishu(notion_page_id, folder_token, create_md):
    """同步 Notion 页面到飞书

    NOTION_PAGE_ID: Notion 页面 ID
    """
    try:
        # 如果没有指定 folder_token，使用配置文件中的值
        # 但如果使用用户令牌，则不使用 app 的 folder_token（用户可能无权限）
        if not folder_token:
            if not ctx.config.get("feishu_user_access_token"):
                folder_token = ctx.config.get("feishu_folder_token", "")

        click.echo(f"Syncing Notion page {notion_page_id} to Feishu...")

        feishu_token, md_file, status = ctx.engine.sync_notion_to_feishu(
            notion_page_id,
            feishu_folder_token=folder_token,
            create_md=create_md
        )
        
        click.echo(f"✓ {status}")
        click.echo(f"Feishu Token: {feishu_token}")
        
        if md_file:
            click.echo(f"Markdown File: {md_file}")
    
    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@sync.command()
@click.argument('md_file')
@click.option('--folder-token', default='', help='飞书文件夹 token (默认使用配置文件中的值)')
@click.option('--notion-page-id', default='', help='关联的 Notion 页面 ID')
def markdown_to_feishu(md_file, folder_token, notion_page_id):
    """同步本地 Markdown 文件到飞书

    MD_FILE: Markdown 文件路径
    """
    try:
        # 如果没有指定 folder_token，使用配置文件中的值
        # 但如果使用用户令牌，则不使用 app 的 folder_token（用户可能无权限）
        if not folder_token:
            if not ctx.config.get("feishu_user_access_token"):
                folder_token = ctx.config.get("feishu_folder_token", "")

        click.echo(f"Syncing Markdown file {md_file} to Feishu...")

        feishu_token, status = ctx.engine.sync_markdown_to_feishu(
            md_file,
            feishu_folder_token=folder_token,
            notion_page_id=notion_page_id
        )
        
        click.echo(f"✓ {status}")
        click.echo(f"Feishu Token: {feishu_token}")
    
    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@sync.command()
@click.argument('feishu_token')
@click.option('--md-file', default='', help='本地 Markdown 文件路径')
@click.option('--notion-page-id', default='', help='关联的 Notion 页面 ID')
def feishu_to_markdown(feishu_token, md_file, notion_page_id):
    """同步飞书文档到本地 Markdown
    
    FEISHU_TOKEN: 飞书文档 token
    """
    try:
        click.echo(f"Syncing Feishu document {feishu_token} to Markdown...")
        
        md_file, status = ctx.engine.sync_feishu_to_markdown(
            feishu_token,
            md_file=md_file,
            notion_page_id=notion_page_id
        )
        
        click.echo(f"✓ {status}")
        click.echo(f"Markdown File: {md_file}")
    
    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@sync.command()
@click.argument('feishu_token')
@click.argument('notion_page_id')
def feishu_to_notion(feishu_token, notion_page_id):
    """同步飞书文档到 Notion 页面
    
    FEISHU_TOKEN: 飞书文档 token
    NOTION_PAGE_ID: Notion 页面 ID
    """
    try:
        click.echo(f"Syncing Feishu document to Notion page...")
        
        status = ctx.engine.sync_feishu_to_notion(feishu_token, notion_page_id)
        
        click.echo(f"✓ {status}")
    
    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@sync.command()
@click.argument('md_file')
@click.argument('notion_page_id')
def markdown_to_notion(md_file, notion_page_id):
    """同步本地 Markdown 文件到 Notion 页面
    
    MD_FILE: Markdown 文件路径
    NOTION_PAGE_ID: Notion 页面 ID
    """
    try:
        click.echo(f"Syncing Markdown file to Notion page...")
        
        status = ctx.engine.sync_markdown_to_notion(md_file, notion_page_id)
        
        click.echo(f"✓ {status}")
    
    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@cli.group()
def status():
    """状态查询命令"""
    ctx.ensure_config()


@status.command()
@click.argument('notion_page_id')
def sync_status(notion_page_id):
    """查看同步状态
    
    NOTION_PAGE_ID: Notion 页面 ID
    """
    try:
        status_info = ctx.engine.get_sync_status(notion_page_id)
        
        click.echo(f"Sync Status for Notion page {notion_page_id}:")
        click.echo(json.dumps(status_info, indent=2, ensure_ascii=False))
    
    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@status.command()
def list_mappings():
    """列出所有同步映射"""
    try:
        mappings = ctx.engine.mapping.get_all_mappings()
        
        if not mappings:
            click.echo("No mappings found.")
            return
        
        click.echo("Sync Mappings:")
        for notion_id, mapping_info in mappings.items():
            click.echo(f"\nNotion Page ID: {notion_id}")
            click.echo(f"  Feishu Token: {mapping_info.get('feishu_token')}")
            if mapping_info.get('md_file'):
                click.echo(f"  Markdown File: {mapping_info.get('md_file')}")
            click.echo(f"  Last Sync: {mapping_info.get('last_sync')}")
    
    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
def version():
    """显示版本信息"""
    click.echo("Notion Feishu Sync v1.0.0")


def main():
    """主入口"""
    cli()


if __name__ == '__main__':
    main()
