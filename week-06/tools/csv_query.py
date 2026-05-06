"""
csv_query.py — Tool 4 (Read)
Query IELTS band descriptors из CSV файла.
Агент может спросить: "что значит LR 6.0?" и получить официальное описание.
"""
import sys, os, io, csv
sys.path.insert(0, os.path.dirname(__file__))
from base import ToolResult

SCHEMA = {
    "name": "csv_query",
    "description": (
        "Look up official IELTS band descriptor for a specific criterion and score. "
        "Use this to ground your feedback in official IELTS language. "
        "Criteria: ta, cc, lr, gra. Scores: 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0"
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "criterion": {
                "type": "string",
                "enum": ["ta", "cc", "lr", "gra"],
                "description": "The criterion to look up"
            },
            "band": {
                "type": "number",
                "description": "The band score (e.g. 5.0, 6.5)"
            }
        },
        "required": ["criterion", "band"]
    }
}

# Встроенные дескрипторы (упрощённые официальные формулировки)
DESCRIPTORS = {
    "ta": {
        4.0: "The prompt is dealt with but no clear position. Ideas are present but undeveloped.",
        4.5: "Addresses the prompt but position is unclear. Limited development of ideas.",
        5.0: "Addresses prompt; position is present but not always clear. Main ideas but limited support.",
        5.5: "Addresses prompt adequately; position is clear. Main ideas present but underdeveloped.",
        6.0: "Addresses all parts of the prompt. Clear position throughout. Main ideas extended and supported.",
        6.5: "Addresses all parts of the prompt. Clear position. Main ideas extended with relevant support.",
        7.0: "Addresses all parts of the prompt. Clear, sustained position. Main ideas clearly presented with extended support.",
        7.5: "Covers all requirements fully. Position is clear and developed throughout with well-extended ideas.",
        8.0: "Fully addresses all aspects of the task with sophisticated coverage of ideas and a fully developed position.",
        8.5: "Covers all requirements of the task fully. Ideas are highly developed with precise examples.",
        9.0: "Fully addresses all aspects of the task. Sophisticated ideas with fully developed arguments."
    },
    "cc": {
        4.0: "Information is arranged but not clearly. Cohesive devices are used but inaccurately.",
        4.5: "Some organisation present. Cohesive devices used but mechanical or repetitive.",
        5.0: "Information is organised but not always logically. Cohesive devices used but not always appropriately.",
        5.5: "Information is organised. Cohesive devices are used but with some inaccuracies.",
        6.0: "Information and ideas are organised clearly. Cohesive devices are used effectively though with some lapses.",
        6.5: "Information and ideas are logically organised. Cohesive devices are used effectively.",
        7.0: "Information logically organised. Clear progression. Range of cohesive devices used appropriately.",
        7.5: "Information logically organised with clear progression. Cohesive devices used skillfully.",
        8.0: "Sequence of information is managed skillfully. Cohesive devices used accurately and appropriately.",
        8.5: "Writes with full flexibility. Cohesion is natural and precise.",
        9.0: "The message is effortlessly communicated. Cohesion is used naturally and without effort."
    },
    "lr": {
        4.0: "Basic vocabulary. Limited control of word formation. Errors may obscure meaning.",
        4.5: "Limited vocabulary. Some errors in word choice and formation.",
        5.0: "Minimal range. Noticeable errors in spelling and word formation. May cause difficulty.",
        5.5: "Adequate range. Some errors in word choice and spelling but generally clear.",
        6.0: "Adequate range. Some errors in word choice and collocation but generally clear.",
        6.5: "Sufficient range. Some errors in word choice and collocation but generally effective.",
        7.0: "Sufficient range. Some errors in word choice, collocation, and spelling — but these don't impede communication.",
        7.5: "Wide range. Very few errors in word choice, collocation, or spelling.",
        8.0: "Wide resource. Rare errors. Uses less common vocabulary with precision.",
        8.5: "Very wide range. Vocabulary used with precision and flexibility.",
        9.0: "Full flexibility and precision. Uses vocabulary with full accuracy and sophistication."
    },
    "gra": {
        4.0: "Very limited range. Mostly simple sentences. Numerous errors.",
        4.5: "Limited range. Some complex sentences attempted. Frequent errors.",
        5.0: "Limited range. Complex sentences attempted. Several errors, which may cause difficulty.",
        5.5: "Mix of simple and complex structures. Several errors but meaning is clear.",
        6.0: "Mix of simple and complex structures. Some errors but they rarely reduce communication.",
        6.5: "Uses a variety of complex structures. Some errors remain but generally well-controlled.",
        7.0: "Uses a variety of complex structures. Produces frequent error-free sentences.",
        7.5: "Wide range of structures. Majority error-free. Occasional minor errors.",
        8.0: "Wide range of structures. Most sentences error-free. Rare errors occur.",
        8.5: "Wide range of structures used flexibly. Almost all sentences error-free.",
        9.0: "Full range of structures used with complete flexibility and accuracy."
    }
}

CRITERION_NAMES = {
    "ta": "Task Achievement",
    "cc": "Coherence & Cohesion",
    "lr": "Lexical Resource",
    "gra": "Grammatical Range & Accuracy"
}


def csv_query(criterion: str, band: float) -> ToolResult:
    criterion = criterion.lower()
    if criterion not in DESCRIPTORS:
        return ToolResult(
            success=False,
            error="validation_error",
            message=f"Unknown criterion: '{criterion}'",
            suggested_action="Use one of: ta, cc, lr, gra",
            example_valid_call='csv_query(criterion="lr", band=6.0)'
        )

    valid_bands = sorted(DESCRIPTORS[criterion].keys())
    # Найти ближайший band
    closest = min(valid_bands, key=lambda b: abs(b - band))
    descriptor = DESCRIPTORS[criterion][closest]

    return ToolResult(
        success=True,
        data={
            "criterion": criterion,
            "criterion_name": CRITERION_NAMES[criterion],
            "band_requested": band,
            "band_found": closest,
            "descriptor": descriptor
        }
    )
