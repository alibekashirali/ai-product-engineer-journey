"""
researcher.py — Собирает данные по каждой подзадаче.
ACT: получает подзадачу → собирает данные → возвращает structured data.
"""
import re
import sys as _sys
import os as _os

_AGENTS_DIR = _os.path.dirname(_os.path.abspath(__file__))
if _AGENTS_DIR not in _sys.path:
    _sys.path.insert(0, _AGENTS_DIR)

from base_agent import BaseAgent

SYSTEM = """You are a market research specialist. Research the given subtask and return findings.

STRICT FORMAT — respond with EXACTLY this structure, nothing else:
SUBTASK_ID: {id}
CONFIDENCE: high|medium|low

FINDING_1: [one sentence finding]
DETAIL_1: [2-3 sentences of supporting detail with specific examples or numbers]

FINDING_2: [one sentence finding]
DETAIL_2: [2-3 sentences of supporting detail]

FINDING_3: [one sentence finding]
DETAIL_3: [2-3 sentences of supporting detail]

FINDING_4: [one sentence finding]
DETAIL_4: [2-3 sentences of supporting detail]

FINDING_5: [one sentence finding]
DETAIL_5: [2-3 sentences of supporting detail]

Use exactly this format. No JSON. No markdown. No preamble."""


class ResearcherAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Researcher",
            role="Data gathering",
            system_prompt=SYSTEM
        )

    def run(self, subtask: dict, context: str = "") -> dict:
        prompt = f"""Research this specific topic:
Task ID: {subtask['id']}
Task: {subtask['task']}
Focus: {subtask['focus']}
{f'Context: {context}' if context else ''}

Provide 5 specific, factual findings with details."""

        self.log("research", subtask['task'], "gathering data")
        raw = self.call_llm(prompt, max_tokens=900)
        data = self._parse_text(raw, subtask)
        n = len(data.get('findings', []))
        self.log("findings_ready", subtask['task'], f"{n} findings, confidence={data.get('confidence')}")
        return data

    def _parse_text(self, raw: str, subtask: dict) -> dict:
        """Парсит текстовый формат в структуру."""
        lines = raw.strip().split('\n')
        findings = []
        confidence = "medium"
        current_point = None

        for line in lines:
            line = line.strip()
            if line.startswith("CONFIDENCE:"):
                confidence = line.split(":", 1)[1].strip().lower()
            elif re.match(r"FINDING_\d+:", line):
                current_point = line.split(":", 1)[1].strip()
            elif re.match(r"DETAIL_\d+:", line) and current_point:
                detail = line.split(":", 1)[1].strip()
                if current_point:
                    findings.append({"point": current_point, "detail": detail})
                current_point = None

        # Fallback если парсинг не дал результатов
        if not findings:
            self.log("parse_fallback", subtask['task'], "text parse failed, extracting sentences")
            sentences = [s.strip() for s in re.split(r'[.\n]', raw) if len(s.strip()) > 20][:5]
            findings = [{"point": s[:80], "detail": s} for s in sentences]

        return {
            "subtask_id": subtask.get('id', 0),
            "subtask": subtask.get('task', ''),
            "findings": findings,
            "key_sources": ["LLM knowledge base"],
            "confidence": confidence
        }

    def refine(self, subtask: dict, critique_feedback: str) -> dict:
        """Повторный сбор данных после FAIL от Critic."""
        refined = subtask.copy()
        refined['task'] = f"{subtask['task']} [Focus on: {critique_feedback[:80]}]"
        self.log("refine", critique_feedback[:80], "re-researching")
        return self.run(refined, context=f"Previous data was insufficient: {critique_feedback}")