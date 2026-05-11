"""
json_exporter.py — сохраняет полный RunResult (включая brief и steps) в JSON файл.
Один файл на run — для детального анализа и debugging.
"""
import json
import os

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")


class JSONExporter:
    def __init__(self, reports_dir: str = REPORTS_DIR):
        self.dir = reports_dir
        os.makedirs(self.dir, exist_ok=True)

    def export(self, result) -> str:
        path = os.path.join(self.dir, f"{result.run_id}.json")
        data = result.to_dict()
        data["brief"] = result.brief
        data["agent_steps"] = result.agent_steps
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"  [JSONExporter] ✅ Saved {path}")
        return path

    def export_brief(self, result) -> str:
        """Сохраняет только текст brief в markdown."""
        path = os.path.join(self.dir, f"{result.run_id}_brief.md")
        content = (f"# Market Intelligence Brief\n"
                   f"**Topic:** {result.topic}\n"
                   f"**Run:** {result.run_id}\n"
                   f"**Quality:** {result.quality} ({result.score:.2f})\n\n"
                   f"{result.brief}")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  [JSONExporter] ✅ Brief saved {path}")
        return path
