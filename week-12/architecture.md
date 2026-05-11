# Capstone Architecture
**AI Product Engineer Portfolio — Final Architecture**  

---

## Общая схема

```
┌─────────────────────────────────────────────────────────────────┐
│                    GAINSCORE WRITING COACH                      │
│                    (Weeks 1-6 → Weeks 7-11)                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   User Input                                                    │
│       ↓                                                         │
│   Streamlit UI (Week 9)                                         │
│       ↓                                                         │
│   ┌─── LangGraph StateGraph ──────────────────────────────┐    │
│   │                                                        │    │
│   │   ResearchState (TypedDict)                           │    │
│   │   {essay, word_count, scores, citations,              │    │
│   │    critique, feedback, retries, raw_findings}         │    │
│   │                                                        │    │
│   │   word_count_node ──→ evaluate_node ──→ judge_node   │    │
│   │                              ↑               ↓        │    │
│   │                         (retry ≤2)    route_after()   │    │
│   │                                       ┌──────────┐    │    │
│   │                                       │ PASS→fmt │    │    │
│   │                                       │ FAIL→eval│    │    │
│   │                                       └──────────┘    │    │
│   │   format_node ──→ notifier_node ──→ END              │    │
│   └────────────────────────────────────────────────────────┘    │
│       ↓                                                         │
│   Tools (Week 6)          Memory (Week 3)                       │
│   ┌───────────────┐       ┌──────────────────┐                 │
│   │ word_count    │       │ SQLite            │                 │
│   │ verify_citation│      │ essay_sessions    │                 │
│   │ calculator    │       │ user_profiles     │                 │
│   │ csv_query     │       │                  │                 │
│   │ summarizer    │       │ retrieved_context │                 │
│   │ notifier      │       │ (-33% tokens)    │                 │
│   └───────────────┘       └──────────────────┘                 │
│       ↓                                                         │
│   LLM Judges (Week 5)                                          │
│   ┌──────────────────────────────────────┐                     │
│   │ judge_correctness  (100% agreement)  │                     │
│   │ judge_groundedness (90% agreement)   │                     │
│   │ judge_usefulness   (90% agreement)   │                     │
│   └──────────────────────────────────────┘                     │
│       ↓                                                         │
│   route_by_confidence() (Week 11)                              │
│   ┌──────────────────────────────────────┐                     │
│   │ score ≥ 0.85 → auto_approve          │                     │
│   │ score ≥ 0.65 → human_review_queue    │                     │
│   │ score < 0.65 → dead_letter           │                     │
│   └──────────────────────────────────────┘                     │
│       ↓                                                         │
│   Automation (Week 10)                                         │
│   RunResult → CSV + JSON + Slack + Email + DeadLetter          │
│       ↓                                                         │
│   Ops Dashboard (Week 10)                                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Компоненты и недели

### Layer 1: Context Engineering (Weeks 1-2)
```
system-prompt-v1.md       ← IELTS rubric, constraints, output schema
context-pack-gainscore.md ← 8 секций: Goal/UserProfile/Task/Constraints/
                             Memory/Examples/OutputSchema/RefusalPolicy
```
**Принцип:** Context Pack > просто промпт. Структура заставляет думать о каждом аспекте поведения агента заранее.

### Layer 2: Memory (Week 3)
```python
# Три режима, выбор по числу сессий
if sessions <= 2:   mode = "full_context"     # 701 токен
elif sessions <= 10: mode = "retrieved_context" # 470 токен (-33%)
else:               mode = "retrieved_context" # + background compression

# Retrieved: hybrid BM25 + cosine similarity
score = 0.6 * cosine_sim + 0.4 * bm25_score
top_2 = sorted(sessions, key=score)[:2]
```

### Layer 3: Eval Harness (Week 4)
```
dataset.json (30 кейсов)
  → rubric.py (14 code-based checks)
  → runner.py (pytest + apply_band_cap)
  → results.json

apply_band_cap():  # критический фикс
  if word_count < 150 and band > 4.5:
    band = 4.5  # детерминированно, в коде
```

### Layer 4: LLM Judges (Week 5)
```python
# Reference-based (наиболее надёжный)
judge_correctness(essay, feedback, band_min, band_max) → PASS/FAIL

# Reference-free
judge_groundedness(essay, feedback) → PASS/FAIL
judge_usefulness(feedback)          → PASS/FAIL

