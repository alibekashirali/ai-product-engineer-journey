"""
verify_citation.py — Tool 2 (Read)
Проверяет что цитата существует в тексте эссе.
Фикс fabrication бага из cal_018 (Week 5 calibration).
"""
import sys, os, re
sys.path.insert(0, os.path.dirname(__file__))
from base import ToolResult

SCHEMA = {
    "name": "verify_citation",
    "description": (
        "Verify that a quoted phrase actually exists in the essay text. "
        "Call this before including any quote in feedback to prevent fabricated citations. "
        "Returns whether the citation is valid and the closest match found."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "quote": {"type": "string", "description": "The phrase you want to cite"},
            "essay": {"type": "string", "description": "The full essay text"}
        },
        "required": ["quote", "essay"]
    }
}


def verify_citation(quote: str, essay: str) -> ToolResult:
    if not quote or not quote.strip():
        return ToolResult(
            success=False,
            error="validation_error",
            message="Quote cannot be empty",
            suggested_action="Provide a specific phrase from the essay to verify"
        )
    if not essay or not essay.strip():
        return ToolResult(
            success=False,
            error="validation_error",
            message="Essay text cannot be empty",
            suggested_action="Provide the full essay text"
        )

    quote_clean = quote.lower().strip().strip('"\'')
    essay_lower = essay.lower()

    # Exact match
    if quote_clean in essay_lower:
        return ToolResult(
            success=True,
            data={"valid": True, "match_type": "exact", "quote": quote}
        )

    # Partial match — найти longest matching subsequence
    quote_words = quote_clean.split()
    best_overlap = 0
    best_match = ""

    for i in range(len(quote_words)):
        for j in range(i + 2, len(quote_words) + 1):
            sub = " ".join(quote_words[i:j])
            if sub in essay_lower:
                if len(sub) > len(best_match):
                    best_match = sub
                    best_overlap = j - i

    if best_overlap >= 3:
        return ToolResult(
            success=True,
            data={
                "valid": False,
                "match_type": "partial",
                "quote": quote,
                "closest_match": best_match,
                "suggestion": f'Use this instead: "{best_match}"'
            },
            message=f"Exact quote not found, but partial match exists: '{best_match}'",
            suggested_action=f'Replace the citation with the actual text: "{best_match}"'
        )

    return ToolResult(
        success=True,
        data={"valid": False, "match_type": "none", "quote": quote},
        message="Citation not found in essay text — this would be a fabricated quote",
        suggested_action="Find an actual phrase from the essay to cite, or describe without quoting"
    )
