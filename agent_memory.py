# -*- coding: utf-8 -*-
"""长时记忆：跨会话保存经验，下次任务自动带上相关记忆。

原理很简单：
    1. save_memory：把「任务 + 结果」追加存进 memory.jsonl（文件不存在会自动创建）
    2. build_memory_context：把最近 n 条记忆拼成一段文字，注入新任务的 prompt
"""
import json
from datetime import datetime
from pathlib import Path

MEMORY_FILE = Path(__file__).resolve().parent / "memory.jsonl"
# 容量上限：超过就触发压缩（保留最新的）
MAX_MEMORIES = 500
# 每写多少条检查一次压缩（避免每次都读全文件判断）
TRIM_CHECK_INTERVAL = 50
_write_count = 0

def load_memories() -> list[dict]:
    """读取所有历史记忆；文件不存在时返回空列表。"""
    if not MEMORY_FILE.exists():
        return []
    memorise = []
    for line in MEMORY_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            memorise.append(json.loads(line))
        except json.JSONDecodeError:
            # 跳过损坏的行（比如写到一半崩了），不影响其他记忆
            continue
    return memorise


def _trim_if_needed():
    """超过上限时，只保留最新的 MAX_MEMORIES 条（重写文件）。"""
    memorise = load_memories()
    if len(memorise) <= MAX_MEMORIES:
        return
    kept = memorise[-MAX_MEMORIES:]
    MEMORY_FILE.write_text(
        "\n".join(json.dumps(m, ensure_ascii=False) for m in kept) + "\n",
        encoding="utf-8",
    )


def save_memory(entry: dict):
    """追加一条记忆（O(1) 写，崩溃安全）。"""
    global _write_count

    #自动添加时间戳
    entry.setdefault("timestamp", datetime.now().isoformat(timespec="seconds"))

    #追加一行
    with MEMORY_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


    #每追加一行_write_count加一，每隔TRIM_CHECK_INTERVAL条判断是否需要压缩
    _write_count += 1
    if _write_count%TRIM_CHECK_INTERVAL == 0:
        _trim_if_needed()


def build_memory_context(n: int = 5) -> str:
    """把最近 n 条记忆拼成一段上下文，供注入新任务的 prompt。"""
    memories = load_memories()
    if not memories:
        return "（暂无历史记忆）"
    return "\n".join(
        f"- 任务：{m.get('task')} → 结果：{m.get('result', '')}"
        for m in memories[-n:]
    )


def clear_memories():
    """清空所有记忆（演示从零开始用）。"""
    if MEMORY_FILE.exists():
        MEMORY_FILE.unlink()
