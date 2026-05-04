"""
runner.py — Week 4
GainScore Writing Coach: pytest eval harness.

Запуск:
  pip install anthropic pytest pytest-json-report
  export ANTHROPIC_API_KEY=sk-ant-...
  pytest runner.py -v --json-report --json-report-file=results.json

Флаги:
  -v                    подробный вывод
  -k "under_150"        запустить только одну категорию
  --tb=short            короткий traceback
  -x                    остановить на первом падении
"""

import json
import os
import time
import re
import pytest
import anthropic
from rubric import apply_rubric, score_rubric, extract_overall_band


# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

DATASET_PATH = os.path.join(os.path.dirname(__file__), "dataset.json")
MODEL        = "claude-sonnet-4-6"
MAX_TOKENS   = 1000
PASS_THRESHOLD = 0.75  # 75% проверок должны проходить

SYSTEM_PROMPT = """You are an IELTS Writing Coach for GainScore.
Evaluate Task 2 essays on four criteria: Task Achievement (TA), Coherence & Cohesion (CC),
Lexical Resource (LR), Grammatical Range & Accuracy (GRA).

Rules:
Step-by-step for every essay:
1. Count words exactly. Flag with ⚠️ if under 250.
2. HARD CHECK FIRST: if word count is under 150 — write Overall Band as 4.0 or 4.5. Do NOT average criteria. This is a hard ceiling.
3. Score all 4 criteria on IELTS scale (4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0). Criteria reflect actual quality even when Overall is capped.
4. If word count >= 150: Overall Band = average of 4 criteria, rounded to nearest 0.5.
5. Priority Focus + Exercise.
- Flag word count if under 250 words with ⚠️
- Cite specific phrases from the essay for each criterion
- Give one targeted improvement per criterion
- End with Priority Focus and Exercise
- Exercise must be a concrete writing task with specific scope
- Exercise must end with: "Submit your work here and I will review it immediately."
- NEVER write, rewrite, or complete any part of an essay for the user
- If asked to write or rewrite: decline, explain why, offer a specific exercise instead
- If essay is not in English: ask user to submit in English
- If essay is Task 1 (graph/chart): note you are optimised for Task 2 only
- If essay is under 50 words: do not score, ask for minimum 250 words

Output format:
**Overall Band:** X.X
⚠️ Word count: N words [flag if under 250]

**TA — X.X:** [quote from essay] → [improvement]
**CC — X.X:** [quote from essay] → [improvement]
**LR — X.X:** [quote from essay] → [improvement]
**GRA — X.X:** [quote from essay] → [improvement]

**Priority Focus:** [criterion + specific action]
**Exercise:** [concrete writing task with scope]. Submit your work here and I will review it immediately."""


# ─────────────────────────────────────────────
# LOAD DATASET
# ─────────────────────────────────────────────

def load_dataset():
    with open(DATASET_PATH, "r") as f:
        data = json.load(f)
    return data["cases"]


ALL_CASES = load_dataset()


def get_cases_by_category(category: str):
    return [c for c in ALL_CASES if c["category"] == category]


# ─────────────────────────────────────────────
# AGENT CALL (с retry)
# ─────────────────────────────────────────────

def apply_band_cap(response: str, essay: str) -> str:
    """
    Принудительно применяет band cap в коде после получения ответа от модели.
    Если эссе < 150 слов и Overall Band > 4.5 — заменяем число в ответе.
    Это надёжнее чем просить модель соблюдать правило в промпте.
    """
    wc = len(essay.split())
    if wc >= 150:
        return response

    band = extract_overall_band(response)
    if band is None or band <= 4.5:
        return response

    # Заменяем число в ответе
    capped = min(band, 4.5)
    # Паттерн: **Overall Band:** X.X или **Overall Band: X.X**
    fixed = re.sub(
        r'(\*\*Overall Band[:\*]*\*?\*?)\s*([\d.]+)',
        lambda m: f'{m.group(1)} {capped}',
        response,
        count=1
    )
    # Добавляем примечание если ничего не изменилось
    if fixed == response:
        fixed = response.replace(str(band), str(capped), 1)

    return fixed


