"""
critic.py — Self-critique агент. Текстовый формат вместо JSON.
"""
import re
import sys as _sys
import os as _os

_AGENTS_DIR = _os.path.dirname(_os.path.abspath(__file__))
if _AGENTS_DIR not in _sys.path:
    _sys.path.insert(0, _AGENTS_DIR)

from base_agent import BaseAgent

SYSTEM = """You are a quality control specialist for market research reports.
Evaluate the analysis strictly. Use EXACTLY this format:

VERDICT: PASS or FAIL
SCORE: 0.0 to 1.0
SPECIFICITY: 0.0 to 1.0
EVIDENCE_QUALITY: 0.0 to 1.0
ACTIONABILITY: 0.0 to 1.0
COMPLETENESS: 0.0 to 1.0
STRENGTH_1: [one strength of the analysis]
STRENGTH_2: [another strength, or NONE]
WEAKNESS_1: [one weakness, or NONE if PASS]
FEEDBACK: [one paragraph of specific actionable feedback]

PASS if ALL scores >= 0.6
FAIL if ANY score < 0.6

Use exactly these field names. No JSON. No markdown."""


class CriticAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Critic",
            role="Quality evaluation",
            system_prompt=SYSTEM
        )

    def run(self, analysis: dict, topic: str) -> dict:
        # Компактное представление анализа
        sections_text = ""
        for s in analysis.get('key_sections', []):
            sections_text += f"\n{s.get('title', '')}: "
            sections_text += "; ".join(s.get('insights', [])[:2])

        analysis_summary = f"""Topic: {topic}
Summary: {analysis.get('executive_summary', 'EMPTY')[:200]}
Sections ({len(analysis.get('key_sections', []))}): {sections_text[:400]}
Trends: {', '.join(analysis.get('market_trends', [])[:3])}
Landscape: {analysis.get('competitive_landscape', 'EMPTY')[:150]}
Opportunities: {', '.join(analysis.get('opportunities', [])[:3])}
Confidence: {analysis.get('confidence_score', 0)}"""

        self.log("evaluate", f"analysis for: {topic}", "running quality check")
        raw = self.call_llm(
            f"Evaluate this market research analysis:\n\n{analysis_summary}\n\nApply the rubric strictly.",
            max_tokens=600
        )
        critique = self._parse_text(raw)
        verdict = critique.get('verdict', 'FAIL')
        score = critique.get('score', 0)
        self.log("verdict", topic, f"{verdict} (score={score})")
        return critique

    def _parse_text(self, raw: str) -> dict:
        result = {
            "verdict": "FAIL",
            "score": 0.0,
            "criteria_scores": {
                "specificity": 0.0,
                "evidence_quality": 0.0,
                "actionability": 0.0,
                "completeness": 0.0
            },
            "strengths": [],
            "weaknesses": [],
            "feedback": ""
        }

        for line in raw.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            if line.startswith("VERDICT:"):
                result["verdict"] = line.split(":", 1)[1].strip().upper()
            elif line.startswith("SCORE:"):
                try:
                    result["score"] = float(line.split(":", 1)[1].strip())
                except ValueError:
                    pass
            elif line.startswith("SPECIFICITY:"):
                try:
                    result["criteria_scores"]["specificity"] = float(line.split(":", 1)[1].strip())
                except ValueError:
                    pass
            elif line.startswith("EVIDENCE_QUALITY:"):
                try:
                    result["criteria_scores"]["evidence_quality"] = float(line.split(":", 1)[1].strip())
                except ValueError:
                    pass
            elif line.startswith("ACTIONABILITY:"):
                try:
                    result["criteria_scores"]["actionability"] = float(line.split(":", 1)[1].strip())
                except ValueError:
                    pass
            elif line.startswith("COMPLETENESS:"):
                try:
                    result["criteria_scores"]["completeness"] = float(line.split(":", 1)[1].strip())
                except ValueError:
                    pass
            elif re.match(r"STRENGTH_\d+:", line):
                val = line.split(":", 1)[1].strip()
                if val and val != "NONE":
                    result["strengths"].append(val)
            elif re.match(r"WEAKNESS_\d+:", line):
                val = line.split(":", 1)[1].strip()
                if val and val != "NONE":
                    result["weaknesses"].append(val)
            elif line.startswith("FEEDBACK:"):
                result["feedback"] = line.split(":", 1)[1].strip()

        return result