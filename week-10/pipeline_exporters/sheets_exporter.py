"""
sheets_exporter.py — mock Google Sheets export.
В production: заменить на gspread или Google Sheets API.
Сейчас: выводит что именно было бы отправлено.
"""


class SheetsExporter:
    def __init__(self, spreadsheet_id: str = "MOCK_SPREADSHEET_ID",
                 sheet_name: str = "Pipeline Runs"):
        self.spreadsheet_id = spreadsheet_id
        self.sheet_name = sheet_name

    def export(self, result) -> dict:
        """Mock: печатает payload который ушёл бы в Google Sheets."""
        row = [
            result.run_id,
            result.topic[:50],
            result.started_at[:10],
            result.quality,
            f"{result.score:.2f}",
            f"{result.elapsed_s:.0f}s",
            str(result.word_count),
            str(result.cost_tokens),
            result.error or "—"
        ]
        print(f"  [SheetsExporter] 📊 Would append to Google Sheets:")
        print(f"    Spreadsheet: {self.spreadsheet_id}")
        print(f"    Sheet: {self.sheet_name}")
        print(f"    Row: {row}")
        return {
            "spreadsheet_id": self.spreadsheet_id,
            "sheet": self.sheet_name,
            "row": row,
            "status": "mock_success"
        }