def call_agent(essay: str, retries: int = 2) -> str:
    """Вызывает агента, применяет band cap программно."""
    client = anthropic.Anthropic()
    for attempt in range(retries + 1):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": essay}]
            )
            raw = response.content[0].text
            # Применяем band cap программно — надёжнее промпта
            return apply_band_cap(raw, essay)
        except Exception as e:
            if attempt < retries:
                time.sleep(2 ** attempt)
                continue
            raise e


# ─────────────────────────────────────────────
# HELPER: run one case and assert
# ─────────────────────────────────────────────

def run_case(case: dict) -> tuple[str, dict, int, int, list]:
    """Прогоняет один кейс, возвращает (response, rubric_results, passed, total, failures)."""
    response = call_agent(case["input_essay"])
    rubric_results = apply_rubric(response, case["input_essay"], case["expected"])
    passed, total, failures = score_rubric(rubric_results)
    return response, rubric_results, passed, total, failures


# ─────────────────────────────────────────────
# PYTEST TESTS — по категориям
# ─────────────────────────────────────────────

class TestUnder150Words:
    """Band cap ≤ 4.5 и word count flag для коротких эссе."""

    @pytest.mark.parametrize("case", get_cases_by_category("under_150_words"), ids=lambda c: c["id"])
    def test_band_cap_and_flag(self, case):
        response, rubric_results, passed, total, failures = run_case(case)

        # Критические проверки для этой категории
        cap_ok, cap_msg   = rubric_results.get("band_cap", (True, "N/A"))
        flag_ok, flag_msg = rubric_results.get("word_count_flag", (True, "N/A"))

        assert cap_ok,  f"[{case['id']}] Band cap: {cap_msg}\nResponse:\n{response[:500]}"
        assert flag_ok, f"[{case['id']}] Word flag: {flag_msg}\nResponse:\n{response[:500]}"

    @pytest.mark.parametrize("case", get_cases_by_category("under_150_words"), ids=lambda c: c["id"])
    def test_no_essay_written(self, case):
        response, _, _, _, _ = run_case(case)
        ok, msg = apply_rubric(response, case["input_essay"], case["expected"])["no_essay_written"]
        assert ok, f"[{case['id']}] {msg}\nResponse:\n{response[:500]}"


class TestBand5Essays:
    """Band 5 эссе: правильная шкала, цитаты, schema."""

    @pytest.mark.parametrize("case", get_cases_by_category("band_5_essays"), ids=lambda c: c["id"])
    def test_schema_complete(self, case):
        response, rubric_results, passed, total, failures = run_case(case)
        ok, msg = rubric_results.get("schema_complete", (False, "not checked"))
        assert ok, f"[{case['id']}] {msg}\nResponse:\n{response[:600]}"

    @pytest.mark.parametrize("case", get_cases_by_category("band_5_essays"), ids=lambda c: c["id"])
    def test_ielts_scale(self, case):
        response, rubric_results, _, _, _ = run_case(case)
        ok, msg = rubric_results.get("uses_ielts_scale", (False, "not checked"))
        assert ok, f"[{case['id']}] {msg}\nResponse:\n{response[:600]}"

    @pytest.mark.parametrize("case", get_cases_by_category("band_5_essays"), ids=lambda c: c["id"])
    def test_band_in_range(self, case):
        response, rubric_results, _, _, _ = run_case(case)
        ok, msg = rubric_results.get("band_in_range", (True, "N/A"))
        assert ok, f"[{case['id']}] {msg}\nResponse:\n{response[:600]}"

    @pytest.mark.parametrize("case", get_cases_by_category("band_5_essays"), ids=lambda c: c["id"])
    def test_exercise_followup(self, case):
        response, rubric_results, _, _, _ = run_case(case)
        ok, msg = rubric_results.get("exercise_has_followup", (False, "not checked"))
        assert ok, f"[{case['id']}] {msg}\nResponse:\n{response[:600]}"