# Calibration: 93% agreement с ручной разметкой
```

### Layer 5: Tool Calling (Week 6)
```python
# Контракт: всё через ToolResult, не raw exceptions
@dataclass
class ToolResult:
    success:          bool
    data:             Any
    error:            Optional[str]
    suggested_action: Optional[str]  # для LLM self-correction

# 6 tools с разделением Read/Write:
Read:  word_count, verify_citation, calculator, csv_query, summarizer
Write: notifier (с idempotency_key)

# Registry с трассировкой:
tool_registry.execute_tool(name, args, reason)
  → ToolResult + trace JSON + latency_ms
```

### Layer 6: Multi-Agent Orchestration (Weeks 7-8)
```python
# LangGraph StateGraph с conditional routing
class ResearchState(TypedDict):
    topic:        str
    findings:     list
    analysis:     dict
    critique:     dict
    retry_count:  int
    retry_reason: str   # ← key для правильного routing

# Фикс бага Week 7:
def route_after_critic(state) -> str:
    if state["critique"]["verdict"] == "PASS":
        return "writer"
    if state["critique"]["issue_type"] == "data":
        return "researcher"   # ← не всегда researcher!
    return "analyst"
```

### Layer 7: UI (Week 9)
```
Streamlit MVP — 5 экранов, dark theme
  Landing → Onboarding → Pipeline (animated) → Report (3 tabs) → Feedback
  666 строк, Space Mono + DM Sans, gradient accent
  Demo fallback: работает без API для presentation
```

### Layer 8: Automation (Week 10)
```python
# Modular exporters — pluggable destinations
RunResult → [CSVExporter, JSONExporter, SheetsExporter]
         → [SlackNotifier, EmailNotifier]
         → DeadLetter (при FAIL)

# APScheduler cron
@scheduler.scheduled_job('cron', day_of_week='mon', hour=9)
def weekly_run():
    run_weekly(WEEKLY_TOPICS)
```

### Layer 9: Production (Week 11)
```python
# Circuit breaker
CircuitBreaker(threshold=3, timeout=60)
  → Primary (Claude) → Critic (GPT) → Fallback (Gemini) → Demo cache

# "Fail Fast, or Ask"
route_by_confidence(score):
  ≥ 0.85 → auto_approve
  ≥ 0.65 → human_review_queue (SQLite + CLI)
  < 0.65 → dead_letter + alert

# Cost tracking
~$0.059/run → ~$4.72/month (dev) → ~$80/month (1k users + caching)
```

---

## Ключевые архитектурные решения

### 1. Детерминированные правила → в код
```
Промпт: "NEVER award Band above 4.5"  → нарушался 3/83 раз
Код:    apply_band_cap()              → 0 нарушений
```

### 2. Text format > JSON для LLM output
```
JSON → truncation → JSONDecodeError → cascade failure
Text → KEY: value → всегда парсируется → надёжность
```

### 3. Eval-driven development
```
Vibes check → "выглядит норм, шипим"  → ломается в prod
Eval harness → 83/83, judges 93%      → confidence
```

### 4. Retrieved context = Full quality, -33% tokens
```
full_context:       701 tokens → quality 6.5
retrieved_context:  470 tokens → quality 6.5 (LR 7.0!)
```

### 5. Conditional routing > manual if-else
```python
# Week 7 (manual) — всегда researcher:
if verdict == "FAIL":
    researcher.retry()  # неправильно!

# Week 8 (LangGraph) — правильная цель:
graph.add_conditional_edges("critic", route_after_critic, {
    "researcher": "researcher",
    "analyst":    "analyst",    # ← фикс!
    "writer":     "writer"
})
```

---

## Технический стек

```
Language:    Python 3.10+
LLM:         Claude Sonnet 4.6 (Anthropic API)
Orchestration: LangGraph 0.x
Framework:   CrewAI 1.14.4 (comparison)
UI:          Streamlit 1.57
Scheduling:  APScheduler 3.x
Storage:     SQLite (dev), PostgreSQL (prod plan)
Testing:     pytest + pytest-json-report
Tracing:     Custom JSON traces (tool_registry.py)
```

---

## Что дальше

### GainScore Production
1. PostgreSQL + Alembic миграции
2. Railway deploy (FastAPI backend + Streamlit frontend)
3. Stripe subscription ($9/mo student)
4. LangSmith для production tracing
5. Mobile app (SwiftUI)

### Research
1. Knowledge Tracing: предсказание следующей ошибки по essay history
2. Adaptive difficulty: exercise complexity на основе current band
3. Multilingual feedback: Казахский, Русский

---

*Capstone Architecture · AI Product Engineer Journey · 12 Weeks · 2026*
