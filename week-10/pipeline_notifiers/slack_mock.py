"""
slack_mock.py — mock Slack webhook уведомления.
В production: заменить requests.post(SLACK_WEBHOOK_URL, json=payload)
"""
import json
from datetime import datetime

QUALITY_THRESHOLD = 0.65


class SlackNotifier:
    def __init__(self, webhook_url: str = "https://hooks.slack.com/MOCK",
                 channel: str = "#ai-pipeline"):
        self.webhook_url = webhook_url
        self.channel = channel

    def notify(self, result) -> dict:
        """Отправляет нотификацию о завершении run."""
        emoji = "✅" if result.success else "❌"
        color = "good" if result.success else "danger"

        payload = {
            "channel": self.channel,
            "username": "Pipeline Bot",
            "icon_emoji": ":robot_face:",
            "attachments": [{
                "color": color,
                "title": f"{emoji} Pipeline Run Complete",
                "fields": [
                    {"title": "Topic",   "value": result.topic[:50], "short": True},
                    {"title": "Quality", "value": f"{result.quality} ({result.score:.2f})", "short": True},
                    {"title": "Time",    "value": f"{result.elapsed_s:.0f}s", "short": True},
                    {"title": "Words",   "value": str(result.word_count), "short": True},
                    {"title": "Run ID",  "value": result.run_id, "short": False},
                ],
                "footer": f"AI Market Intelligence Copilot | {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC"
            }]
        }

        if result.error:
            payload["attachments"][0]["fields"].append(
                {"title": "Error", "value": result.error[:100], "short": False}
            )

        print(f"  [SlackNotifier] 📨 Would POST to Slack {self.channel}:")
        print(f"    {emoji} {result.quality} · score={result.score:.2f} · {result.elapsed_s:.0f}s · '{result.topic[:40]}'")
        return {"status": "mock_sent", "payload": payload}

    def alert(self, level: str, message: str, run_id: str = "") -> dict:
        """Алерт для critical issues — silent failures, low quality, etc."""
        emoji = "🚨" if level == "critical" else "⚠️"
        payload = {
            "channel": self.channel,
            "text": f"{emoji} *[{level.upper()}]* {message}",
            "attachments": [{
                "color": "danger" if level == "critical" else "warning",
                "text": f"Run ID: `{run_id}`" if run_id else ""
            }]
        }
        print(f"  [SlackNotifier] {emoji} ALERT [{level}]: {message}")
        return {"status": "mock_alert_sent", "payload": payload}