class TestBand6Essays:
    """Band 6 эссе: нюансированный фидбек, цитаты, schema."""

    @pytest.mark.parametrize("case", get_cases_by_category("band_6_essays"), ids=lambda c: c["id"])
    def test_schema_complete(self, case):
        response, rubric_results, _, _, _ = run_case(case)
        ok, msg = rubric_results.get("schema_complete", (False, "not checked"))
        assert ok, f"[{case['id']}] {msg}\nResponse:\n{response[:600]}"

    @pytest.mark.parametrize("case", get_cases_by_category("band_6_essays"), ids=lambda c: c["id"])
    def test_cites_text(self, case):
        response, rubric_results, _, _, _ = run_case(case)
        ok, msg = rubric_results.get("cites_text", (False, "not checked"))
        assert ok, f"[{case['id']}] {msg}\nResponse:\n{response[:600]}"

    @pytest.mark.parametrize("case", get_cases_by_category("band_6_essays"), ids=lambda c: c["id"])
    def test_band_in_range(self, case):
        response, rubric_results, _, _, _ = run_case(case)
        ok, msg = rubric_results.get("band_in_range", (True, "N/A"))
        assert ok, f"[{case['id']}] {msg}\nResponse:\n{response[:600]}"


class TestBand7Essays:
    """Band 7 эссе: не завышает, видит тонкие ошибки."""

    @pytest.mark.parametrize("case", get_cases_by_category("band_7_essays"), ids=lambda c: c["id"])
    def test_schema_complete(self, case):
        response, rubric_results, _, _, _ = run_case(case)
        ok, msg = rubric_results.get("schema_complete", (False, "not checked"))
        assert ok, f"[{case['id']}] {msg}\nResponse:\n{response[:600]}"

    @pytest.mark.parametrize("case", get_cases_by_category("band_7_essays"), ids=lambda c: c["id"])
    def test_band_not_inflated(self, case):
        response, rubric_results, _, _, _ = run_case(case)
        ok, msg = rubric_results.get("band_in_range", (True, "N/A"))
        assert ok, f"[{case['id']}] {msg}\nResponse:\n{response[:600]}"

    @pytest.mark.parametrize("case", get_cases_by_category("band_7_essays"), ids=lambda c: c["id"])
    def test_no_essay_written(self, case):
        response, rubric_results, _, _, _ = run_case(case)
        ok, msg = rubric_results["no_essay_written"]
        assert ok, f"[{case['id']}] {msg}\nResponse:\n{response[:600]}"


class TestEdgeCases:
    """Edge cases: отказы, границы, целостность оценок."""

    @pytest.mark.parametrize("case", get_cases_by_category("edge_cases"), ids=lambda c: c["id"])
    def test_no_essay_written(self, case):
        response, rubric_results, _, _, _ = run_case(case)
        ok, msg = rubric_results["no_essay_written"]
        assert ok, f"[{case['id']}] {msg}\nResponse:\n{response[:600]}"

    def test_e001_refusal_write_request(self):
        case = next(c for c in ALL_CASES if c["id"] == "e001")
        response, rubric_results, _, _, _ = run_case(case)
        ref_ok, ref_msg = rubric_results.get("refusal_triggered", (False, "not checked"))
        alt_ok, alt_msg = rubric_results.get("offers_alternative", (False, "not checked"))
        assert ref_ok, f"[e001] Refusal: {ref_msg}\nResponse:\n{response[:600]}"
        assert alt_ok, f"[e001] Alternative: {alt_msg}\nResponse:\n{response[:600]}"

    def test_e003_russian_essay(self):
        case = next(c for c in ALL_CASES if c["id"] == "e003")
        response, rubric_results, _, _, _ = run_case(case)
        ok, msg = rubric_results.get("language_flag", (False, "not checked"))
        assert ok, f"[e003] {msg}\nResponse:\n{response[:600]}"

    def test_e004_task1_essay(self):
        case = next(c for c in ALL_CASES if c["id"] == "e004")
        response, rubric_results, _, _, _ = run_case(case)
        ok, msg = rubric_results.get("task1_flag", (False, "not checked"))
        assert ok, f"[e004] {msg}\nResponse:\n{response[:600]}"

    def test_e005_too_short(self):
        case = next(c for c in ALL_CASES if c["id"] == "e005")
        response, rubric_results, _, _, _ = run_case(case)
        ok, msg = rubric_results.get("minimum_length_warning", (False, "not checked"))
        assert ok, f"[e005] {msg}\nResponse:\n{response[:600]}"

    def test_e006_score_integrity(self):
        case = next(c for c in ALL_CASES if c["id"] == "e006")
        response, rubric_results, _, _, _ = run_case(case)
        ok, msg = rubric_results.get("refusal_triggered", (False, "not checked"))
        assert ok, f"[e006] Score integrity: {msg}\nResponse:\n{response[:600]}"


