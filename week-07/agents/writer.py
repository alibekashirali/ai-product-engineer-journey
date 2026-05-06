"""
writer.py — Генерирует финальный research brief.
ACT: получает одобренный анализ → форматирует в читаемый markdown brief.
Изоляция: видит только финальный анализ, не видит переписку других агентов.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from base_agent import BaseAgent

SYSTEM = """You are a professional business writer specializing in market research briefs.
Transform structured analysis data into a clear, readable markdown report.

Format guidelines:
- Executive Summary: 3-4 sentences
- Use ## headers for sections
- Use bullet points for lists
- Bold key terms and numbers
- End with clear Next Steps section
- Target length: 400-600 words
- Tone: professional, direct, actionable

Do NOT include meta-commentary about the analysis process."""


class WriterAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Writer",
            role="Report generation",
            system_prompt=SYSTEM
        )

    def run(self, analysis: dict, critique: dict, topic: str) -> str:
        quality_note = ""
        if critique.get('verdict') == 'FAIL':
            quality_note = "\nNote: This report is based on best available data (quality gate not fully passed).\n"

        strengths = "\n".join(f"- {s}" for s in critique.get('strengths', []))

        prompt = f"""Write a professional market research brief based on this analysis.

Topic: {topic}
{quality_note}

Executive Summary: {analysis.get('executive_summary', '')}

Key Sections:
{self._format_sections(analysis.get('key_sections', []))}

Market Trends: {', '.join(analysis.get('market_trends', []))}

Competitive Landscape: {analysis.get('competitive_landscape', '')}

Opportunities: {', '.join(analysis.get('opportunities', []))}

Risks: {', '.join(analysis.get('risks', []))}

Analyst confidence score: {analysis.get('confidence_score', 0)}

Write a clear, professional markdown brief for a business audience."""

        self.log("write", f"analysis confidence={analysis.get('confidence_score')}", "generating brief")
        brief = self.call_llm(prompt, max_tokens=1200)
        self.log("brief_ready", topic, f"{len(brief.split())} words written")
        return brief

    def _format_sections(self, sections: list) -> str:
        result = ""
        for s in sections:
            result += f"\n{s.get('title', '')}:\n"
            for insight in s.get('insights', []):
                result += f"  - {insight}\n"
            result += f"  Evidence: {s.get('evidence', '')}\n"
        return result
