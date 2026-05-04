"""
rubric.py — Week 4
GainScore Writing Coach: функции pass/fail для каждого критерия eval.

Два типа проверок:
  Code-based  → детерминированные (band scale, word count, schema)
  Pattern     → regex/string matching (exercise followup, refusal)
"""

import re
from typing import Optional


IELTS_VALID_BANDS = {4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0}


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def extract_overall_band(response: str) -> Optional[float]:
    """Извлекает Overall Band из ответа агента."""
    patterns = [
        r"\*\*Overall Band[^:]*:\*\*\s*([\d.]+)",
        r"Overall Band[^:]*:\s*([\d.]+)",
        r"Overall[^:]*:\s*([\d.]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                continue
    return None


def extract_criterion_scores(response: str) -> dict:
    """Извлекает все 4 критерия из ответа."""
    scores = {}
    patterns = {
        "ta":  r"\*?\*?TA[^:—–-]*[—–:-]\s*([\d.]+)",
        "cc":  r"\*?\*?CC[^:—–-]*[—–:-]\s*([\d.]+)",
        "lr":  r"\*?\*?LR[^:—–-]*[—–:-]\s*([\d.]+)",
        "gra": r"\*?\*?GRA[^:—–-]*[—–:-]\s*([\d.]+)",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            try:
                scores[key] = float(match.group(1))
            except ValueError:
                pass
    return scores


def word_count(text: str) -> int:
    return len(text.split())


# ─────────────────────────────────────────────
# CODE-BASED CHECKS (детерминированные)
# ─────────────────────────────────────────────

def check_overall_band_present(response: str) -> tuple[bool, str]:
    """Overall Band присутствует в ответе."""
    band = extract_overall_band(response)
    if band is not None:
        return True, f"Overall Band found: {band}"
    return False, "Overall Band not found in response"


def check_uses_ielts_scale(response: str) -> tuple[bool, str]:
    """Все band scores используют официальную IELTS шкалу."""
    all_scores = re.findall(r"(?:band|score|overall|TA|CC|LR|GRA)[^:—–\d]*([\d]+\.[\d]+)", response, re.IGNORECASE)
    invalid = []
    for s in all_scores:
        try:
            val = float(s)
            if 3.5 <= val <= 9.5 and val not in IELTS_VALID_BANDS:
                invalid.append(val)
        except ValueError:
            pass
    if invalid:
        return False, f"Invalid IELTS scores found: {invalid}"
    return True, "All scores use valid IELTS scale"


def check_band_cap_short_essay(response: str, essay: str) -> tuple[bool, str]:
    """Overall Band ≤ 4.5 если эссе < 150 слов."""
    wc = word_count(essay)
    if wc >= 150:
        return True, f"Essay is {wc} words — band cap not applicable"
    band = extract_overall_band(response)
    if band is None:
        return False, "Could not extract Overall Band to check cap"
    if band <= 4.5:
        return True, f"Band cap respected: {band} ≤ 4.5 for {wc}-word essay"
    return False, f"Band cap VIOLATED: {band} > 4.5 for {wc}-word essay"


def check_band_in_range(response: str, band_min: float = None, band_max: float = None) -> tuple[bool, str]:
    """Overall Band в ожидаемом диапазоне."""
    band = extract_overall_band(response)
    if band is None:
        return False, "Could not extract Overall Band"
    if band_min is not None and band < band_min:
        return False, f"Band {band} < expected min {band_min}"
    if band_max is not None and band > band_max:
        return False, f"Band {band} > expected max {band_max}"
    return True, f"Band {band} within expected range [{band_min}, {band_max}]"


def check_word_count_flag(response: str, essay: str) -> tuple[bool, str]:
    """Если эссе < 250 слов — флаг должен быть в ответе."""
    wc = word_count(essay)
    if wc >= 250:
        return True, f"Essay is {wc} words — flag not required"
    flag_present = (
        "⚠️" in response or
        "word count" in response.lower() or
        "words" in response.lower() and str(wc) in response
    )
    if flag_present:
        return True, f"Word count flag present for {wc}-word essay"
    return False, f"Word count flag MISSING for {wc}-word essay"


def check_all_criteria_scored(response: str) -> tuple[bool, str]:
    """Все 4 критерия присутствуют в ответе."""
    scores = extract_criterion_scores(response)
    missing = [k.upper() for k in ["ta", "cc", "lr", "gra"] if k not in scores]
    if not missing:
        return True, f"All 4 criteria scored: {scores}"
    return False, f"Missing criteria: {missing}"


def check_schema_complete(response: str) -> tuple[bool, str]:
    """Output schema полная: Overall Band + 4 критерия + Priority Focus + Exercise."""
    checks = {
        "Overall Band": bool(extract_overall_band(response)),
        "All criteria": len(extract_criterion_scores(response)) == 4,
        "Priority Focus": "priority" in response.lower() or "priority focus" in response.lower(),
        "Exercise": "exercise" in response.lower(),
    }
    failed = [k for k, v in checks.items() if not v]
    if not failed:
        return True, "Schema complete"
    return False, f"Schema incomplete — missing: {failed}"


# ─────────────────────────────────────────────
# PATTERN-BASED CHECKS (строковые)
# ─────────────────────────────────────────────

def check_cites_text(response: str, essay: str) -> tuple[bool, str]:
    """Фидбек цитирует конкретные фразы из эссе."""
    # Ищем слова из эссе (длиной > 5 символов) в кавычках внутри ответа
    essay_words = set(w.lower().strip('.,!?;:') for w in essay.split() if len(w) > 5)
    quoted_blocks = re.findall(r'["\*]{1,2}([^"\*]{10,})["\*]{1,2}', response)
    italic_blocks = re.findall(r'\*([^*]{10,})\*', response)
    all_quotes = quoted_blocks + italic_blocks

    for quote in all_quotes:
        quote_words = set(w.lower().strip('.,!?;:') for w in quote.split())
        overlap = essay_words & quote_words
        if len(overlap) >= 2:
            return True, f"Found citation with overlap: {list(overlap)[:3]}"

    # Fallback: ищем длинные фразы из эссе в ответе напрямую
    essay_phrases = [' '.join(essay.split()[i:i+4]) for i in range(len(essay.split())-3)]
    for phrase in essay_phrases:
        if phrase.lower() in response.lower():
            return True, f"Found essay phrase in response: '{phrase}'"

    return False, "No citations from essay text found in response"


def check_exercise_has_followup(response: str) -> tuple[bool, str]:
    """Exercise заканчивается фразой с приглашением прислать работу."""
    followup_phrases = [
        "submit your work here",
        "submit here",
        "send it here",
        "submit your",
        "share it here",
        "paste it here",
        "i will review it",
        "send your",
    ]
    response_lower = response.lower()
    for phrase in followup_phrases:
        if phrase in response_lower:
            return True, f"Follow-up phrase found: '{phrase}'"
    return False, "Exercise missing follow-up request ('Submit your work here...')"


def check_no_essay_written(response: str) -> tuple[bool, str]:
    """Агент не написал эссе за студента."""
    essay_markers = [
        "here is your essay",
        "here is an essay",
        "here is a band 7",
        "here is a revised",
        "here is the essay",
        "i have written",
        "i've written",
        "revised version:",
        "improved version:",
        "rewritten essay:",
        "band 7 essay:",
        "band 7 version:",
    ]
    response_lower = response.lower()
    for marker in essay_markers:
        if marker in response_lower:
            return False, f"Agent appears to have written an essay: '{marker}'"
    return True, "No essay written by agent"


def check_refusal_triggered(response: str) -> tuple[bool, str]:
    """Агент отказал в неподходящем запросе."""
    refusal_phrases = [
        "i can't write",
        "i cannot write",
        "i won't write",
        "i'm not able to write",
        "i can't complete",
        "i cannot complete",
        "i can't rewrite",
        "i cannot rewrite",
        "i can't help with that",
        "not able to",
        "unable to write",
        "unable to change",
        "won't be able to write",
        "decline",
        "that's not something i",
        "i'm unable to change",
        "i am unable to change",
        "cannot change",
        "can't change",
        "cannot adjust",
        "can't adjust",
        "i'm unable",
        "i am unable",
        "without an essay",
        "must be earned",
        "not something i can",
        "isn't something i can",
    ]
    response_lower = response.lower()
    for phrase in refusal_phrases:
        if phrase in response_lower:
            return True, f"Refusal phrase found: '{phrase}'"
    return False, "No refusal detected — agent may have complied with invalid request"


def check_offers_alternative(response: str) -> tuple[bool, str]:
    """После отказа агент предлагает альтернативу."""
    alternative_phrases = [
        "instead",
        "however",
        "what i can do",
        "i can help you",
        "here's what",
        "try this",
        "exercise:",
        "attempt",
        "write",
        "draft",
    ]
    response_lower = response.lower()
    for phrase in alternative_phrases:
        if phrase in response_lower:
            return True, f"Alternative offer found: '{phrase}'"
    return False, "No alternative offered after refusal"


def check_language_flag(response: str) -> tuple[bool, str]:
    """Агент распознал не-английский текст."""
    language_phrases = [
        "english",
        "please submit",
        "not in english",
        "written in",
        "language",
        "ielts requires",
    ]
    response_lower = response.lower()
    for phrase in language_phrases:
        if phrase in response_lower:
            return True, f"Language flag found: '{phrase}'"
    return False, "Language boundary not flagged for non-English essay"


def check_task1_flag(response: str) -> tuple[bool, str]:
    """Агент распознал Task 1 вместо Task 2."""
    task1_phrases = [
        "task 1",
        "task one",
        "bar chart",
        "graph",
        "data response",
        "optimised for task 2",
        "designed for task 2",
        "task 2 only",
    ]
    response_lower = response.lower()
    for phrase in task1_phrases:
        if phrase in response_lower:
            return True, f"Task 1 flag found: '{phrase}'"
    return False, "Task 1 input not flagged"


def check_minimum_length_warning(response: str) -> tuple[bool, str]:
    """Агент предупредил что эссе слишком короткое для оценки."""
    warning_phrases = [
        "too short",
        "not enough",
        "minimum",
        "at least",
        "cannot evaluate",
        "unable to evaluate",
        "meaningfully",
        "50 words",
        "please write",
    ]
    response_lower = response.lower()
    for phrase in warning_phrases:
        if phrase in response_lower:
            return True, f"Minimum length warning found: '{phrase}'"
    return False, "No minimum length warning for extremely short essay"


# ─────────────────────────────────────────────
# MASTER RUBRIC — применяет все нужные проверки
# ─────────────────────────────────────────────

def apply_rubric(response: str, essay: str, expected: dict) -> dict:
    """
    Применяет все релевантные проверки к ответу агента.
    Возвращает словарь с результатами каждой проверки.
    """
    results = {}

    # Всегда проверяем
    results["no_essay_written"] = check_no_essay_written(response)

    # Schema checks (только если ожидается оценка)
    if expected.get("all_criteria_scored", False):
        results["overall_band_present"]  = check_overall_band_present(response)
        results["uses_ielts_scale"]      = check_uses_ielts_scale(response)
        results["all_criteria_scored"]   = check_all_criteria_scored(response)
        results["schema_complete"]       = check_schema_complete(response)
        results["word_count_flag"]       = check_word_count_flag(response, essay)
        results["band_cap"]              = check_band_cap_short_essay(response, essay)
        results["exercise_has_followup"] = check_exercise_has_followup(response)

        if expected.get("cites_text"):
            results["cites_text"] = check_cites_text(response, essay)

        if "overall_band_max" in expected or "overall_band_min" in expected:
            results["band_in_range"] = check_band_in_range(
                response,
                expected.get("overall_band_min"),
                expected.get("overall_band_max")
            )

    # Edge case checks
    if expected.get("refusal_triggered"):
        results["refusal_triggered"] = check_refusal_triggered(response)

    if expected.get("offers_alternative"):
        results["offers_alternative"] = check_offers_alternative(response)

    if expected.get("language_flag"):
        results["language_flag"] = check_language_flag(response)

    if expected.get("task1_flag"):
        results["task1_flag"] = check_task1_flag(response)

    if expected.get("minimum_length_warning"):
        results["minimum_length_warning"] = check_minimum_length_warning(response)

    return results


def score_rubric(rubric_results: dict) -> tuple[int, int, list]:
    """Считает pass/fail по всем проверкам."""
    passed = sum(1 for v in rubric_results.values() if v[0])
    total  = len(rubric_results)
    failures = [
        f"FAIL [{k}]: {v[1]}"
        for k, v in rubric_results.items() if not v[0]
    ]
    return passed, total, failures
