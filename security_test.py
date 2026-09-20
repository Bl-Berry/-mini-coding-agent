# -*- coding: utf-8 -*-
"""安全测试：验证 run_command 的四层防线能把攻击拦下来"""
from coding_tools import run_command

cases = [
    ("dir & del /q C:\\important", "应拒"),
    ("del /s /q *", "应拒"),
    ("DEL /S /Q *", "应拒（大小写）"),
    ("powershell -c Remove-Item -Recurse C:\\", "应拒"),
    ('python -c "import os"', "应拒（-c 任意代码）"),
    ("python -m pip install requests", "应拒（-m 模块）"),
    ("git reset --hard", "应拒（危险 git 子命令）"),
    ("where python", "应放行"),
    ("findstr Hello sample.txt", "应放行"),
    ("git status", "应放行"),
]

print("=" * 60)
for cmd, expect in cases:
    result = run_command(cmd)
    print(f"[{expect}] 输入: {cmd!r}")
    print(f"        输出: {result}")
    print("-" * 60)
