"""
planner.py — Декомпозирует задачу. Текстовый формат.
"""
import re
import sys as _sys
import os as _os

_AGENTS_DIR = _os.path.dirname(_os.path.abspath(__file__))
if _AGENTS_DIR not in _sys.path:
    _sys.path.insert(0, _AGENTS_DIR)

from base_agent import BaseAgent

SYSTEM = """You are a research planning specialist. Break down a research topic into subtasks.

Use EXACTLY this format:
TOPIC: [original topic]
OUTPUT_FORMAT: [brief description of desired output]

SUBTASK_1_ID: 1
SUBTASK_1_TASK: [specific research question]
SUBTASK_1_FOCUS: [what specifically to look for]

SUBTASK_2_ID: 2
SUBTASK_2_TASK: [specific research question]
SUBTASK_2_FOCUS: [what specifically to look for]

SUBTASK_3_ID: 3
SUBTASK_3_TASK: [specific research question]
SUBTASK_3_FOCUS: [what specifically to look for]

SUBTASK_4_ID: 4
SUBTASK_4_TASK: [specific research question]
SUBTASK_4_FOCUS: [what specifically to look for]

Use exactly these field names. No JSON. No markdown."""


class PlannerAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Planner",
            role="Task decomposition",
            system_prompt=SYSTEM
        )

    def run(self, topic: str) -> dict:
        self.log("decompose", f"topic: {topic}", "creating research plan")
        raw = self.call_llm(
            f"Break this research topic into 4 specific subtasks:\n\n{topic}",
            max_tokens=500
        )
        plan = self._parse_text(raw, topic)
        n = len(plan.get('subtasks', []))
        self.log("plan_ready", topic, f"{n} subtasks created")
        return plan

    def _parse_text(self, raw: str, topic: str) -> dict:
        subtasks = []
        current = {}

        for line in raw.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            if re.match(r"SUBTASK_\d+_ID:", line):
                if current.get('task'):
                    subtasks.append(current)
                try:
                    current = {'id': int(line.split(":", 1)[1].strip())}
                except ValueError:
                    current = {'id': len(subtasks) + 1}
            elif re.match(r"SUBTASK_\d+_TASK:", line):
                current['task'] = line.split(":", 1)[1].strip()
            elif re.match(r"SUBTASK_\d+_FOCUS:", line):
                current['focus'] = line.split(":", 1)[1].strip()

        if current.get('task'):
            subtasks.append(current)

        # Fallback если парсинг не дал результатов
        if not subtasks:
            sentences = [s.strip() for s in raw.split('\n') if len(s.strip()) > 20][:4]
            subtasks = [{'id': i+1, 'task': s[:100], 'focus': 'general research'} for i, s in enumerate(sentences)]

        return {
            "topic": topic,
            "subtasks": subtasks,
            "output_format": "market research brief"
        }