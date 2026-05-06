"""
notifier.py — Tool 6 (Write)
Mock уведомление студенту о готовом фидбеке.
Write tool — требует idempotency key чтобы не отправить дважды.
"""
import sys, os, json, hashlib
from datetime import datetime
sys.path.insert(0, os.path.dirname(__file__))
from base import ToolResult

SCHEMA = {
    "name": "notifier",
    "description": (
        "Send a notification to the student that their essay feedback is ready. "
        "Use this ONLY after completing the full evaluation. "
        "Write tool — will not send duplicate notifications for the same session."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "user_id": {"type": "integer", "description": "Student's user ID"},
            "overall_band": {"type": "number", "description": "Final overall band score"},
            "session_id": {"type": "string", "description": "Unique session identifier for idempotency"}
        },
        "required": ["user_id", "overall_band", "session_id"]
    }
}

# Mock sent log — в production это была бы БД
_SENT_LOG: set = set()


def notifier(user_id: int, overall_band: float, session_id: str) -> ToolResult:
    # Idempotency check — Write tool не должен срабатывать дважды
    idempotency_key = f"{user_id}:{session_id}"
    if idempotency_key in _SENT_LOG:
        return ToolResult(
            success=True,
            data={
                "sent": False,
                "reason": "duplicate",
                "idempotency_key": idempotency_key,
                "message": "Notification already sent for this session"
            }
        )

    # Validate
    if overall_band not in {4.0,4.5,5.0,5.5,6.0,6.5,7.0,7.5,8.0,8.5,9.0}:
        return ToolResult(
            success=False,
            error="validation_error",
            message=f"Invalid band score: {overall_band}",
            suggested_action="Use an official IELTS band score"
        )

    # Mock send
    _SENT_LOG.add(idempotency_key)
    notification = {
        "to": f"user_{user_id}@gainscore.app",
        "subject": f"Your IELTS feedback is ready — Band {overall_band}",
        "body": (
            f"Hi! Your essay has been evaluated. "
            f"Overall Band: {overall_band}. "
            f"Log in to GainScore to see detailed feedback and your exercise."
        ),
        "sent_at": datetime.utcnow().isoformat(),
        "session_id": session_id
    }

    return ToolResult(
        success=True,
        data={"sent": True, "notification": notification, "idempotency_key": idempotency_key}
    )
