"""
analyst.py — Структурирует и анализирует данные от Researcher.
Использует текстовый формат вместо JSON чтобы избежать truncation.
"""
import re
import sys as _sys
import os as _os

_AGENTS_DIR = _os.path.dirname(_os.path.abspath(__file__))
if _AGENTS_DIR not in _sys.path:
    _sys.path.insert(0, _AGENTS_DIR)

from base_agent import BaseAgent

SYSTEM = """You are a market analyst. Analyze research findings and produce a structured report.

Use EXACTLY this format:

EXECUTIVE_SUMMARY: [2-3 sentences overview of the market]

SECTION_1_TITLE: [section name]
SECTION_1_INSIGHT_1: [specific insight with named examples]
SECTION_1_INSIGHT_2: [specific insight with data]
SECTION_1_EVIDENCE: [concrete example or data point]

SECTION_2_TITLE: [section name]
SECTION_2_INSIGHT_1: [specific insight]
SECTION_2_INSIGHT_2: [specific insight]
SECTION_2_EVIDENCE: [concrete example or data point]

SECTION_3_TITLE: [section name]
SECTION_3_INSIGHT_1: [specific insight]
SECTION_3_INSIGHT_2: [specific insight]
SECTION_3_EVIDENCE: [concrete example or data point]

MARKET_TRENDS: [trend 1] | [trend 2] | [trend 3]
COMPETITIVE_LANDSCAPE: [2-3 sentences on key players and dynamics]
OPPORTUNITIES: [opp 1] | [opp 2] | [opp 3]
RISKS: [risk 1] | [risk 2]
CONFIDENCE: 0.7

Use exactly these field names. No JSON. No markdown headers."""


class AnalystAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Analyst",
            role="Data analysis and structuring",
            system_prompt=SYSTEM
        )

    def run(self, all_findings: list, topic: str) -> dict:
        # Компактное представление findings
        findings_text = ""
        for f in all_findings:
            findings_text += f"\n[{f.get('subtask', 'Research')}]\n"
            for point in f.get('findings', [])[:4]:  # max 4 per subtask
                findings_text += f"• {point['point']}: {point.get('detail', '')[:120]}\n"

        prompt = f"""Analyze these findings about: {topic}

{findings_text[:3000]}

Write the analysis following the exact format specified."""

        self.log("analyze", f"{len(all_findings)} research sets", "synthesizing findings")
        raw = self.call_llm(prompt, max_tokens=1500)
        analysis = self._parse_text(raw, topic)
        n_sections = len(analysis.get('key_sections', []))
        self.log("analysis_ready", topic, f"{n_sections} sections, confidence={analysis.get('confidence_score')}")
        return analysis

    def _parse_text(self, raw: str, topic: str) -> dict:
        """Парсит текстовый формат в структуру."""
        lines = raw.strip().split('\n')
        result = {
            "topic": topic,
            "executive_summary": "",
            "key_sections": [],
            "market_trends": [],
            "competitive_landscape": "",
            "opportunities": [],
            "risks": [],
            "confidence_score": 0.7
        }

        current_section = None
        current_insights = []
        current_evidence = ""
        current_title = ""

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith("EXECUTIVE_SUMMARY:"):
                result["executive_summary"] = line.split(":", 1)[1].strip()

            elif re.match(r"SECTION_\d+_TITLE:", line):
                # Сохраняем предыдущую секцию
                if current_title and current_insights:
                    result["key_sections"].append({
                        "title": current_title,
                        "insights": current_insights,
                        "evidence": current_evidence
                    })
                current_title = line.split(":", 1)[1].strip()
                current_insights = []
                current_evidence = ""

            elif re.match(r"SECTION_\d+_INSIGHT_\d+:", line):
                current_insights.append(line.split(":", 1)[1].strip())

            elif re.match(r"SECTION_\d+_EVIDENCE:", line):
                current_evidence = line.split(":", 1)[1].strip()

            elif line.startswith("MARKET_TRENDS:"):
                trends_raw = line.split(":", 1)[1].strip()
                result["market_trends"] = [t.strip() for t in trends_raw.split("|") if t.strip()]

            elif line.startswith("COMPETITIVE_LANDSCAPE:"):
                result["competitive_landscape"] = line.split(":", 1)[1].strip()

            elif line.startswith("OPPORTUNITIES:"):
                opps_raw = line.split(":", 1)[1].strip()
                result["opportunities"] = [o.strip() for o in opps_raw.split("|") if o.strip()]

            elif line.startswith("RISKS:"):
                risks_raw = line.split(":", 1)[1].strip()
                result["risks"] = [r.strip() for r in risks_raw.split("|") if r.strip()]

            elif line.startswith("CONFIDENCE:"):
                try:
                    result["confidence_score"] = float(line.split(":", 1)[1].strip())
                except ValueError:
                    pass

        # Сохраняем последнюю секцию
        if current_title and current_insights:
            result["key_sections"].append({
                "title": current_title,
                "insights": current_insights,
                "evidence": current_evidence
            })

        # Fallback если парсинг не дал секций
        if not result["key_sections"] and len(raw) > 100:
            self.log("parse_fallback", topic, "using raw text as fallback")
            result["executive_summary"] = raw[:300]
            result["key_sections"] = [{"title": "Analysis", "insights": [raw[:500]], "evidence": ""}]
            result["confidence_score"] = 0.4

        return result