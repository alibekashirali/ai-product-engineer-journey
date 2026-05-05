"""
judge_usefulness.py — Week 5
Проверяет: Exercise — конкретное письменное задание или общий совет?

Reference-free judge.
Именно этот judge поймал бы Gemini в Неделе 2 (давал списки вместо задания).

Отличие от rubric.py check_exercise_has_followup():
  rubric.py → проверяет есть ли фраза "Submit your work here" (string match)
  judge_usefulness → проверяет является ли Exercise педагогически ценным
"""

import json
import anthropic

client = anthropic.Anthropic()
MODEL = "claude-sonnet-4-6"

JUDGE_SYSTEM = """You are an expert IELTS teacher evaluating the quality of writing exercises 
assigned to students. Your job is to determine whether an exercise is pedagogically useful.

You must output ONLY valid JSON. No preamble, no explanation outside the JSON.
"""

JUDGE_PROMPT = """Evaluate whether the Exercise in this IELTS writing feedback is pedagogically useful.

<feedback>
{feedback}
</feedback>

Evaluation criteria:
PASS if ALL of the following are true:
- The Exercise is a concrete WRITING task (not a brainstorm list, not general advice)
- It has a specific, bounded scope (word count, number of sentences, or clear deliverable)
- The student can complete it right now in the chat
- It targets the specific weakness identified in the feedback

FAIL if ANY of the following are true:
- The Exercise is a list of ideas to think about ("brainstorm 3 ways to...")
- It gives general advice without a specific writing task ("study vocabulary")
- There is no Exercise section at all
- The Exercise asks the student to rewrite the entire essay (too broad)

<example>
Exercise: Write two body paragraphs of 80-100 words each. In each paragraph, include one specific named example (a real technology, statistic, or country). Submit your work here and I will review it immediately.
Verdict: PASS — concrete, bounded, specific, completable now
</example>

<example>
Exercise: Think about 3 ways technology helps people and 3 ways it is harmful. Then try to write a paragraph.
Verdict: FAIL — brainstorm list, no specific writing scope
</example>

<example>
Exercise: Improve your vocabulary by studying advanced words for technology topics.
Verdict: FAIL — general advice, not a writing task
</example>

Respond with ONLY this JSON:
{{
  "verdict": "PASS" or "FAIL",
  "score": 0.0 to 1.0,
  "evidence": "paste the Exercise text you found, or 'not found'",
  "reasoning": "1-2 sentences explaining your verdict"
}}"""


def judge_usefulness(feedback: str, n_runs: int = 1) -> dict:
    """
    Запускает usefulness judge на Exercise секцию фидбека.
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
                    "content": JUDGE_PROMPT.format(feedback=feedback[:2000])
                }]
            )
            raw = response.content[0].text.strip()
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

    avg_score = sum(scores) / len(scores)
    final_verdict = "PASS" if avg_score >= 0.5 else "FAIL"

    return {
        "judge": "usefulness",
        "verdict": final_verdict,
        "score": round(avg_score, 2),
        "evidence": evidences[0],
        "reasoning": reasonings[0],
        "runs": n_runs,
        "raw_scores": scores
    }


if __name__ == "__main__":
    feedback_claude = """**Priority Focus:** Word count — reach 250+ words with specific examples.
**Exercise:** Rewrite your two body paragraphs only. Each paragraph must be at least 90 words and contain one named, specific example (e.g. a real app, medical technology, or cited trend). Do not change your introduction or conclusion. Submit your work here and I will review it immediately."""

    feedback_gemini = """**Priority Focus:** Expand your arguments.
**Exercise:** Make a list of 3 benefits of technology and 3 drawbacks. Think about specific examples for each. Then try writing one of them as a full paragraph."""

    feedback_generic = """**Priority Focus:** Improve all criteria.
**Exercise:** Study vocabulary related to technology and practice writing more complex sentences. Focus on grammar accuracy."""

    print("=== Judge Usefulness Test ===\n")

    print("Test 1: Claude-style exercise (should PASS)")
    r1 = judge_usefulness(feedback_claude)
    print(f"Verdict: {r1['verdict']} | Score: {r1['score']}")
    print(f"Reasoning: {r1['reasoning']}\n")

    print("Test 2: Gemini-style brainstorm (should FAIL)")
    r2 = judge_usefulness(feedback_gemini)
    print(f"Verdict: {r2['verdict']} | Score: {r2['score']}")
    print(f"Reasoning: {r2['reasoning']}\n")

    print("Test 3: Generic advice (should FAIL)")
    r3 = judge_usefulness(feedback_generic)
    print(f"Verdict: {r3['verdict']} | Score: {r3['score']}")
    print(f"Reasoning: {r3['reasoning']}")
