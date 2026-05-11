"""
run_result.py — стандартный объект результата каждого run.
Все exporters и notifiers работают только с RunResult — не знают о pipeline.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class RunResult:
    run_id:      str
    topic:       str
    started_at:  str
    finished_at: str
    elapsed_s:   float
    quality:     str          # PASS / FAIL
    score:       float        # 0.0 - 1.0
    brief:       str
    agent_steps: list = field(default_factory=list)
    cost_tokens: int = 0      # примерный расход токенов
    retries:     int = 0
    framework:   str = "LangGraph"
    error:       Optional[str] = None

    @classmethod
    def make_id(cls) -> str:
        return f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')[:23].replace('.', '_')}"

    @property
    def success(self) -> bool:
        return self.error is None and self.quality == "PASS"

    @property
    def word_count(self) -> int:
        return len(self.brief.split())

    def to_dict(self) -> dict:
        return {
            "run_id":      self.run_id,
            "topic":       self.topic,
            "started_at":  self.started_at,
            "finished_at": self.finished_at,
            "elapsed_s":   round(self.elapsed_s, 1),
            "quality":     self.quality,
            "score":       self.score,
            "word_count":  self.word_count,
            "cost_tokens": self.cost_tokens,
            "retries":     self.retries,
            "framework":   self.framework,
            "error":       self.error,
        }

    def to_csv_row(self) -> dict:
        """Плоская строка для CSV."""
        return self.to_dict()
