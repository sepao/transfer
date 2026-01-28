#!/usr/bin/env python3
"""
基础测试脚本
测试各个模块的功能
"""

import sys
import os
import json

# 添加 src 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.markdown_handler import MarkdownHandler
from src.notion_client import markdown_to_notion_blocks
from src.config import Config


def test_markdown_handler():
    """测试 Markdown 处理器"""
    print("=" * 50)
    print("测试 Markdown 处理器")
    print("=" * 50)
    
    handler = MarkdownHandler("./test_markdown")
    
    # 测试创建文件
    content = """# 测试文档

这是一个测试文档。

## 第二级标题

- 列表项 1
- 列表项 2
- 列表项 3

### 第三级标题

```python
def hello():
    print("Hello, World!")
```

**粗体文本** 和 *斜体文本*
"""
    
    file_path = handler.create_from_content("测试文档", content)
    print(f"✓ 创建文件: {file_path}")
    
    # 测试读取文件
    read_content = handler.read_file(file_path)
    print(f"✓ 读取文件成功，内容长度: {len(read_content)} 字符")
    
    # 测试文件存在检查
    exists = handler.file_exists(file_path)
    print(f"✓ 文件存在检查: {exists}")
    
    # 测试列出文件
    files = handler.list_files()
    print(f"✓ 列出文件: {files}")
    
    # 清理
    handler.delete_file(file_path)
    print(f"✓ 删除文件成功")
    
    print()


def test_markdown_to_notion_blocks():
    """测试 Markdown 转 Notion 块"""
    print("=" * 50)
    print("测试 Markdown 转 Notion 块")
    print("=" * 50)
    
    markdown = """# 标题 1

这是一个段落。

## 标题 2

- 列表项 1
- 列表项 2

1. 有序项 1
1. 有序项 2

```python
code block
```
"""
    
    blocks = markdown_to_notion_blocks(markdown)
    print(f"✓ 转换成功，生成 {len(blocks)} 个块")
    
    # 打印块结构
    for i, block in enumerate(blocks[:5]):  # 只打印前 5 个
        print(f"  块 {i+1}: {block.get('type')}")
    
    if len(blocks) > 5:
        print(f"  ... 还有 {len(blocks) - 5} 个块")
    
    print()


def test_config():
    """测试配置管理"""
    print("=" * 50)
    print("测试配置管理")
    print("=" * 50)
    
    # 创建测试配置
    test_config_file = "test_config.json"
    test_config_data = {
        "notion_api_key": "test_key",
        "feishu_app_id": "test_id",
        "feishu_app_secret": "test_secret"
    }
    
    with open(test_config_file, 'w') as f:
        json.dump(test_config_data, f)
    
    try:
        config = Config(test_config_file)
        print(f"✓ 配置加载成功")
        
        # 测试获取值
        api_key = config.get("notion_api_key")
        print(f"✓ 获取配置值: notion_api_key = {api_key}")
        
        # 测试设置值
        config.set("test_key", "test_value")
        print(f"✓ 设置配置值成功")
        
        # 测试验证
        try:
            config.validate()
            print(f"✓ 配置验证通过")
        except ValueError as e:
            print(f"✗ 配置验证失败: {e}")
    
    finally:
        # 清理
        if os.path.exists(test_config_file):
            os.remove(test_config_file)
    
    print()


def test_cli_help():
    """测试 CLI 帮助命令"""
    print("=" * 50)
    print("测试 CLI 帮助命令")
    print("=" * 50)
    
    import subprocess
    
    try:
        result = subprocess.run(
            ["python", "main.py", "--help"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(__file__)
        )
        
        if result.returncode == 0:
            print("✓ CLI 帮助命令执行成功")
            print("\n输出内容:")
            print(result.stdout[:200] + "...")
        else:
            print(f"✗ CLI 帮助命令执行失败")
            print(result.stderr)
    except Exception as e:
        print(f"✗ 执行 CLI 命令出错: {e}")
    
    print()


def main():
    """主测试函数"""
    print("\n")
    print("╔" + "=" * 48 + "╗")
    print("║" + " " * 10 + "Notion Feishu Sync 基础测试" + " " * 12 + "║")
    print("╚" + "=" * 48 + "╝")
    print()
    
    try:
        test_markdown_handler()
        test_markdown_to_notion_blocks()
        test_config()
        test_cli_help()
        
        print("=" * 50)
        print("✓ 所有基础测试完成！")
        print("=" * 50)
        print()
        print("下一步:")
        print("1. 运行 'python main.py init' 初始化配置")
        print("2. 输入您的 Notion API Key 和飞书应用凭证")
        print("3. 使用 'python main.py sync --help' 查看同步命令")
        print()
    
    except Exception as e:
        print(f"✗ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
