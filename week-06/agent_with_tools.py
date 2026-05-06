"""
agent_with_tools.py — Week 6
GainScore Writing Coach с tool calling.

Агент теперь явно вызывает tools вместо встроенных инструкций промпта:
  1. word_count()      — подсчёт слов (детерминированный)
  2. verify_citation() — проверка цитат перед включением в фидбек
  3. calculator()      — overall band (точный, с cap)
  4. csv_query()       — официальные IELTS дескрипторы
  5. summarizer()      — сжатие истории
  6. notifier()        — уведомление студента (write)
"""
import sys, os, json

# Add tools directory to path
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_TOOLS_DIR = os.path.join(_BASE_DIR, "tools")
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

import anthropic
from tool_registry import (
    start_trace, execute_tool, finish_trace,
    print_trace_summary, TOOL_SCHEMAS
)

client = anthropic.Anthropic()
MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You are an IELTS Writing Coach for GainScore.

You have access to tools. Use them in this order for every essay evaluation:
1. ALWAYS call word_count first to get the word count and band cap status
2. Score all 4 IELTS criteria: TA, CC, LR, GRA (on scale: 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0)
3. Before citing ANY phrase, call verify_citation to confirm it exists in the essay
4. Call calculator with all 4 scores and the word_count to get the official Overall Band
5. Optionally call csv_query to look up official IELTS descriptor language
6. Write your complete feedback following the output format
7. Call notifier to inform the student their feedback is ready

Output format:
**Overall Band:** [from calculator tool]
[word count flag from word_count tool if applicable]

**TA — X.X:** [verified quote] → [improvement]
**CC — X.X:** [verified quote] → [improvement]
**LR — X.X:** [verified quote] → [improvement]
**GRA — X.X:** [verified quote] → [improvement]

**Priority Focus:** [criterion + specific action]
**Exercise:** [concrete writing task with scope]. Submit your work here and I will review it immediately.

Rules:
- NEVER write or rewrite the essay for the student
- NEVER include a citation without first calling verify_citation
- Overall Band MUST come from the calculator tool, not your own math"""


def process_tool_call(tool_name: str, tool_input: dict, reason: str = "") -> str:
    """Выполняет tool call через registry и возвращает JSON строку для API."""
    result = execute_tool(tool_name, tool_input, reason=reason)
    return json.dumps(result.to_dict())


def evaluate_essay(essay: str, user_id: int = 1, session_id: str = "demo") -> str:
    """
    Запускает агента с tool calling для оценки эссе.
    Возвращает финальный фидбек.
    """
    start_trace(session_id)

    messages = [{"role": "user", "content": f"Please evaluate this IELTS Task 2 essay:\n\n{essay}"}]

    max_iterations = 10
    iteration = 0
    final_response = ""

    while iteration < max_iterations:
        iteration += 1

        response = client.messages.create(
            model=MODEL,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            tools=TOOL_SCHEMAS,
            messages=messages
        )

        # Добавляем ответ ассистента в историю
        messages.append({"role": "assistant", "content": response.content})

        # Нет tool calls — финальный ответ
        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    final_response = block.text
            break

        # Обрабатываем tool calls
        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    # Определяем reason из контекста (упрощённо)
                    reason_map = {
                        "word_count": "checking essay length and band cap",
                        "verify_citation": "verifying citation exists in essay",
                        "calculator": "computing official overall band score",
                        "csv_query": "looking up official IELTS descriptor",
                        "summarizer": "compressing student history",
                        "notifier": "notifying student feedback is ready"
                    }
                    reason = reason_map.get(block.name, "")
                    result_json = process_tool_call(block.name, block.input, reason)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_json
                    })

            messages.append({"role": "user", "content": tool_results})

    trace = finish_trace()
    print_trace_summary(trace)
    return final_response


if __name__ == "__main__":
    test_essay = """Technology is very important in our lives today.
    Many people use smartphones every day. Technology is good because it helps us
    communicate with friends and family. However, some people think technology is bad
    because we spend too much time on our phones. In conclusion, technology has both
    advantages and disadvantages and we should use it carefully."""

    print("Running GainScore Agent with Tools...\n")
    feedback = evaluate_essay(test_essay, user_id=42, session_id="week06_test")
    print("\n" + "="*50)
    print("FINAL FEEDBACK:")
    print("="*50)
    print(feedback)