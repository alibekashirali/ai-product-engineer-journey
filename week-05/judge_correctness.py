"""
judge_correctness.py — Week 5
Проверяет: соответствуют ли band scores реальному уровню эссе?

Reference-based judge — сравниваем с ожидаемым диапазоном из dataset.json.
Вопрос: правильный ли уровень, или агент завышает/занижает?

Отличие от rubric.py check_band_in_range():
  rubric.py → проверяет числовой диапазон (механически)
  judge_correctness → проверяет обоснованность оценки (семантически)
"""

import json
import anthropic

client = anthropic.Anthropic()
MODEL = "claude-sonnet-4-6"

JUDGE_SYSTEM = """You are a senior IELTS examiner with 10+ years of experience.
Your job is to verify whether band scores assigned to an essay are accurate and justified.

You must output ONLY valid JSON. No preamble, no explanation outside the JSON.
"""

JUDGE_PROMPT = """Evaluate whether the band scores in this feedback accurately reflect the essay quality.

<essay>
{essay}
</essay>

<feedback>
{feedback}
</feedback>

<expected_range>
Overall Band expected: {band_min} to {band_max}
</expected_range>

Evaluation criteria:
PASS if ALL of the following are true:
- The Overall Band score is within the expected range ({band_min}-{band_max})
- The individual criterion scores are plausible given the essay text
- There is no obvious score inflation (giving high scores to a weak essay)
- There is no obvious score deflation (giving low scores to a strong essay)

FAIL if ANY of the following are true:
- Overall Band is outside the expected range
- Criterion scores contradict the essay quality (e.g. GRA 7.0 for an essay with many grammar errors)
- Score inflation detected: essay is weak but scores are consistently high
- Score deflation detected: essay is strong but scores are consistently low

Focus on Overall Band accuracy first, then check if criterion scores are internally consistent.

Respond with ONLY this JSON:
{{
  "verdict": "PASS" or "FAIL",
  "score": 0.0 to 1.0,
  "overall_band_found": "the Overall Band from feedback, as a number",
  "evidence": "quote the most problematic score + reason, or 'scores appear accurate'",
  "reasoning": "1-2 sentences explaining your verdict"
}}"""


def judge_correctness(essay: str, feedback: str,
                      band_min: float = None, band_max: float = None,
                      n_runs: int = 1) -> dict:
    """
    Запускает correctness judge.
    band_min/band_max из dataset.json expected поля.
    """
    scores = []
    verdicts = []
    evidences = []
    reasonings = []
    bands_found = []

    range_str = f"{band_min or '?'} to {band_max or '?'}"

    for _ in range(n_runs):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=300,
                system=JUDGE_SYSTEM,
                messages=[{
                    "role": "user",
                    "content": JUDGE_PROMPT.format(
                        essay=essay[:1200],
                        feedback=feedback[:1500],
                        band_min=band_min or "not specified",
                        band_max=band_max or "not specified"
                    )
                }]
            )
            raw = response.content[0].text.strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            result = json.loads(raw)
            scores.append(result.get("score", 0.0))
            verdicts.append(result.get("verdict", "FAIL"))
            evidences.append(result.get("evidence", ""))
            reasonings.append(result.get("reasoning", ""))
            bands_found.append(result.get("overall_band_found", "unknown"))
        except Exception as e:
            scores.append(0.0)
            verdicts.append("FAIL")
            evidences.append("")
            reasonings.append(f"Error: {e}")
            bands_found.append("unknown")

    avg_score = sum(scores) / len(scores)
    final_verdict = "PASS" if avg_score >= 0.5 else "FAIL"

    return {
        "judge": "correctness",
        "verdict": final_verdict,
        "score": round(avg_score, 2),
        "overall_band_found": bands_found[0],
        "expected_range": f"{band_min}-{band_max}",
        "evidence": evidences[0],
        "reasoning": reasonings[0],
        "runs": n_runs,
        "raw_scores": scores
    }


if __name__ == "__main__":
    weak_essay = """Technology is very important in our lives today.
    Many people use smartphones every day. Technology is good because it helps us communicate
    with friends and family. However, some people think technology is bad because we spend
    too much time on our phones. In conclusion, technology has both advantages and disadvantages."""

    strong_essay = """The question of whether individuals or governments bear greater responsibility 
    for protecting the environment has become increasingly urgent in the face of accelerating climate change. 
    While individual choices undoubtedly have an impact, I would argue that systemic change driven by 
    government policy is ultimately more decisive. Governments possess the legislative and fiscal tools 
    necessary to drive large-scale change. Carbon pricing mechanisms, renewable energy subsidies, and 
    stricter emissions regulations can restructure entire economies. Scandinavian countries have demonstrated 
    that ambitious climate policies can significantly reduce national carbon footprints without sacrificing 
    economic prosperity."""

    feedback_correct = """**Overall Band:** 4.5
⚠️ Word count: 83 words — under 250 minimum.
**TA — 4.0:** "technology has both advantages and disadvantages" → Both sides mentioned but not developed.
**CC — 5.0:** "However, some people think" → One marker used.
**LR — 4.5:** "very important" → Too basic for Band 6+.
**GRA — 4.5:** All simple sentences — no complex structures.
**Priority Focus:** Word count first.
**Exercise:** Write two body paragraphs. Submit your work here and I will review it immediately."""

    feedback_inflated = """**Overall Band:** 7.0
**TA — 7.0:** Great job addressing both sides of the argument thoroughly.
**CC — 7.0:** Excellent paragraph structure and logical flow throughout.
**LR — 7.0:** Good range of vocabulary used effectively.
**GRA — 7.0:** Complex sentences used accurately with minimal errors.
**Priority Focus:** Keep up the good work!
**Exercise:** Submit your work here and I will review it immediately."""

    print("=== Judge Correctness Test ===\n")

    print("Test 1: Correct scores for weak essay (should PASS)")
    r1 = judge_correctness(weak_essay, feedback_correct, band_min=4.0, band_max=5.0)
    print(f"Verdict: {r1['verdict']} | Score: {r1['score']} | Band found: {r1['overall_band_found']}")
    print(f"Reasoning: {r1['reasoning']}\n")

    print("Test 2: Inflated scores for weak essay (should FAIL)")
    r2 = judge_correctness(weak_essay, feedback_inflated, band_min=4.0, band_max=5.0)
    print(f"Verdict: {r2['verdict']} | Score: {r2['score']} | Band found: {r2['overall_band_found']}")
    print(f"Evidence: {r2['evidence']}")
    print(f"Reasoning: {r2['reasoning']}\n")

    print("Test 3: Correct scores for strong essay (should PASS)")
    feedback_strong = """**Overall Band:** 7.0
**TA — 7.0:** "systemic change driven by government policy is ultimately more decisive" → Clear position, well-supported.
**CC — 7.0:** Logical flow from individual to government responsibility.
**LR — 7.5:** "legislative and fiscal tools", "restructure entire economies" — precise collocations.
**GRA — 7.0:** Complex clauses used accurately throughout.
**Priority Focus:** Develop the individual responsibility counterargument more fully.
**Exercise:** Add one paragraph acknowledging individual action. Submit your work here and I will review it immediately."""
    r3 = judge_correctness(strong_essay, feedback_strong, band_min=6.5, band_max=7.5)
    print(f"Verdict: {r3['verdict']} | Score: {r3['score']} | Band found: {r3['overall_band_found']}")
    print(f"Reasoning: {r3['reasoning']}")