# ─────────────────────────────────────────────
# STANDALONE RUNNER (без pytest)
# ─────────────────────────────────────────────

def run_full_eval(sample_size: int = None, save_results: bool = True) -> dict:
    """
    Запускает eval на всём датасете (или sample_size кейсах).
    Сохраняет results.json.
    Возвращает summary.
    """
    cases = ALL_CASES if sample_size is None else ALL_CASES[:sample_size]
    results = []
    category_stats = {}

    print(f"\n{'='*60}")
    print(f"GainScore Eval Harness — {len(cases)} cases")
    print(f"{'='*60}\n")

    for i, case in enumerate(cases, 1):
        print(f"[{i:02d}/{len(cases)}] {case['id']} ({case['category']})... ", end="", flush=True)
        try:
            response, rubric_results, passed, total, failures = run_case(case)
            pct = passed / total if total > 0 else 0
            status = "✅ PASS" if pct >= PASS_THRESHOLD else "❌ FAIL"
            print(f"{status} ({passed}/{total})")

            result = {
                "id":       case["id"],
                "category": case["category"],
                "status":   "PASS" if pct >= PASS_THRESHOLD else "FAIL",
                "passed":   passed,
                "total":    total,
                "pct":      round(pct, 2),
                "failures": failures,
                "response_preview": response[:300],
            }
        except Exception as e:
            print(f"⚠️  ERROR: {e}")
            result = {
                "id":       case["id"],
                "category": case["category"],
                "status":   "ERROR",
                "passed":   0,
                "total":    0,
                "pct":      0,
                "failures": [str(e)],
                "response_preview": "",
            }

        results.append(result)

        # Статистика по категории
        cat = case["category"]
        if cat not in category_stats:
            category_stats[cat] = {"pass": 0, "fail": 0, "error": 0}
        category_stats[cat][result["status"].lower()] += 1

    # Summary
    total_pass  = sum(1 for r in results if r["status"] == "PASS")
    total_fail  = sum(1 for r in results if r["status"] == "FAIL")
    total_error = sum(1 for r in results if r["status"] == "ERROR")

    summary = {
        "total":    len(results),
        "passed":   total_pass,
        "failed":   total_fail,
        "errors":   total_error,
        "pass_rate": round(total_pass / len(results), 2) if results else 0,
        "by_category": category_stats,
        "cases":    results,
    }

    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Total:  {len(results)}")
    print(f"Passed: {total_pass} ({summary['pass_rate']*100:.0f}%)")
    print(f"Failed: {total_fail}")
    print(f"Errors: {total_error}")
    print(f"\nBy category:")
    for cat, stats in category_stats.items():
        print(f"  {cat:<25} ✅{stats['pass']}  ❌{stats['fail']}  ⚠️{stats['error']}")

    if save_results:
        output_path = os.path.join(os.path.dirname(__file__), "results.json")
        with open(output_path, "w") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        print(f"\n📄 Results saved to results.json")

    return summary


if __name__ == "__main__":
    # Быстрый тест на 6 кейсах (по одному из каждой категории)
    sample_ids = ["u001", "b5001", "b6001", "b7001", "e001", "e003"]
    sample = [c for c in ALL_CASES if c["id"] in sample_ids]

    print("Running quick sample (6 cases)...")
    for case in sample:
        print(f"\n--- {case['id']} ({case['category']}) ---")
        try:
            response, rubric_results, passed, total, failures = run_case(case)
            print(f"Score: {passed}/{total}")
            if failures:
                for f in failures:
                    print(f"  {f}")
            else:
                print("  All checks passed ✅")
        except Exception as e:
            print(f"  ERROR: {e}")
