"""
summarizer.py — Tool 5 (Read)
Сжимает историю эссе для memory pipeline (Week 3).
Заменяет compressed_context() функцию — теперь это явный tool call с трассировкой.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from base import ToolResult

SCHEMA = {
    "name": "summarizer",
    "description": (
        "Summarize a student's essay history into a compact memory string. "
        "Use this when the student has 3+ previous sessions to compress history "
        "before including it in context. Returns a 2-3 sentence summary."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "sessions": {
                "type": "array",
                "description": "List of session objects with date, overall_band, and key issues",
                "items": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string"},
                        "overall_band": {"type": "number"},
                        "ta": {"type": "number"},
                        "cc": {"type": "number"},
                        "lr": {"type": "number"},
                        "gra": {"type": "number"},
                        "recurring_error": {"type": "string"}
                    }
                }
            },
            "user_goal": {
                "type": "string",
                "description": "Student's target band, e.g. '7.0'"
            }
        },
        "required": ["sessions"]
    }
}


def summarizer(sessions: list, user_goal: str = "7.0") -> ToolResult:
    if not sessions:
        return ToolResult(
            success=False,
            error="validation_error",
            message="Sessions list cannot be empty",
            suggested_action="Provide at least one previous session"
        )

    if len(sessions) > 20:
        return ToolResult(
            success=False,
            error="validation_error",
            message="Too many sessions (max 20)",
            suggested_action="Pass only the most recent 20 sessions"
        )

    # Считаем прогресс
    bands = [s.get("overall_band", 0) for s in sessions if s.get("overall_band")]
    first_band = bands[0] if bands else None
    last_band  = bands[-1] if bands else None
    trend = "improving" if (first_band and last_band and last_band > first_band) else \
            "declining"  if (first_band and last_band and last_band < first_band) else \
            "stable"

    # Собираем recurring errors
    errors = [s.get("recurring_error", "") for s in sessions if s.get("recurring_error")]
    unique_errors = list(dict.fromkeys(errors))[:3]

    # Последние оценки критериев
    last = sessions[-1]

    summary = (
        f"Student has completed {len(sessions)} session(s). "
        f"Progress: Band {first_band} → {last_band} ({trend}, goal: {user_goal}). "
        f"Current scores: TA={last.get('ta','?')} CC={last.get('cc','?')} "
        f"LR={last.get('lr','?')} GRA={last.get('gra','?')}. "
    )
    if unique_errors:
        summary += f"Recurring issues: {'; '.join(unique_errors)}."

    token_estimate = len(summary.split()) * 1.3  # приблизительно

    return ToolResult(
        success=True,
        data={
            "summary": summary,
            "sessions_count": len(sessions),
            "trend": trend,
            "first_band": first_band,
            "last_band": last_band,
            "token_estimate": int(token_estimate)
        }
    )
