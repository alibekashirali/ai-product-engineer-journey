# AI Product Engineer Portfolio
**Alibek Ashirali** · Data Engineer @ Kaspi.kz · EdTech Founder · iOS Instructor  
**Location:** Almaty, Kazakhstan  
**Focus:** AI-powered EdTech, LLM systems, Knowledge Tracing  
**GitHub:** [alibekashirali](https://github.com/alibekashirali)

---

## О программе

12-недельная self-study программа AI Product Engineer — от промптинга до production-grade multi-agent систем. Каждая неделя: теория → код → реальный запуск → eval → reflection.

**Stack:** Python · Claude API · LangGraph · CrewAI · Streamlit · SQLite · APScheduler · pytest

---

## Проекты

### 1. GainScore IELTS Writing Coach
**Статус:** Production-ready agent  
**Описание:** LLM агент для оценки IELTS Task 2 эссе по официальной шкале (4.0-9.0). Персональная память студента, педагогические упражнения, anti-fabrication защита.

| Метрика | Результат |
|---|---|
| Eval accuracy | 83/83 (100%) |
| LLM judge agreement | 93% с ручной разметкой |
| Tool calling success | 11/11 (100%) |
| Fabricated citations | 0 (verify_citation tool) |

**Артефакты:**
- [Case Study →](case_study_gainscore.md)
- `week-01/` System prompt v1 (Claude 30/30 benchmark)
- `week-02/` Context Pack v4 (memory, schema, refusal policy)
- `week-03/` Memory pipeline (retrieved context: −33% tokens)
- `week-04/` Eval harness (83/83 pytest)
- `week-05/` LLM judges (93% agreement)
- `week-06/` Tool calling (verify_citation, calculator, word_count)

---

### 2. AI Market Intelligence Copilot
**Статус:** Live MVP + Automation  
**Описание:** Multi-agent research pipeline генерирует structured intelligence briefs по рыночным темам. 5 специализированных агентов, conditional routing, weekly automation, ops dashboard.

| Метрика | Результат |
|---|---|
| Brief quality (LangGraph) | PASS 0.72 · 471 слов |
| Brief quality (CrewAI) | PASS 0.87 · 650 слов |
| Latency | 87s (LangGraph) · 235s (CrewAI) |
| Automation runs | 8 runs в history.csv |
| Cost per run | ~$0.059 |

**Артефакты:**
- [Case Study →](case_study_copilot.md)
- `week-07/` Multi-agent pipeline (5 агентов, text format)
- `week-08/` LangGraph vs CrewAI comparison
- `week-09/` Streamlit MVP (5 экранов, dark theme)
- `week-10/` Automation stack (exporters, notifiers, scheduler)
- `week-11/` Production checklist (5/10 failure modes решены)

---

## Финальная архитектура

```
User Input (topic/essay)
    ↓
Streamlit UI (Week 9)
    ↓
LangGraph StateGraph (Week 8)
    ├── word_count tool       ← детерминированный (Week 6)
    ├── verify_citation tool  ← anti-fabrication (Week 6)
    ├── calculator tool       ← точный band score (Week 6)
    ├── csv_query tool        ← IELTS дескрипторы (Week 6)
    └── notifier tool         ← write, idempotency (Week 6)
    ↓
LLM Judge (Week 5)
    ├── judge_groundedness    ← citations quality
    ├── judge_usefulness      ← exercise quality
    └── judge_correctness     ← score accuracy
    ↓
route_by_confidence()         ← Fail Fast or Ask (Week 11)
    ├── score ≥ 0.85 → auto_approve
    ├── score ≥ 0.65 → human_review_queue
    └── score < 0.65 → dead_letter
    ↓
RunResult → CSVExporter + JSONExporter + SlackNotifier (Week 10)
    ↓
Ops Dashboard (Week 10)
```

**[Подробная архитектура →](architecture.md)**

---

## Eval Summary

| Неделя | Что измеряли | Результат |
|---|---|---|
| 4 | Eval harness accuracy | 83/83 (100%) |
| 5 | LLM judge agreement | 93% (threshold: 80%) |
| 6 | Tool selection accuracy | 100% (11/11) |
| 8 | Brief quality LangGraph | 0.72 PASS |
| 8 | Brief quality CrewAI | 0.87 PASS |
| 9 | Demo flow completion | ✅ < 3 min |
| 10 | Pipeline automation | 6/8 PASS (75%) |
| 11 | Failure modes resolved | 5/10 |

**[Полный Eval Report →](eval_report.md)**

---

## Технические решения

### Проблемы и как решили

| Проблема | Решение | Неделя |
|---|---|---|
| Band cap нарушался в промпте | `apply_band_cap()` в коде | 4 |
| Fabricated citations | `verify_citation` tool | 6 |
| JSON truncation в агентах | Текстовый `KEY: value` формат | 7 |
| Wrong retry target | Conditional edges в LangGraph | 8 |
| `exporters` name conflict (Anaconda) | Переименовали в `pipeline_exporters` | 10 |
| Silent quality degradation | LLM judges + human review queue | 5, 11 |

### Ключевые выводы

1. **Детерминированные правила → в код, не в промпт.** Промпт нарушался 3/4 раз. Код — никогда.
2. **Текстовые форматы надёжнее JSON** для LLM output в агентных системах.
3. **Retrieved context = Full context по качеству, -33% токенов.**
4. **CrewAI даёт лучшее качество brief** (accumulated context). **LangGraph — лучшую архитектуру** (conditional routing).
5. **"Fail Fast, or Ask"** — главный паттерн для production human-in-the-loop.

---

## Roadmap

### GainScore (следующие 3 месяца)
- [ ] Deploy LangGraph pipeline на Railway
- [ ] PostgreSQL вместо SQLite (memory pipeline)
- [ ] Stripe интеграция (subscription)
- [ ] Mobile app (SwiftUI — уже есть iOS опыт)
- [ ] A/B тест: LangGraph agent vs simple prompt

### Research направления (PhD)
- Knowledge Tracing через LLM agents
- Adaptive exercise generation на основе essay history
- Multi-lingual IELTS feedback (Казахский, Русский)
- Eval методология для педагогических AI систем

---

## Контакты

- **Email:** [your email]
- **GitHub:** [alibekashirali](https://github.com/alibekashirali)
- **GainScore:** [gainscores.com](https://gainscores.com)
- **LinkedIn:** [your linkedin]

---

*AI Product Engineer · 12-Week Journey · 2026*
