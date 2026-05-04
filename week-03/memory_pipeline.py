"""
memory_pipeline.py — Week 3
GainScore Writing Coach: три режима работы с памятью пользователя

Режимы:
  1. full_context     — вся история в контекст
  2. compressed_context — LLM суммаризирует историю
  3. retrieved_context  — RAG: только релевантные сессии

Хранилище: SQLite (mock для PostgreSQL)
"""

import sqlite3
import json
import os
import math
import re
from datetime import datetime
from typing import Optional
import anthropic

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gainscore_memory.db")
client = anthropic.Anthropic()
MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You are an IELTS Writing Coach for GainScore.
Evaluate Task 2 essays on four criteria: Task Achievement (TA), Coherence & Cohesion (CC),
Lexical Resource (LR), Grammatical Range & Accuracy (GRA).

Rules:
- Score each criterion using IELTS scale only: 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0
- Overall band = average of 4 scores, rounded to nearest 0.5
- NEVER award Overall Band above 4.5 if essay is under 150 words
- Flag word count if under 250 words
- Cite specific phrases from the essay for each criterion
- Give one targeted improvement per criterion
- End with Priority Focus and Exercise
- Exercise must end with: "Submit your work here and I will review it immediately."

Output format:
**Overall Band:** X.X
⚠️ Word count: N words [flag if under 250]

**TA — X.X:** [quote] → [improvement]
**CC — X.X:** [quote] → [improvement]
**LR — X.X:** [quote] → [improvement]
**GRA — X.X:** [quote] → [improvement]

**Priority Focus:** [criterion + specific action]
**Exercise:** [concrete writing task] Submit your work here and I will review it immediately."""


# ─────────────────────────────────────────────
# DATABASE SETUP
# ─────────────────────────────────────────────
def init_db():
    """Создаёт таблицы если не существуют"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Episodic memory — история эссе
    c.execute("""
        CREATE TABLE IF NOT EXISTS essay_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            essay_text TEXT NOT NULL,
            word_count INTEGER,
            overall_band REAL,
            ta_score REAL,
            cc_score REAL,
            lr_score REAL,
            gra_score REAL,
            feedback_summary TEXT,
            recurring_error TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    
    # Semantic memory — профиль пользователя
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id INTEGER PRIMARY KEY,
            current_level REAL,
            target_band REAL,
            sessions_count INTEGER DEFAULT 0,
            recurring_errors TEXT DEFAULT '{}',
            last_session TEXT
        )
    """)
    
    conn.commit()
    conn.close()


def save_session(user_id: int, essay: str, feedback: str,
                 scores: dict, recurring_error: str = ""):
    """Сохраняет сессию в episodic memory"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    word_count = len(essay.split())
    
    c.execute("""
        INSERT INTO essay_sessions
        (user_id, essay_text, word_count, overall_band,
         ta_score, cc_score, lr_score, gra_score,
         feedback_summary, recurring_error)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id, essay, word_count,
        scores.get("overall", 0),
        scores.get("ta", 0), scores.get("cc", 0),
        scores.get("lr", 0), scores.get("gra", 0),
        feedback[:300],  # сжатый фидбек для RAG
        recurring_error
    ))
    
    # Обновляем semantic memory (профиль)
    c.execute("""
        INSERT INTO user_profiles (user_id, current_level, target_band, sessions_count, last_session)
        VALUES (?, ?, 7.0, 1, datetime('now'))
        ON CONFLICT(user_id) DO UPDATE SET
            current_level = ?,
            sessions_count = sessions_count + 1,
            last_session = datetime('now')
    """, (user_id, scores.get("overall", 0), scores.get("overall", 0)))
    
    conn.commit()
    conn.close()


def get_history(user_id: int) -> list[dict]:
    """Получает всю историю пользователя"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT id, essay_text, word_count, overall_band,
               ta_score, cc_score, lr_score, gra_score,
               feedback_summary, recurring_error, created_at
        FROM essay_sessions
        WHERE user_id = ?
        ORDER BY created_at ASC
    """, (user_id,))
    
    rows = c.fetchall()
    conn.close()
    
    return [{
        "id": r[0], "essay": r[1], "word_count": r[2],
        "overall": r[3], "ta": r[4], "cc": r[5],
        "lr": r[6], "gra": r[7], "feedback": r[8],
        "recurring_error": r[9], "date": r[10]
    } for r in rows]


