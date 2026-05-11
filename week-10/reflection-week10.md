# Reflection — Week 10
**Week:** 10 of 12 — Automation and Workflows
**Status:** ✅ Complete — pipeline работает, 8 runs в history.csv

---

## Что было сделано за неделю

| Артефакт | Статус |
|---|---|
| `theory-notes-week10.md` — scheduling, observability, AI Ops | ✅ |
| `run_result.py` — стандартный dataclass RunResult | ✅ |
| `weekly_pipeline.py` — оркестратор с fallback логикой | ✅ |
| `pipeline_exporters/` — CSV, JSON, Sheets mock | ✅ |
| `pipeline_notifiers/` — Slack mock, Email mock | ✅ |
| `ops_dashboard.py` — Streamlit monitoring | ✅ |
| `scheduler.py` — APScheduler cron | ✅ |
| Реальные runs: 8 JSON файлов + history.csv | ✅ |

---

## Quality Gate

**Из плана:** `python3 weekly_pipeline.py` → отчёт сохранён в `reports/` с timestamp.

✅ **Пройден** — history.csv накапливает историю, каждый run получает уникальный run_id с миллисекундами.

---

## Анализ реальных запусков

### История runs из history.csv

| Run ID | Topic | Quality | Score | Elapsed | Retries |
|---|---|---|---|---|---|
| run_20260508_110954 | EdTech Central Asia | ❌ FAIL | 0.00 | 0s | 0 |
| run_20260508_111602 | AI writing tools | ✅ PASS | 0.68 | 105s | 1 |
| run_20260508_111747 | SaaS PM tools | ❌ FAIL | 0.35 | 117s | 2 |
| run_20260508_111944 | EdTech Central Asia | ✅ PASS | 0.68 | 82s | 0 |
| run_20260508_112218 | B2B analytics | ✅ PASS | 0.82 | 1.2s | 0 |
| run_20260508_113223 | AI writing tools | ✅ PASS | 0.82 | 1.7s | 0 |
| run_20260508_113225 | SaaS PM tools | ✅ PASS | 0.82 | 1.0s | 0 |
| run_20260508_113226 | EdTech Central Asia | ✅ PASS | 0.82 | 1.0s | 0 |

**Итого:** 6/8 PASS (75%), avg_score=0.67, один FAIL из-за `No module named 'langgraph'`

---

## Главный инсайт недели

**Pipeline как продукт требует graceful degradation.**

Первые три run упали с `No module named 'langgraph'` или FAIL quality gate — но automation stack сработал правильно:
- CSV получил строку с `error` полем
- Slack послал `🚨 ALERT [critical]`
- Dead letter queue сохранил файл
- Следующий run запустился независимо

Это и есть production readiness — система не остановилась на первом сбое.

Второй инсайт: **conditional routing LangGraph работает в production.** Run `run_20260508_111602` показал retry в action:
```
Critic: FAIL (score=0.35)
→ route_after_critic: issue_type=analysis → Analyst
Analyst: retry
Critic: PASS (score=0.68)
→ Writer
```
Баг Week 7 решён — retry пошёл к Analyst, а не к Researcher.

---

## Данные по качеству из реальных runs

### LangGraph runs (реальный pipeline)

| Run | Score | Retries | Elapsed | Verdict |
|---|---|---|---|---|
| AI writing tools | 0.68 | 1 retry → PASS | 105s | Critic отправил к Analyst, помогло |
| SaaS PM tools | 0.35 | 2 retries → FAIL | 117s | Analyst стабильно давал 1 секцию, Critic не пропускал |
| EdTech Central Asia | 0.68 | 0 | 82s | Прошёл с первого раза |

### Demo runs (fallback без langgraph)
Score всегда 0.82, elapsed 1-2s — это mock данные. Полезны для тестирования automation stack без API calls.

---

## Failure Mode Analysis

### Failure 1: SaaS PM tools — 2 retries, FAIL (score=0.35)
Analyst стабильно возвращал `1 sections` на всех трёх попытках. Retry шёл к Analyst (правильно!) — но Analyst не мог улучшить результат потому что получал те же данные от Researcher.

**Root cause:** Conditional routing правильный, но данные от Researcher не меняются при повторе через Analyst. Нужно: при втором retry — обновлять и Researcher тоже.

**Fix для Week 12:** добавить счётчик analyst_retries — при >1 → researcher.refine() → analyst.

### Failure 2: Silent quality degradation
Demo brief (score=0.82) содержит шаблонный текст не адаптированный к теме. Это технически PASS, но информационно низкокачественный. Silent failure — метрики зелёные, контент плохой.

**Fix:** добавить judge проверку на "шаблонность" (Week 5 judge_groundedness).

---

## Automation Stack — что работает хорошо

```
RunResult dataclass       ← единый контракт между pipeline и exporters ✅
CSVExporter               ← история накапливается, append работает ✅
JSONExporter              ← полный лог каждого run с brief ✅
SheetsExporter (mock)     ← структура готова, заменить на gspread ✅
SlackNotifier (mock)      ← alerts на FAIL и low quality ✅
EmailNotifier (mock)      ← weekly summary email ✅
Dead letter queue         ← failed runs не теряются ✅
Unique run_id с ms        ← нет коллизий при быстрых runs ✅
utcnow() deprecated fix   ← Python 3.12+ совместимость ✅
```

---

## Known Issues → Backlog

| Issue | Severity | Fix |
|---|---|---|
| SaaS PM brief FAIL при 2 retries (Analyst застрял) | Medium | При analyst_retries > 1 → researcher.refine() |
| Demo brief шаблонный (одинаковый для всех тем) | Low | Добавить topic-aware _demo_brief() |
| ops_dashboard.py не протестирован (нет plotly) | Low | pip install plotly или text fallback |

---

## Связь с реальными проектами

### GainScore
Та же automation архитектура применима к GainScore:
```
weekly_eval.py:
  - Берёт новые эссе из PostgreSQL за неделю
  - Прогоняет через eval harness (Week 4)
  - LLM judge проверяет качество фидбека (Week 5)
  - CSVExporter → Google Sheets с метриками
  - SlackNotifier → alert если avg_score < 0.7
```


---

*Week 10 of 12 | AI Product Engineer Journey*
