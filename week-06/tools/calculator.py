"""
calculator.py — Tool 3 (Read)
Точное вычисление Overall Band по правилам IELTS.
Детерминированный — заменяет LLM averaging (был источником нестабильности).
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from base import ToolResult

VALID_BANDS = {4.0,4.5,5.0,5.5,6.0,6.5,7.0,7.5,8.0,8.5,9.0}

SCHEMA = {
    "name": "calculator",
    "description": (
        "Calculate the Overall Band score from four IELTS criteria scores. "
        "Applies band cap for short essays. Returns the official rounded band. "
        "Call this after scoring all four criteria."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "ta":  {"type": "number", "description": "Task Achievement score"},
            "cc":  {"type": "number", "description": "Coherence & Cohesion score"},
            "lr":  {"type": "number", "description": "Lexical Resource score"},
            "gra": {"type": "number", "description": "Grammatical Range & Accuracy score"},
            "word_count": {"type": "integer", "description": "Essay word count (for band cap check)"}
        },
        "required": ["ta", "cc", "lr", "gra", "word_count"]
    }
}


def calculator(ta: float, cc: float, lr: float, gra: float, word_count: int) -> ToolResult:
    scores = {"ta": ta, "cc": cc, "lr": lr, "gra": gra}

    # Validate all scores
    invalid = {k: v for k, v in scores.items() if v not in VALID_BANDS}
    if invalid:
        return ToolResult(
            success=False,
            error="validation_error",
            message=f"Invalid IELTS scores: {invalid}. Must be from: {sorted(VALID_BANDS)}",
            suggested_action="Use only official IELTS band increments: 4.0, 4.5, 5.0, 5.5, ...",
            example_valid_call="calculator(ta=5.0, cc=5.5, lr=5.0, gra=5.0, word_count=200)"
        )

    avg = sum(scores.values()) / 4

    # Round to nearest 0.5
    rounded = round(avg * 2) / 2
    rounded = max(4.0, min(9.0, rounded))

    # Apply band cap
    capped = False
    cap_reason = None
    if word_count < 150 and rounded > 4.5:
        rounded = 4.5
        capped = True
        cap_reason = f"Essay is {word_count} words — overall band capped at 4.5"

    return ToolResult(
        success=True,
        data={
            "overall_band": rounded,
            "raw_average": round(avg, 2),
            "capped": capped,
            "cap_reason": cap_reason,
            "criteria": scores
        }
    )