def get_profile(user_id: int) -> Optional[dict]:
    """Получает semantic профиль пользователя"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "user_id": row[0], "current_level": row[1],
        "target_band": row[2], "sessions_count": row[3],
        "recurring_errors": json.loads(row[4] or "{}"),
        "last_session": row[5]
    }


# ─────────────────────────────────────────────
# SIMPLE BM25 (без зависимостей)
# ─────────────────────────────────────────────
def bm25_score(query: str, document: str, k1=1.5, b=0.75, avg_dl=100) -> float:
    """Простой BM25 score без внешних библиотек"""
    query_terms = query.lower().split()
    doc_terms = document.lower().split()
    doc_len = len(doc_terms)
    
    score = 0.0
    doc_freq = {}
    for term in doc_terms:
        doc_freq[term] = doc_freq.get(term, 0) + 1
    
    for term in query_terms:
        if term not in doc_freq:
            continue
        tf = doc_freq[term]
        idf = math.log(1 + 1 / (0.5 + 0.5))  # упрощённый IDF
        numerator = tf * (k1 + 1)
        denominator = tf + k1 * (1 - b + b * doc_len / avg_dl)
        score += idf * numerator / denominator
    
    return score


def simple_similarity(text1: str, text2: str) -> float:
    """Простое косинусное сходство через TF без numpy зависимостей"""
    def tf(text):
        words = re.findall(r'\w+', text.lower())
        freq = {}
        for w in words:
            freq[w] = freq.get(w, 0) + 1
        return freq
    
    t1, t2 = tf(text1), tf(text2)
    common = set(t1) & set(t2)
    if not common:
        return 0.0
    
    dot = sum(t1[w] * t2[w] for w in common)
    norm1 = math.sqrt(sum(v**2 for v in t1.values()))
    norm2 = math.sqrt(sum(v**2 for v in t2.values()))
    
    return dot / (norm1 * norm2) if (norm1 * norm2) > 0 else 0.0


# ─────────────────────────────────────────────
# THREE CONTEXT MODES
# ─────────────────────────────────────────────
def full_context(user_id: int, essay: str) -> str:
    """
    Режим 1: вся история в контекст.
    Максимальная точность, максимальный расход токенов.
    """
    history = get_history(user_id)
    
    if not history:
        return essay
    
    history_text = "=== USER HISTORY ===\n"
    for i, s in enumerate(history, 1):
        history_text += f"""
Session {i} ({s['date'][:10]}):
Essay ({s['word_count']} words): {s['essay'][:200]}...
Scores: Overall {s['overall']} | TA {s['ta']} | CC {s['cc']} | LR {s['lr']} | GRA {s['gra']}
Feedback: {s['feedback']}
Recurring error: {s['recurring_error']}
---"""
    
    return f"{history_text}\n\n=== NEW ESSAY TO EVALUATE ===\n{essay}"


def compressed_context(user_id: int, essay: str) -> str:
    """
    Режим 2: LLM сжимает историю → summary в контекст.
    ~90% экономия токенов при сопоставимой точности.
    """
    history = get_history(user_id)
    
    if not history:
        return essay
    
    # Формируем данные для суммаризации
    raw_history = "\n".join([
        f"Session {i} ({s['date'][:10]}): "
        f"Overall={s['overall']}, TA={s['ta']}, CC={s['cc']}, "
        f"LR={s['lr']}, GRA={s['gra']}. "
        f"Recurring error: {s['recurring_error']}. "
        f"Feedback: {s['feedback']}"
        for i, s in enumerate(history, 1)
    ])
    
    summary_response = client.messages.create(
        model=MODEL,
        max_tokens=300,
        messages=[{
            "role": "user",
            "content": f"""Summarize this IELTS student's learning history in 3-4 sentences.
