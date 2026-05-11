"""
email_mock.py — mock email нотификации (SMTP).
В production: заменить на smtplib или SendGrid API (уже в стеке GainScore).
"""
from datetime import datetime


class EmailNotifier:
    def __init__(self, to: str = "team@example.com",
                 from_addr: str = "pipeline@gainscore.app"):
        self.to = to
        self.from_addr = from_addr

    def notify(self, result) -> dict:
        """Отправляет email summary после run."""
        subject = (f"[{'✅ PASS' if result.success else '❌ FAIL'}] "
                   f"Pipeline Report: {result.topic[:40]}")
        body = f"""Pipeline Run Complete
{'='*50}
Run ID:   {result.run_id}
Topic:    {result.topic}
Quality:  {result.quality} (score: {result.score:.2f})
Time:     {result.elapsed_s:.0f}s
Words:    {result.word_count}
Tokens:   ~{result.cost_tokens}
{'ERROR: ' + result.error if result.error else ''}

Brief Preview:
{'-'*50}
{result.brief[:400]}...

View full report in ops dashboard.
"""
        print(f"  [EmailNotifier] 📧 Would send email:")
        print(f"    To: {self.to}")
        print(f"    Subject: {subject}")
        print(f"    Body: {len(body)} chars")
        return {
            "status": "mock_sent",
            "to": self.to,
            "subject": subject,
            "body_length": len(body)
        }

    def weekly_summary(self, history: list[dict]) -> dict:
        """Еженедельный сводный отчёт по всем runs."""
        if not history:
            return {"status": "no_data"}

        total = len(history)
        passed = sum(1 for r in history if r.get("quality") == "PASS")
        avg_score = sum(float(r.get("score", 0)) for r in history) / total
        avg_time = sum(float(r.get("elapsed_s", 0)) for r in history) / total

        subject = f"Weekly Pipeline Summary — {passed}/{total} passed"
        body = f"""Weekly Summary ({datetime.utcnow().strftime('%Y-%m-%d')})
{'='*50}
Total runs:    {total}
Passed:        {passed} ({passed/total*100:.0f}%)
Avg score:     {avg_score:.2f}
Avg time:      {avg_time:.0f}s

Topics covered:
{chr(10).join('  - ' + r.get('topic','')[:50] for r in history[-5:])}
"""
        print(f"  [EmailNotifier] 📊 Weekly summary: {passed}/{total} passed, avg_score={avg_score:.2f}")
        return {"status": "mock_sent", "subject": subject}
