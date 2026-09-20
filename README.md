# mini-coding-agent

> 基于 HuggingFace [smolagents](https://github.com/huggingface/smolagents) **二次开发**的轻量级 Coding Agent。
> 在 `CodeAgent` 基础上新增了「文件操作工具集 + 命令安全层 + 跨会话记忆」，让 Agent 能在沙箱目录内完成「读 → 改 → 验」的代码操作闭环。

---

## ✨ 二次开发新增了什么

### 1. 文件操作工具集（`coding_tools.py`）

围绕「读-改-验」闭环设计了 5 个工具：

| 工具 | 作用 |
| --- | --- |
| `list_dir` | 列出目录内容 |
| `read_file` | 读取文件（超 100KB 自动截断） |
| `write_file` | 创建/覆盖文件 |
| `edit_file` | 精准替换文件片段 |
| `run_command` | 执行白名单内命令 |

### 2. 命令安全层（多层兜底）

针对 `run_command` 设计了多层防护，防止 LLM 生成的代码危害系统：

- **`shell=False`**：`& | ;` 变成普通字符，从根上杜绝命令串联注入
- **命令名白名单**：默认拒绝，只放行明确允许的可执行文件
- **参数形状正则校验**：每个命令只允许参数「长成某种样子」（如 `python` 只允许运行 `.py`，禁止 `-c`/`-m`）
- **路径隔离**：文件操作只能在工作目录内，禁止越界
- **大小与超时限制**：读文件限大小、命令限时，防撑爆上下文 / 死循环

配套 `security_test.py`，用 10 个用例（7 攻击 + 3 合法）验证拦截效果。

### 3. 跨会话记忆系统（`agent_memory.py`）

- JSONL 追加写（O(1) 写入、崩溃安全、跳过损坏行）
- 容量上限 500 条，超限自动压缩保留最新
- 每条自动加时间戳
- 下次任务运行时，取最近 N 条记忆注入 prompt，实现「存经验 → 下次取回」的闭环

配套 `memory_demo.py` 演示「连续两次任务，第二次能记住第一次」。

---

## 🧰 技术栈

- [smolagents](https://github.com/huggingface/smolagents)（CodeAgent / CodeAct）
- 通义千问（OpenAI 兼容接口，DashScope）
- Python 3.10+

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
copy .env.example .env   # 复制后填入你的 API Key
```

### 3. 运行

```bash
# 读-改-验 闭环演示
python mini_coding_agent.py

# 跨会话记忆演示
python memory_demo.py

# 命令安全测试
python security_test.py
```

---

## 📁 目录结构

```
mini-coding-agent/
├── coding_tools.py      # 文件操作工具集 + 命令安全层
├── agent_memory.py      # 跨会话记忆系统
├── mini_coding_agent.py # Agent 装配 + 读-改-验演示
├── memory_demo.py       # 记忆闭环演示
├── security_test.py     # 命令安全测试
├── requirements.txt     # 依赖清单
└── .env.example         # 环境变量模板
```

---

## 📝 说明

本项目基于开源的 [smolagents](https://github.com/huggingface/smolagents) 框架进行二次开发，Agent 核心循环与 CodeAct 执行引擎来自 smolagents，本仓库的贡献集中在**文件操作工具集、命令安全层、跨会话记忆系统**三部分。
