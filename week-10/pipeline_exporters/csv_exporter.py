"""
csv_exporter.py — сохраняет RunResult в history.csv с append.
Каждый run добавляет одну строку — история накапливается.
"""
import csv
import os
from datetime import datetime

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")
CSV_PATH = os.path.join(REPORTS_DIR, "history.csv")

FIELDS = ["run_id", "topic", "started_at", "finished_at",
          "elapsed_s", "quality", "score", "word_count",
          "cost_tokens", "retries", "framework", "error"]


class CSVExporter:
    def __init__(self, path: str = CSV_PATH):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)

    def export(self, result) -> str:
        """Добавляет строку в CSV. Создаёт файл с заголовком если не существует."""
        file_exists = os.path.exists(self.path)
        with open(self.path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
            if not file_exists:
                writer.writeheader()
            writer.writerow(result.to_csv_row())
        print(f"  [CSVExporter] ✅ Appended to {self.path}")
        return self.path

    def read_history(self) -> list[dict]:
        """Читает всю историю запусков."""
        if not os.path.exists(self.path):
            return []
        with open(self.path, "r", encoding="utf-8") as f:
            return list(csv.DictReader(f))
