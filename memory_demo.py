# -*- coding: utf-8 -*-
"""记忆系统演示：连续两次任务，第二次能记住第一次（跨会话记忆）"""
import os
from dotenv import load_dotenv

load_dotenv()

from smolagents import CodeAgent, OpenAIModel
from coding_tools import list_dir, read_file, write_file, edit_file, run_command
from agent_memory import save_memory, build_memory_context, clear_memories

model = OpenAIModel(
    model_id=os.getenv("LLM_DEFAULT_MODEL", "qwen-flash"),
    api_base=os.getenv("OPENAI_API_BASE"),
    api_key=os.getenv("alQwen-api"),
)

agent = CodeAgent(
    tools=[list_dir, read_file, write_file, edit_file, run_command],
    model=model,
    max_steps=10,
)

# 清空历史记忆，保证演示从零开始
clear_memories()

# ── 第一次任务：不依赖任何记忆 ──
task1 = "在沙箱里创建一个 todo.txt，内容写 '学完 agent 记忆系统'"
print("=" * 60)
print("【第一次任务】", task1)
result1 = agent.run(task1)
save_memory({"task": task1, "result": str(result1)})
print("\n第一次结果：", result1)
print("（已存入 memory.jsonl）")

# ── 第二次任务：注入历史记忆 ──
task2 = "根据你的历史记忆，回答：我之前让你做了什么？"
memory_ctx = build_memory_context()
print("\n" + "=" * 60)
print("【第二次任务】", task2)
print("\n注入的记忆上下文：")
print(memory_ctx)
print()
result2 = agent.run(f"历史记忆：\n{memory_ctx}\n\n当前任务：{task2}")
save_memory({"task": task2, "result": str(result2)})

print("\n第二次答案：", result2)
print("\n" + "=" * 60)
print("如果第二次能说出 todo.txt，说明跨会话记忆生效了。")
