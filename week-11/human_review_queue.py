"""
human_review_queue.py — SQLite очередь для human-in-the-loop.

Роутинг:
  score >= 0.85 → auto_approve
  score >= 0.65 → human_review (эта очередь)
  score < 0.65  → auto_reject → dead_letter

CLI:
  python3 human_review_queue.py list           ← показать pending
  python3 human_review_queue.py review <id>    ← принять/отклонить
  python3 human_review_queue.py stats          ← статистика
"""
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone


DB_PATH = os.path.join(os.path.dirname(__file__), "review_queue.db")

# ─────────────────────────────────────────────
# DB SETUP
# ─────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS review_queue (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id      TEXT UNIQUE,
            topic       TEXT,
            score       REAL,
            quality     TEXT,
            brief       TEXT,
            created_at  TEXT,
            status      TEXT DEFAULT 'pending',  -- pending|approved|rejected
            reviewer    TEXT,
            reviewed_at TEXT,
            notes       TEXT
        )
    """)
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
# QUEUE OPERATIONS
# ─────────────────────────────────────────────
def add_to_queue(run_id: str, topic: str, score: float,
                 quality: str, brief: str) -> int:
    """Добавляет run в очередь на review."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.execute("""
            INSERT OR IGNORE INTO review_queue
            (run_id, topic, score, quality, brief, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (run_id, topic, score, quality, brief[:2000],
              datetime.now(timezone.utc).isoformat()))
        conn.commit()
        row_id = cursor.lastrowid
        print(f"  [HumanQueue] 📥 Added to review queue: {run_id} (score={score:.2f})")
        return row_id
    finally:
        conn.close()


def get_pending(limit: int = 20) -> list[dict]:
    """Возвращает pending items."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT * FROM review_queue
        WHERE status = 'pending'
        ORDER BY created_at ASC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def review_item(run_id: str, decision: str,
                reviewer: str = "human", notes: str = "") -> bool:
    """Принимает решение по item: approved | rejected."""
    if decision not in ("approved", "rejected"):
        print(f"Invalid decision: {decision}. Use 'approved' or 'rejected'")
        return False

    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        UPDATE review_queue
        SET status=?, reviewer=?, reviewed_at=?, notes=?
        WHERE run_id=?
    """, (decision, reviewer,
          datetime.now(timezone.utc).isoformat(),
          notes, run_id))
    conn.commit()
    conn.close()
    print(f"  [HumanQueue] {'✅' if decision=='approved' else '❌'} {run_id} → {decision}")
    return True


def get_stats() -> dict:
    """Статистика очереди."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("""
        SELECT status, COUNT(*) as cnt, AVG(score) as avg_score
        FROM review_queue GROUP BY status
    """).fetchall()
    conn.close()
    return {r[0]: {"count": r[1], "avg_score": round(r[2] or 0, 2)} for r in rows}


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────
def cmd_list():
    pending = get_pending()
    if not pending:
        print("✅ No items pending review")
        return
    print(f"\n{'─'*60}")
    print(f"PENDING REVIEW ({len(pending)} items)")
    print(f"{'─'*60}")
    for item in pending:
        print(f"\n  ID:    {item['run_id']}")
        print(f"  Topic: {item['topic'][:55]}")
        print(f"  Score: {item['score']:.2f} | Quality: {item['quality']}")
        print(f"  Added: {item['created_at'][:19]}")
        print(f"  Brief: {item['brief'][:100]}...")
        print(f"\n  Review: python3 human_review_queue.py review {item['run_id']}")


def cmd_review(run_id: str):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM review_queue WHERE run_id=?",
                       (run_id,)).fetchone()
    conn.close()

    if not row:
        print(f"Not found: {run_id}")
        return

    item = dict(row)
    print(f"\n{'─'*60}")
    print(f"REVIEWING: {run_id}")
    print(f"{'─'*60}")
    print(f"Topic:   {item['topic']}")
    print(f"Score:   {item['score']:.2f} | Quality: {item['quality']}")
    print(f"\nBRIEF:\n{item['brief'][:600]}")
    print(f"\n{'─'*60}")

    decision = input("Decision [a=approve / r=reject / s=skip]: ").strip().lower()
    if decision == "a":
        notes = input("Notes (optional): ").strip()
        review_item(run_id, "approved", notes=notes)
    elif decision == "r":
        notes = input("Reason for rejection: ").strip()
        review_item(run_id, "rejected", notes=notes)
    else:
        print("Skipped")


def cmd_stats():
    stats = get_stats()
    print(f"\n{'─'*40}")
    print("REVIEW QUEUE STATS")
    print(f"{'─'*40}")
    for status, data in stats.items():
        icon = {"pending": "⏳", "approved": "✅", "rejected": "❌"}.get(status, "•")
        print(f"  {icon} {status:10} {data['count']:3} items | avg_score={data['avg_score']:.2f}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] == "list":
        cmd_list()
    elif args[0] == "review" and len(args) > 1:
        cmd_review(args[1])
    elif args[0] == "stats":
        cmd_stats()
    else:
        print("Usage:")
        print("  python3 human_review_queue.py list")
        print("  python3 human_review_queue.py review <run_id>")
        print("  python3 human_review_queue.py stats")
