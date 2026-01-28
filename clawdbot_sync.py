#!/usr/bin/env python3
"""
ClawdBot 同步入口
用法: python3 clawdbot_sync.py <命令> [参数]

命令:
  help          - 显示帮助
  list          - 列出可同步文件
  sync <文件名>  - 同步指定文件到飞书
  sync_all      - 同步所有文件
  status        - 查看同步状态
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.clawdbot_handler import handle_command


def main():
    if len(sys.argv) < 2:
        print(handle_command("help"))
        return

    cmd = sys.argv[1]
    args = sys.argv[2:] if len(sys.argv) > 2 else []

    result = handle_command(cmd, *args)
    print(result)


if __name__ == "__main__":
    main()