Focus on: progress trend, recurring errors, current level, what to prioritize next.
Be specific with scores.

History:
{raw_history}

Output only the summary, nothing else."""
        }]
    )
    
    summary = summary_response.content[0].text
    
    return f"""=== USER SUMMARY ({len(history)} sessions) ===
{summary}

=== NEW ESSAY TO EVALUATE ===
{essay}"""


def retrieved_context(user_id: int, essay: str, query: str = None) -> str:
    """
    Режим 3: RAG — только релевантные сессии через hybrid search.
    Масштабируется на большую историю.
    """
    history = get_history(user_id)
    
    if not history:
        return essay
    
    # Запрос по умолчанию — сам эссе
    search_query = query or essay[:200]
    
    # Hybrid scoring: 0.6 * similarity + 0.4 * bm25
    scored = []
    for session in history:
        doc = f"{session['feedback']} {session['recurring_error']} {session['essay'][:150]}"
        
        sim_score = simple_similarity(search_query, doc)
        bm_score = bm25_score(search_query, doc)
        
        # Нормализуем bm25 (обычно в диапазоне 0-3)
        hybrid = 0.6 * sim_score + 0.4 * min(bm_score / 3.0, 1.0)
        scored.append((hybrid, session))
    
    # Берём top-2 самых релевантных
    scored.sort(key=lambda x: x[0], reverse=True)
    top_sessions = [s for _, s in scored[:2]]
    
    retrieved_text = "=== RETRIEVED RELEVANT SESSIONS (top 2) ===\n"
    for s in top_sessions:
        retrieved_text += f"""
Date: {s['date'][:10]} | Overall: {s['overall']}
TA={s['ta']} CC={s['cc']} LR={s['lr']} GRA={s['gra']}
Key issue: {s['recurring_error']}
Feedback: {s['feedback']}
---"""
    
    return f"{retrieved_text}\n\n=== NEW ESSAY TO EVALUATE ===\n{essay}"


# ─────────────────────────────────────────────
# EVALUATE (вызов агента)
# ─────────────────────────────────────────────
def evaluate_essay(context: str, mode_name: str) -> str:
    """Отправляет контекст + эссе агенту, возвращает фидбек"""
    response = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": context}]
    )
    return response.content[0].text


def count_tokens_approx(text: str) -> int:
    """Приблизительный подсчёт токенов (1 токен ≈ 4 символа)"""
    return len(text) // 4


# ─────────────────────────────────────────────
# SEED DATA — 3 прошлых сессии для user_id=42
# ─────────────────────────────────────────────
def seed_history(user_id: int = 42):
    """Заполняет историю тестовыми данными"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Проверяем — уже есть данные?
    c.execute("SELECT COUNT(*) FROM essay_sessions WHERE user_id = ?", (user_id,))
    if c.fetchone()[0] > 0:
        conn.close()
        return
    conn.close()
    
    sessions = [
        {
            "essay": "Technology is very important in our lives. Many people use smartphones every day. Technology is good because it helps us to communicate. However, some people think technology is bad. In conclusion, technology has advantages and disadvantages.",
            "scores": {"overall": 4.5, "ta": 4.0, "cc": 5.0, "lr": 4.5, "gra": 4.5},
            "feedback": "Essay too short (58 words). Did not address both views. Missing examples.",
            "recurring_error": "essay too short, missing counter-argument"
        },
        {
            "essay": "In modern society, technology plays crucial role in our daily lives. Some people argue that technology makes life easier because it allows us to communicate with people around world and access information quickly. On other hand, others believe technology makes life more complicated because we become too dependent on devices. In my opinion, technology has more benefits than drawbacks if we use it wisely.",
            "scores": {"overall": 5.5, "ta": 5.5, "cc": 5.5, "lr": 5.0, "gra": 5.0},
            "feedback": "Better structure. Missing articles: 'plays crucial role' → 'plays a crucial role'. Body paragraphs need examples.",
            "recurring_error": "missing articles (GRA), no specific examples (TA)"
        },
        {
            "essay": "Nowadays, technology has transformed the way people live and work. Proponents argue that innovations such as smartphones and the internet have simplified daily tasks, enabling instant communication and access to vast knowledge. Conversely, critics contend that excessive screen time and digital dependency have complicated modern life. In my view, the benefits outweigh the drawbacks, provided that individuals use technology mindfully.",
            "scores": {"overall": 6.0, "ta": 6.0, "cc": 6.0, "lr": 6.0, "gra": 5.5},
            "feedback": "Good progress. Vocabulary improved. Still missing article before 'internet' in some places. Need more developed examples.",
            "recurring_error": "article errors persist (GRA), examples still generic"
        },
    ]
    
    for s in sessions:
        save_session(user_id, s["essay"], s["feedback"], s["scores"], s["recurring_error"])
    
    print(f"✅ Seeded {len(sessions)} sessions for user_id={user_id}")


