"""
word_count.py — Tool 1 (Read)
Детерминированный подсчёт слов + IELTS флаги.
Заменяет промпт-инструкцию — фикс бага из calibration Week 5.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from base import ToolResult

SCHEMA = {
    "name": "word_count",
    "description": (
        "Count words in an essay and return IELTS-specific flags. "
        "Always call this FIRST before scoring any essay. "
        "Returns word count, below-minimum flag, and band cap info."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Essay text to count"}
        },
        "required": ["text"]
    }
}


def word_count(text: str) -> ToolResult:
    if not text or not text.strip():
        return ToolResult(
            success=False,
            error="validation_error",
            message="Essay text cannot be empty",
            suggested_action="Provide a non-empty essay text",
            example_valid_call='word_count(text="Technology is important...")'
        )

    count = len(text.split())
    below_minimum  = count < 250
    apply_band_cap = count < 150
    extremely_short = count < 50

    flag = None
    if extremely_short:
        flag = f"⚠️ {count} words — too short to evaluate (minimum: 250)"
    elif below_minimum:
        flag = f"⚠️ {count} words — below 250 word minimum"

    return ToolResult(
        success=True,
        data={
            "count": count,
            "below_minimum": below_minimum,
            "apply_band_cap": apply_band_cap,
            "extremely_short": extremely_short,
            "flag": flag,
            "band_cap_value": 4.5 if apply_band_cap else None
        }
    )
