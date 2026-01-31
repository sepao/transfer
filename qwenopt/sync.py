#!/usr/bin/env python3
"""
Qwen 优化版同步入口
极简命令，超强容错

用法: python3 qwenopt/sync.py <命令> [参数]

命令 (以下任意一种写法都行):
  全部  /  all  /  a  /  同步全部  /  quanbu  /  syncall
  列表  /  list /  l  /  ls  /  liebiao
  同步  /  sync /  s  /  <文件名>

示例:
  python3 qwenopt/sync.py 全部
  python3 qwenopt/sync.py list
  python3 qwenopt/sync.py api
"""

import sys
import os

# 添加父项目路径
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from qwenopt.handler import handle_command


def main():
    # 没有参数时显示帮助
    if len(sys.argv) < 2:
        print(handle_command("help"))
        return

    # 合并所有参数（容错：用户可能分开写文件名）
    raw_input = " ".join(sys.argv[1:])

    result = handle_command(raw_input)
    print(result)


if __name__ == "__main__":
    main()
