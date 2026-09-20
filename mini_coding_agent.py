# -*- coding: utf-8 -*-
"""mini coding agent 演示：读-改-验 闭环"""
import os
from dotenv import load_dotenv

# 从项目根目录的 .env 加载通义千问配置
load_dotenv()

from smolagents import CodeAgent, OpenAIModel
from coding_tools import list_dir, read_file, write_file, edit_file, run_command

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

result = agent.run(
    "请列出工作目录里的文件，读取 sample.txt 的内容，"
    "然后新建 copy.txt，把 sample.txt 的内容复制进去。"
)
print("\n===== 最终答案 =====")
print(result)
