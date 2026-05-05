"""
judge_groundedness.py — Week 5
Проверяет: цитирует ли фидбек конкретные фразы из эссе студента?

Reference-free judge — нет эталонного ответа.
Вопрос: правильные ли слова выбраны для цитирования?

Отличие от rubric.py check_cites_text():
  rubric.py → проверяет есть ли любые слова из эссе в кавычках (regex)
  judge_groundedness → проверяет релевантны ли цитаты критерию (semantic)
"""

import json
import anthropic

client = anthropic.Anthropic()
MODEL = "claude-sonnet-4-6"

JUDGE_SYSTEM = """You are a strict evaluator assessing the quality of IELTS writing feedback.
Your job is to determine whether the feedback is properly grounded in the student's essay text.

You must output ONLY valid JSON. No preamble, no explanation outside the JSON.
"""

JUDGE_PROMPT = """Evaluate whether the IELTS writing feedback properly cites specific text from the student's essay.

<essay>
{essay}
</essay>

<feedback>
{feedback}
</feedback>

Evaluation criteria:
PASS if ALL of the following are true:
- At least 2 of the 4 criteria (TA, CC, LR, GRA) include a direct quote or clear reference to a specific phrase from the essay
- The citations are relevant to the criterion being discussed (e.g. a grammar quote under GRA, not under TA)
- Citations are specific (at least 4 words from the actual essay), not paraphrases

FAIL if ANY of the following are true:
- Fewer than 2 criteria cite the actual essay text
- Citations are generic (e.g. "your introduction" without quoting it)
- Quoted text does not appear in the essay

<example>
Essay excerpt: "Technology is good because it helps us communicate"
Feedback: **TA — 5.0:** "Technology is good because" → Your position is stated but underdeveloped
Verdict: PASS — specific quote, relevant to Task Achievement
</example>

<example>
Essay excerpt: "Technology is good because it helps us communicate"
Feedback: **TA — 5.0:** Your introduction mentions technology → Develop your argument more
Verdict: FAIL — no actual quote, generic reference
</example>

Respond with ONLY this JSON:
{{
  "verdict": "PASS" or "FAIL",
  "score": 0.0 to 1.0,
  "evidence": "paste the best citation you found, or 'none found'",
  "reasoning": "1-2 sentences explaining your verdict"
}}"""


def judge_groundedness(essay: str, feedback: str, n_runs: int = 1) -> dict:
    """
    Запускает groundedness judge.
    n_runs=3 для score smoothing (снижает variance).
    """
    scores = []
    verdicts = []
    evidences = []
    reasonings = []

    for _ in range(n_runs):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=300,
                system=JUDGE_SYSTEM,
                messages=[{
                    "role": "user",
                    "content": JUDGE_PROMPT.format(
                        essay=essay[:1000],
                        feedback=feedback[:1500]
                    )
                }]
            )
            raw = response.content[0].text.strip()
            # Убираем markdown fences если есть
            raw = raw.replace("```json", "").replace("```", "").strip()
            result = json.loads(raw)
            scores.append(result.get("score", 0.0))
            verdicts.append(result.get("verdict", "FAIL"))
            evidences.append(result.get("evidence", ""))
            reasonings.append(result.get("reasoning", ""))
        except Exception as e:
            scores.append(0.0)
            verdicts.append("FAIL")
            evidences.append("")
            reasonings.append(f"Error: {e}")

    # Score smoothing
    avg_score = sum(scores) / len(scores)
    final_verdict = "PASS" if avg_score >= 0.5 else "FAIL"

    return {
        "judge": "groundedness",
        "verdict": final_verdict,
        "score": round(avg_score, 2),
        "evidence": evidences[0],
        "reasoning": reasonings[0],
        "runs": n_runs,
        "raw_scores": scores
    }


if __name__ == "__main__":
    # Quick test
    test_essay = """Technology is very important in our lives today. 
    Many people use smartphones every day. Technology is good because it helps us communicate 
    with friends and family. However, some people think technology is bad because we spend 
    too much time on our phones. In conclusion, technology has both advantages and disadvantages."""

    test_feedback_good = """**Overall Band:** 4.5
⚠️ Word count: 83 words — under 250 minimum.

**TA — 4.0:** "technology has both advantages and disadvantages" → You state both sides exist but develop neither. Write one paragraph FOR technology with a specific example, and one AGAINST.
**CC — 5.0:** "However, some people think" → One contrast marker used correctly. Add variety: "Despite this," "On the other hand,"
**LR — 4.5:** "very important" → Replace with precise adjectives: indispensable, transformative, pervasive.
**GRA — 4.5:** "Technology is good because it helps us communicate" → Simple clause. Add complexity: "Technology, which has transformed communication, also raises concerns."

**Priority Focus:** Word count — reach 250 words first.
**Exercise:** Write two body paragraphs of 80-100 words each. Submit your work here and I will review it immediately."""

    test_feedback_bad = """**Overall Band:** 5.0

**TA — 5.0:** Your essay addresses the topic but needs more development.
**CC — 5.0:** The structure is adequate but could be improved.
**LR — 5.0:** Your vocabulary is basic. Try to use more advanced words.
**GRA — 5.0:** There are some grammar issues in your essay.

**Priority Focus:** Improve all areas.
**Exercise:** Rewrite the essay with better vocabulary. Submit your work here and I will review it immediately."""

    print("=== Judge Groundedness Test ===\n")

    print("Test 1: Good feedback (should PASS)")
    result1 = judge_groundedness(test_essay, test_feedback_good)
    print(f"Verdict: {result1['verdict']} | Score: {result1['score']}")
    print(f"Evidence: {result1['evidence'][:80]}...")
    print(f"Reasoning: {result1['reasoning']}\n")

    print("Test 2: Bad feedback (should FAIL)")
    result2 = judge_groundedness(test_essay, test_feedback_bad)
    print(f"Verdict: {result2['verdict']} | Score: {result2['score']}")
    print(f"Evidence: {result2['evidence']}")
    print(f"Reasoning: {result2['reasoning']}")
