# -*- coding: utf-8 -*-
"""反思闭环演示：跑任务 → 反思提炼教训 → 存记忆 → 下次带教训"""
import os
from dotenv import load_dotenv

load_dotenv()

from smolagents import CodeAgent, OpenAIModel
from coding_tools import list_dir, read_file, write_file, edit_file, run_command
from agent_memory import save_reflection, build_reflection_context, clear_memories
from reflect import generate_reflection

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

clear_memories()

# ── 第一次：跑任务 + 反思 ──
task1 = "在沙箱里创建一个 todo.txt，内容写 '学完 agent 反思机制'"
print("=" * 60)
print("【第一次任务】", task1)
result1 = agent.run(task1)
steps1 = agent.memory.steps  # 拿执行轨迹（必须在第二次 run 之前取）
reflection1 = generate_reflection(model, task1, str(result1), steps1)
save_reflection(reflection1)
print("\n第一次反思出的教训：", reflection1.get("lesson", ""))
print("适用场景：", reflection1.get("applicable_when", ""))

# ── 第二次：注入历史教训 ──
lesson_ctx = build_reflection_context()
task2 = "在沙箱里再创建一个 note.txt，内容写 '第二次任务'"
print("\n" + "=" * 60)
print("【第二次任务】", task2)
print("\n注入的历史教训：")
print(lesson_ctx)
print()
result2 = agent.run(f"历史教训：\n{lesson_ctx}\n\n当前任务：{task2}")
print("第二次结果：", result2)
print("\n" + "=" * 60)
print("反思闭环完成：第一次的教训已存进 memory，并注入到第二次任务。")
