"""
cost_tracker.py — учёт токенов и бюджета на каждый run.

Цены Claude Sonnet 4.6 (приблизительно):
  Input:  $3 per 1M tokens
  Output: $15 per 1M tokens
"""
import os
import csv
import json
from datetime import datetime, timezone
from dataclasses import dataclass

COST_LOG = os.path.join(os.path.dirname(__file__), "cost_log.csv")
BUDGET_ALERT_USD = 1.00   # алерт при превышении в день

# Цены per 1M токенов (USD)
PRICING = {
    "claude-sonnet-4-6": {"input": 3.0,  "output": 15.0},
    "gpt-4o":            {"input": 5.0,  "output": 15.0},
    "gemini-1.5-flash":  {"input": 0.075,"output": 0.30},
    "demo_cache":        {"input": 0.0,  "output": 0.0},
}

# Приблизительный расход токенов по агентам
AGENT_TOKEN_ESTIMATES = {
    "Planner":    {"input": 500,  "output": 300},
    "Researcher": {"input": 400,  "output": 600},  # × subtasks
    "Analyst":    {"input": 2000, "output": 800},
    "Critic":     {"input": 800,  "output": 200},
    "Writer":     {"input": 1500, "output": 1000},
    "Demo":       {"input": 0,    "output": 0},
}


@dataclass
class TokenUsage:
    run_id:       str
    model:        str
    input_tokens: int
    output_tokens: int
    cost_usd:     float
    timestamp:    str

    def to_dict(self) -> dict:
        return {
            "run_id":        self.run_id,
            "model":         self.model,
            "input_tokens":  self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens":  self.input_tokens + self.output_tokens,
            "cost_usd":      round(self.cost_usd, 5),
            "timestamp":     self.timestamp,
        }


def estimate_run_cost(agent_steps: list, model: str = "claude-sonnet-4-6") -> TokenUsage:
    """Оценивает стоимость run по шагам агентов."""
    total_in = 0
    total_out = 0

    for step in agent_steps:
        agent = step.get("agent", "")
        est = AGENT_TOKEN_ESTIMATES.get(agent, {"input": 500, "output": 300})
        total_in  += est["input"]
        total_out += est["output"]

    # Если нет шагов — используем дефолт
    if not agent_steps:
        total_in, total_out = 9200, 0

    pricing = PRICING.get(model, PRICING["claude-sonnet-4-6"])
    cost = (total_in * pricing["input"] + total_out * pricing["output"]) / 1_000_000

    return TokenUsage(
        run_id=f"est_{datetime.now(timezone.utc).strftime('%H%M%S')}",
        model=model,
        input_tokens=total_in,
        output_tokens=total_out,
        cost_usd=cost,
        timestamp=datetime.now(timezone.utc).isoformat()
    )


def log_cost(run_id: str, usage: TokenUsage):
    """Сохраняет стоимость в cost_log.csv."""
    data = usage.to_dict()
    data["run_id"] = run_id
    file_exists = os.path.exists(COST_LOG)
    with open(COST_LOG, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(data.keys()))
        if not file_exists:
            writer.writeheader()
        writer.writerow(data)


def get_daily_cost() -> float:
    """Возвращает суммарную стоимость за сегодня."""
    if not os.path.exists(COST_LOG):
        return 0.0
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    total = 0.0
    with open(COST_LOG) as f:
        for row in csv.DictReader(f):
            if row.get("timestamp", "").startswith(today):
                total += float(row.get("cost_usd", 0))
    return total


def check_budget_alert(run_id: str = "") -> bool:
    """Проверяет бюджет и алертит при превышении."""
    daily = get_daily_cost()
    if daily >= BUDGET_ALERT_USD:
        print(f"  [CostTracker] 🚨 BUDGET ALERT: ${daily:.3f} spent today (limit ${BUDGET_ALERT_USD})")
        return True
    return False


def get_cost_summary() -> dict:
    """Сводка по стоимости."""
    if not os.path.exists(COST_LOG):
        return {"total_runs": 0, "total_cost_usd": 0, "avg_cost_usd": 0}

    rows = []
    with open(COST_LOG) as f:
        rows = list(csv.DictReader(f))

    if not rows:
        return {"total_runs": 0, "total_cost_usd": 0, "avg_cost_usd": 0}

    total = sum(float(r.get("cost_usd", 0)) for r in rows)
    return {
        "total_runs":    len(rows),
        "total_cost_usd": round(total, 4),
        "avg_cost_usd":  round(total / len(rows), 5),
        "total_tokens":  sum(int(r.get("total_tokens", 0)) for r in rows),
        "daily_cost_usd": round(get_daily_cost(), 4),
    }


if __name__ == "__main__":
    print("=== Cost Tracker Test ===\n")

    # Тестовые шаги
    mock_steps = [
        {"agent": "Planner",    "action": "plan_ready",     "detail": "3 subtasks"},
        {"agent": "Researcher", "action": "findings_ready", "detail": "9 findings"},
        {"agent": "Analyst",    "action": "analysis_ready", "detail": "2 sections"},
        {"agent": "Critic",     "action": "verdict",        "detail": "PASS"},
        {"agent": "Writer",     "action": "brief_ready",    "detail": "440 words"},
    ]

    usage = estimate_run_cost(mock_steps)
    print(f"Estimated cost for typical run:")
    print(f"  Input tokens:  {usage.input_tokens:,}")
    print(f"  Output tokens: {usage.output_tokens:,}")
    print(f"  Cost (Claude): ${usage.cost_usd:.5f}")

    log_cost("test_run_001", usage)
    print(f"\nLogged to: {COST_LOG}")

    summary = get_cost_summary()
    print(f"\nSummary: {summary}")

    # Projection
    weekly = usage.cost_usd * 20
    monthly = usage.cost_usd * 80
    print(f"\nProjections (20 runs/week):")
    print(f"  Weekly:  ${weekly:.3f}")
    print(f"  Monthly: ${monthly:.3f}")