# ─────────────────────────────────────────────
# BENCHMARK — сравнение трёх режимов
# ─────────────────────────────────────────────
def run_benchmark():
    """Запускает все три режима и сравнивает результаты"""
    
    user_id = 42
    
    # Тестовое эссе (4-я сессия пользователя)
    test_essay = """
    In contemporary society, technology has become an indispensable part of everyday existence. 
    While advocates of technological progress assert that innovation has made life significantly 
    more convenient, detractors argue that it has introduced unprecedented levels of complexity.
    
    On one hand, technology undeniably simplifies numerous aspects of daily life. For instance, 
    smartphones enable instant communication across continents, while e-commerce platforms allow 
    consumers to purchase goods without leaving their homes. Furthermore, medical advancements 
    powered by technology have extended human life expectancy considerably.
    
    On the other hand, the proliferation of digital devices has created new challenges. Many 
    individuals report feeling overwhelmed by constant notifications and the pressure to remain 
    perpetually connected. Moreover, the rapid pace of technological change demands continuous 
    learning and adaptation, which many find stressful.
    
    In conclusion, while technology has introduced certain complexities, its benefits to 
    communication, commerce, and healthcare outweigh the drawbacks. The key lies in developing 
    a balanced relationship with technology rather than rejecting or uncritically embracing it.
    """.strip()
    
    print("\n" + "="*60)
    print("GAINSCORE MEMORY PIPELINE — BENCHMARK")
    print("="*60)
    print(f"User ID: {user_id}")
    print(f"Essay: {len(test_essay.split())} words")
    print(f"History sessions: {len(get_history(user_id))}")
    print("="*60)
    
    modes = [
        ("FULL CONTEXT",       lambda: full_context(user_id, test_essay)),
        ("COMPRESSED CONTEXT", lambda: compressed_context(user_id, test_essay)),
        ("RETRIEVED CONTEXT",  lambda: retrieved_context(user_id, test_essay)),
    ]
    
    results = {}
    
    for mode_name, build_context in modes:
        print(f"\n{'─'*40}")
        print(f"▶ Mode: {mode_name}")
        print(f"{'─'*40}")
        
        ctx = build_context()
        token_estimate = count_tokens_approx(ctx)
        print(f"📊 Context size: ~{token_estimate} tokens")
        
        feedback = evaluate_essay(ctx, mode_name)
        results[mode_name] = {
            "tokens": token_estimate,
            "feedback": feedback
        }
        
        print(f"\n{feedback}\n")
    
    # ── Итоговая таблица ──
    print("\n" + "="*60)
    print("BENCHMARK SUMMARY")
    print("="*60)
    print(f"{'Mode':<25} {'Tokens':>8} {'vs Full':>10}")
    print("─"*45)
    
    base_tokens = results["FULL CONTEXT"]["tokens"]
    for mode, data in results.items():
        ratio = data["tokens"] / base_tokens if base_tokens > 0 else 1
        print(f"{mode:<25} {data['tokens']:>8} {ratio:>9.0%}")
    
    print("\n✅ Benchmark complete. Check feedback above for quality comparison.")
    print("📝 Fill in benchmark-memory.md with your observations.")
    
    return results


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("🚀 Initialising GainScore Memory Pipeline...")
    
    init_db()
    seed_history(user_id=42)
    
    results = run_benchmark()
