# -*- coding: utf-8 -*-
"""反思模块：从一次任务的执行过程里提炼出可复用的经验。"""
import json

from smolagents import ChatMessage, MessageRole
from smolagents.memory import ActionStep, FinalAnswerStep, PlanningStep


MAX_FIELD_CHARS = 300
MAX_STEPS_IN_SUMMARY = 10


def _truncate(text, n: int) -> str:
    text = str(text).strip()
    return text if len(text) <= n else text[:n] + "..."


def extract_steps_summary(steps: list) -> str:
    """把 memory.steps 压成一段可读的执行轨迹。"""
    lines = []
    for s in steps:
        if isinstance(s, PlanningStep):
            lines.append(f"[规划] {_truncate(s.plan, MAX_FIELD_CHARS)}")
        elif isinstance(s, ActionStep):
            lines.append(f"第 {s.step_number} 步：")
            if s.code_action:
                lines.append(f"  代码：{_truncate(s.code_action, MAX_FIELD_CHARS)}")
            if s.observations:
                lines.append(f"  观察：{_truncate(s.observations, MAX_FIELD_CHARS)}")
            if s.error:
                lines.append(f"  错误：{_truncate(str(s.error), MAX_FIELD_CHARS)}")
        elif isinstance(s, FinalAnswerStep):
            lines.append(f"[最终答案] {_truncate(str(s.output), MAX_FIELD_CHARS)}")

    if len(lines) > MAX_STEPS_IN_SUMMARY * 4:
        half = MAX_STEPS_IN_SUMMARY // 2 * 4
        lines = lines[:half] + ["...（中间步骤省略）..."] + lines[-half:]

    return "\n".join(lines) or "（无执行记录）"


def judge_success(steps: list) -> tuple[bool, str]:
    """用规则判断任务是否成功。

    注意：memory.steps 里只有 TaskStep/PlanningStep/ActionStep，没有 FinalAnswerStep，
    所以判断「是否成功」要看 ActionStep 的 is_final_answer 标志。
    """
    action_steps = [s for s in steps if isinstance(s, ActionStep)]

    # 有没有给出最终答案
    has_final = any(s.is_final_answer for s in action_steps)
    if not has_final:
        if action_steps and action_steps[-1].error is not None:
            return False, f"最后一步报错：{type(action_steps[-1].error).__name__}"
        return False, "达到最大步数仍未给出最终答案"

    # 给了最终答案，看过程中有没有踩坑（已自纠）
    errors = [s for s in action_steps if s.error is not None]
    if errors:
        return True, f"成功，但过程中踩了 {len(errors)} 次坑（已自纠）"
    return True, "一次通过，无错误"


REFLECT_PROMPT = """你刚完成一个任务。请分析这次执行过程，产出一条可复用的经验。

## 任务
{task}

## 结果
{result}

## 是否成功
{success}（{reason}）

## 执行轨迹
{steps_summary}

## 要求
1. task_type：任务类型（bug_fix / feature_add / refactor / test_gen / doc_gen / 其他）
2. domain：技术栈（python / javascript / java / 其他）
3. lesson：这次"特有的发现"。**不要写"要跑测试"这类常识**，只写这次让你意外或值得记住的事。如果没什么特别发现，写"无特别经验"。
4. applicable_when：这条经验在什么条件下适用（要具体）
5. evidence：你的判断依据（引用执行轨迹里的具体事件）

**只返回 JSON**，不要有多余文字：
{{"task_type": "...", "domain": "...", "lesson": "...", "applicable_when": "...", "evidence": "..."}}
"""


def _extract_text(response) -> str:
    """从 ChatMessage 里提取纯文本。"""
    if not hasattr(response, "content"):
        return str(response)

    content = response.content

    # content 是列表：提取所有 text 块
    if isinstance(content, list):
        return "".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )

    # content 是字符串：直接用
    return str(content)


def generate_reflection(model, task: str, result: str, steps: list) -> dict:
    """调 LLM 生成结构化反思。"""
    success, reason = judge_success(steps)
    steps_summary = extract_steps_summary(steps)

    prompt = REFLECT_PROMPT.format(
        task=task,
        result=_truncate(str(result), 500),
        success="成功" if success else "失败",
        reason=reason,
        steps_summary=steps_summary,
    )

    #包装成消息列表
    messages = [
        ChatMessage(
            role=MessageRole.USER,
            content= [{"type" : "text" , "text" : prompt}]
        )
    ]
    try:
        response = model.generate(messages)
        text = _extract_text(response)  # ★ 改这里
        reflection = _parse_json(text)
    except Exception as e:
        reflection = {"lesson": f"反思生成失败：{type(e).__name__}: {e}"}

    reflection.setdefault("task_type", "unknown")
    reflection.setdefault("domain", "unknown")
    reflection.setdefault("lesson", "无特别经验")
    reflection.setdefault("applicable_when", "")
    reflection.setdefault("evidence", "")
    reflection["success"] = success
    reflection["reason"] = reason

    return reflection


def _parse_json(text: str) -> dict:
    """从 LLM 输出里抠出 JSON。"""
    text = text.strip()

    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        text = text.rsplit("```", 1)[0].strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError(f"无法解析 JSON：{text[:200]}")