from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class ToolResult:
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    message: Optional[str] = None
    suggested_action: Optional[str] = None
    example_valid_call: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "message": self.message,
            "suggested_action": self.suggested_action,
            "example_valid_call": self.example_valid_call,
        }
