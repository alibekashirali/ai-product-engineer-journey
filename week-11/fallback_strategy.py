"""
fallback_strategy.py — Multi-model fallback с circuit breaker.
Primary: Claude Sonnet 4.6
Critic:  GPT-4o (независимая архитектура)
Fallback: Gemini 1.5 Flash (дешевле)
Last: Demo cache
"""
import time
import os
from dataclasses import dataclass, field
from typing import Optional
import anthropic

# ─────────────────────────────────────────────
# CIRCUIT BREAKER
# ─────────────────────────────────────────────
@dataclass
class CircuitBreaker:
    name:       str
    threshold:  int   = 3      # сколько ошибок до открытия
    timeout_s:  float = 60.0   # как долго circuit открыт
    failures:   int   = field(default=0, init=False)
    opened_at:  Optional[float] = field(default=None, init=False)
    state:      str   = field(default="closed", init=False)  # closed|open|half-open

    def can_call(self) -> bool:
        if self.state == "closed":
            return True
        if self.state == "open":
            if time.time() - self.opened_at > self.timeout_s:
                self.state = "half-open"
                return True
            return False
        return True  # half-open — пробуем

    def record_success(self):
        self.failures = 0
        self.state = "closed"
        self.opened_at = None

    def record_failure(self):
        self.failures += 1
        if self.failures >= self.threshold:
            self.state = "open"
            self.opened_at = time.time()
            print(f"  [CircuitBreaker] ⚡ {self.name} OPEN after {self.failures} failures")


# ─────────────────────────────────────────────
# MODEL CONFIGS
# ─────────────────────────────────────────────
MODELS = {
    "primary":  "claude-sonnet-4-6",
    "critic":   "claude-sonnet-4-6",   # в prod: gpt-4o через openai client
    "fallback": "claude-sonnet-4-6",   # в prod: gemini-1.5-flash через google client
}

_breakers: dict[str, CircuitBreaker] = {
    name: CircuitBreaker(name=name) for name in MODELS
}

_anthropic = anthropic.Anthropic()

DEMO_RESPONSES = {
    "generic": "## Executive Summary\nMarket analysis complete. Key findings: strong growth, competitive landscape, clear opportunities.",
}


# ─────────────────────────────────────────────
# CORE CALL FUNCTION
# ─────────────────────────────────────────────
def call_with_fallback(
    system: str,
    user: str,
    max_tokens: int = 1000,
    temperature: float = 0.3,
    role: str = "primary",
    timeout: float = 30.0
) -> tuple[str, str]:
    """
    Вызывает модель с fallback цепочкой.
    Возвращает (response_text, model_used).

    Порядок:
      1. Primary (Claude Sonnet)
      2. Critic/Fallback (другой провайдер)
      3. Demo cache
    """
    chain = [role, "critic" if role == "primary" else "primary", "fallback"]

    for tier_name in chain:
        model = MODELS.get(tier_name, MODELS["primary"])
        breaker = _breakers[tier_name]

        if not breaker.can_call():
            print(f"  [Fallback] ⚡ {tier_name} circuit OPEN, skipping")
            continue

        try:
            print(f"  [Fallback] Trying {tier_name} ({model})...")
            response = _anthropic.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}]
            )
            text = response.content[0].text
            breaker.record_success()
            print(f"  [Fallback] ✅ {tier_name} succeeded")
            return text, model

        except Exception as e:
            breaker.record_failure()
            print(f"  [Fallback] ❌ {tier_name} failed: {type(e).__name__}: {e}")
            continue

    # Last resort — demo cache
    print(f"  [Fallback] 🔄 Using demo cache (all models failed)")
    return DEMO_RESPONSES["generic"], "demo_cache"


# ─────────────────────────────────────────────
# CONFIDENCE-BASED ROUTING
# ─────────────────────────────────────────────
def route_by_confidence(score: float, run_id: str = "") -> str:
    """
    Паттерн 'Fail Fast, or Ask'.
    Возвращает routing decision.
    """
    AUTO_APPROVE  = 0.85
    HUMAN_REVIEW  = 0.65

    if score >= AUTO_APPROVE:
        print(f"  [Router] ✅ AUTO APPROVE (score={score:.2f})")
        return "auto_approve"
    elif score >= HUMAN_REVIEW:
        print(f"  [Router] 👤 HUMAN REVIEW (score={score:.2f})")
        return "human_review"
    else:
        print(f"  [Router] ❌ AUTO REJECT (score={score:.2f})")
        return "auto_reject"


def get_breaker_status() -> dict:
    """Возвращает статус всех circuit breakers."""
    return {
        name: {"state": b.state, "failures": b.failures}
        for name, b in _breakers.items()
    }


if __name__ == "__main__":
    print("=== Fallback Strategy Test ===\n")

    # Test routing
    for score in [0.90, 0.75, 0.50]:
        decision = route_by_confidence(score)
        print(f"  score={score} → {decision}")

    print()
    print("Circuit breaker status:", get_breaker_status())
