# -*- coding: utf-8 -*-
"""文件操作工具集：把 smolagents 的 CodeAgent 改造成 mini coding agent。

安全设计（多层兜底）：
    1. shell=False      —— & | ; 变成普通字符，从根上杜绝命令串联/注入
    2. 命令名白名单     —— 只允许少数真实可执行文件（默认拒绝）
    3. 参数形状白名单   —— 每个命令只允许参数"长成某种样子"，正则匹配不上就拒
    4. 路径隔离         —— 文件操作只能在工作目录内，禁止逃逸
    5. 大小与超时限制   —— 读文件限大小、命令限时，防撑爆上下文 / 死循环
"""
import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path

from smolagents import tool

# 工作目录：agent 能碰的边界（路径隔离），相对于项目根目录，自动创建
WORK_DIR = Path(__file__).resolve().parent / "sandbox"
WORK_DIR.mkdir(parents=True, exist_ok=True)

# 读文件上限：防止读超大文件撑爆上下文
MAX_READ_BYTES = 100 * 1024  # 100 KB

# 命令白名单 + 参数形状正则（正则匹配"命令名之后的参数串"）。
# 注意：shell=False 下 dir/type/echo 是 cmd 内置命令（不是 exe）跑不了，所以只放真 exe。
COMMAND_WHITELIST = {
    # 命令名  ->  参数正则
    "python":  re.compile(r"^[A-Za-z0-9_\-/\\]+\.py(?:\s+.*)?$"),          # 只允许运行 .py 脚本，禁止 -c / -m
    "pytest":  re.compile(r"^.*$"),                                         # 运行测试（验证步骤）
    "git":     re.compile(r"^(?:status|diff|log|show)(?:\s+.*)?$"),  # 只读 git 子命令
    "findstr": re.compile(r"^.+$"),                                         # 文件内容搜索
    "where":   re.compile(r"^.+$"),                                         # 查找文件位置
}


def _resolve(path: str) -> Path:
    """把用户给的路径解析到工作目录内，越界则报错（路径隔离）。"""
    p = Path(path)
    if not p.is_absolute():
        p = WORK_DIR / p
    p = p.resolve()
    if not p.is_relative_to(WORK_DIR.resolve()):
        raise PermissionError(f"路径越界，禁止访问工作目录之外：{path}")
    return p


@tool
def list_dir(path: str = ".") -> str:
    """列出指定目录下的文件和子目录。

    Args:
        path: 目录路径，默认 "." 表示工作目录。

    Returns:
        每行一个条目，目录名后面带 /。
    """
    target = _resolve(path)
    entries = sorted(target.iterdir())
    return "\n".join(e.name + ("/" if e.is_dir() else "") for e in entries) or "(空目录)"


@tool
def read_file(path: str) -> str:
    """读取一个文本文件的内容（超过大小上限会截断）。

    Args:
        path: 文件路径。

    Returns:
        文件内容（过大时截断并提示）。
    """
    target = _resolve(path)
    size = target.stat().st_size
    if size > MAX_READ_BYTES:
        # 只读前 MAX_READ_BYTES 个字节
        with target.open("rb") as f:
            raw = f.read(MAX_READ_BYTES)
        text = raw.decode("utf-8", errors="replace")
        return text + f"\n\n[已截断，源文件 {size} 字节]"
    return target.read_text(encoding="utf-8")


@tool
def write_file(path: str, content: str) -> str:
    """创建或覆盖一个文件，写入给定内容。

    Args:
        path: 文件路径。
        content: 要写入的完整文本内容。

    Returns:
        成功提示。
    """
    target = _resolve(path)
    target.parent.mkdir(parents=True, exist_ok=True)  # 确保父目录存在
    target.write_text(content, encoding="utf-8")
    return f"已写入 {target}"


@tool
def edit_file(path: str, old: str, new: str) -> str:
    """把文件中第一次出现的 old 片段替换为 new。

    Args:
        path: 文件路径。
        old: 要被替换的旧文本。
        new: 替换后的新文本。

    Returns:
        替换结果说明。
    """
    target = _resolve(path)
    if not target.exists():
        return f"错误：文件不存在 {target}"
    text = target.read_text(encoding="utf-8")
    if old not in text:
        return "错误：文件中找不到要替换的片段"
    target.write_text(text.replace(old, new, 1), encoding="utf-8")
    return f"已在 {target} 完成替换"


@tool
def run_command(command: str) -> str:
    """在沙箱工作目录中执行一个白名单内的安全命令。

    Args:
        command: 要执行的命令。

    Returns:
        命令输出，或拒绝原因。
    """
    # 1. 切词：posix=False 让 Windows 反斜杠当普通字符，正确处理引号
    try:
        argv = shlex.split(command, posix=False)
    except ValueError as e:
        return f"命令解析失败：{e}"
    if not argv:
        return "拒绝执行：空命令"

    # 1.1. 去引号（posix=False 会保留引号）
    argv = [argv[0]] + [_strip_quotes(a) for a in argv[1:]]

    # 2. 命令名白名单：basename + 小写，防路径/大小写绕过
    cmd = os.path.basename(argv[0]).lower()
    if cmd not in COMMAND_WHITELIST:
        return f"拒绝执行：命令 '{cmd}' 不在白名单"

    # 3. 参数形状白名单：命令名之后的参数必须匹配该命令允许的正则
    args_str = " ".join(argv[1:])
    if not COMMAND_WHITELIST[cmd].match(args_str):
        return f"拒绝执行：参数 '{args_str}' 不符合 {cmd} 的允许格式"

    # 5. 找完整路径
    exe_path = shutil.which(cmd)
    if exe_path is None:
         return f"命令 '{cmd}' 未找到（确认已安装且在 PATH 中）"
    argv[0] = exe_path

    # 4. 执行：shell=False 杜绝 & | ; 注入，cwd 限制目录，timeout 防死循环
    try:
        r = subprocess.run(
            argv, shell=False, cwd=str(WORK_DIR),
            capture_output=True, text=True, timeout=10,
            errors="replace",  # 中文 Windows 命令输出是 GBK，用 errors=replace 防解码崩溃
        )
        return (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        return "命令超时，已终止"
    except FileNotFoundError:
        return f"命令 '{cmd}' 未找到（确认已安装且在 PATH 中）"

def _strip_quotes(s: str) -> str:
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'"):
        return s[1:-1]
    return s