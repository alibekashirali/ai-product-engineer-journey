# Theory Notes — Week 10
**Тема:** Automation, Scheduling, Observability
**Источники:** Maxim AI (Nov 2025), iguazio LLM Observability Tools, Logz.io Top 9 Tools, Patronus AI, Orq.ai

---

## Главный сдвиг в мышлении

| Weeks 1-9 (Build) | Week 10 (Operate) |
|---|---|
| Запускаешь вручную | Запускается по расписанию |
| Смотришь в консоль | Метрики в dashboard |
| Знаешь когда сломалось | Алерт приходит раньше тебя |
| Один run = один отчёт | N runs = тренды + история |
| Debugging через print() | Traces + structured logs |

> **Ключевой тезис:** в 2023-2024 компании экспериментировали с LLM. К 2025-2026 они операционализируют их в масштабе. Observability больше не опциональна — она определяет качество, стоимость и доверие.

---

## 3 Принципа

### Принцип 1 — Три кита AI Ops: Traces, Evals, Alerts

Распределённая трассировка, учёт токенов, автоматические оценки и циклы обратной связи с людьми — это базовые требования в 2025 году.

```
TRACES  → что именно делал каждый агент, сколько токенов, сколько времени
EVALS   → автоматическая проверка качества output на каждом run
ALERTS  → уведомление когда метрики выходят за пороги
```

Для нашего pipeline это значит:
- **Trace:** каждый run сохраняет JSON с шагами агентов (уже есть из Week 6-7)
- **Eval:** LLM judge проверяет quality score (уже есть из Week 5)
- **Alert:** mock Slack/email если score < 0.6 или latency > 300s

### Принцип 2 — Pipeline как scheduled job, не как скрипт

Разница между `python3 pipeline.py` и production automation:

```
Manual run:
  python3 pipeline.py → отчёт в консоли → забыл сохранить → потеряно

Automated pipeline:
  cron/scheduler → run() → save CSV → notify → dashboard update
```

Каждый run должен:
1. Иметь уникальный `run_id` с timestamp
2. Сохранять output в персистентное хранилище (CSV / JSON / DB)
3. Отправлять нотификацию (Slack, email, webhook)
4. Обновлять metrics dashboard

### Принцип 3 — Modular exporters, не hardcoded destinations

Модульность критична в AI пайплайнах — команды используют разные модели и инструменты для разных задач. Observability должна объединять всё это без потери видимости.

```python
# НЕ ТАК: hardcoded
result = pipeline.run(topic)
with open("report.csv", "a") as f:
    f.write(result)
requests.post(SLACK_URL, json={"text": result})

# ТАК: pluggable exporters
exporters = [CSVExporter(), SheetsExporter(), SlackNotifier()]
for exporter in exporters:
    exporter.export(run_result)
```

Сегодня — CSV. Завтра — Google Sheets. Послезавтра — Notion API. Архитектура должна позволять добавить новый exporter без изменения pipeline.

---

## 2 Паттерна

### Паттерн 1 — Run Result Schema

Каждый automated run должен производить стандартный объект:

```python
@dataclass
class RunResult:
    run_id:      str       # "run_20260508_143022"
    topic:       str       # тема исследования
    started_at:  str       # ISO timestamp
    finished_at: str
    elapsed_s:   float     # время выполнения
    quality:     str       # PASS / FAIL
    score:       float     # 0.0 - 1.0
    brief:       str       # финальный текст
    agent_steps: list      # лог шагов
    cost_tokens: int       # примерный расход токенов
    error:       str|None  # None если успешно
```

Этот объект передаётся во все exporters. Exporters не знают о pipeline — только о RunResult.

### Паттерн 2 — Dead Letter Queue для failed runs

Настраивай алерты на критические метрики и получай еженедельные сводки чтобы опережать проблемы. Задавай пороги для latency, стоимости или evaluation scores.

При неудачном run (Exception или quality < threshold):

```
Run fails
  ↓
Save to dead_letter/run_id.json  ← не теряем данные
  ↓
Alert: "Run FAILED: {error}"     ← немедленно знаем
  ↓
Human review queue               ← ждёт ручной проверки
  ↓
Retry policy: max 2 retries      ← автоматически или вручную
```

---

## 1 Антипаттерн

### ❌ Silent failures — pipeline завершился но output плохой

Самая опасная ситуация: pipeline отработал без Exception, quality score низкий, но никто не узнал. Отчёт ушёл в CSV, нотификация отправилась, все довольны — но brief был пустым или hallucinated.

**Фикс:** alert не только на Exception, но и на quality < threshold:

```python
if run_result.score < QUALITY_THRESHOLD:
    notifier.alert(
        level="warning",
        message=f"Low quality run: score={run_result.score}",
        run_id=run_result.run_id
    )
    dead_letter_queue.save(run_result)
```

---

## Observability Stack для нашего pipeline

```
┌─────────────────────────────────────────────────────────┐
│  WEEKLY_PIPELINE.PY                                     │
│  cron → run() → RunResult                               │
├─────────────────┬───────────────────────────────────────┤
│  EXPORTERS      │  NOTIFIERS                            │
│  CSVExporter    │  SlackNotifier  (webhook mock)        │
│  JSONExporter   │  EmailNotifier  (SMTP mock)           │
│  SheetsExporter │                                       │
│  (mock)         │                                       │
├─────────────────┴───────────────────────────────────────┤
│  OPS DASHBOARD (Streamlit)                              │
│  - Run history table                                    │
│  - Quality score trend chart                            │
│  - Latency distribution                                 │
│  - Failed runs / dead letter queue                      │
└─────────────────────────────────────────────────────────┘
```

---

## Scheduling — три уровня

| Уровень | Инструмент | Когда |
|---|---|---|
| **Simple** | APScheduler (Python) | Один процесс, простой cron |
| **Medium** | Celery + Redis | Несколько воркеров, очереди |
| **Production** | Airflow / Prefect | DAGs, retry, monitoring UI |

**Для Week 10:** APScheduler — достаточно для weekly run без внешних зависимостей.

```python
from apscheduler.schedulers.blocking import BlockingScheduler

scheduler = BlockingScheduler()

@scheduler.scheduled_job('cron', day_of_week='mon', hour=9)
def weekly_run():
    run_pipeline(topics=WEEKLY_TOPICS)

scheduler.start()
```

---

## Cost Accounting — важная часть observability

Вызовы больших моделей через платные API стоят денег. Каждый токен промпта и ответа имеет цену.

Примерный расчёт для нашего pipeline:
```
Planner:    ~500 tokens in + ~300 out
Researcher: ~400 × 3 subtasks = ~2100 tokens
Analyst:    ~2000 in + ~800 out
Critic:     ~800 in + ~200 out
Writer:     ~1500 in + ~1000 out
────────────────────────────────
Total:      ~9200 tokens per run

Claude Sonnet 4.6: $3/$15 per 1M tokens
Cost per run: ~$0.02-0.05
Weekly (5 topics): ~$0.10-0.25
Monthly: ~$0.50-1.00
```

Дёшево — но трекинг важен для прогнозирования при масштабировании.

---

## Применение к GainScore

```
Automated weekly:
  - Collect: новые эссе студентов из БД
  - Run: eval pipeline на каждом эссе
  - Judge: LLM judge оценивает качество фидбека
  - Export: метрики в CSV + Google Sheets
  - Alert: если judge score < 0.7 на >10% эссе → review

Continuous eval (при каждом изменении промпта):
  pytest runner.py → LLM judges → score comparison
  Если regression → alert + block deploy
```

---

## Что строим в Days 2-3

```
weekly_pipeline.py    ← оркестратор: topics → runs → export → notify
run_result.py         ← dataclass RunResult
exporters/
  csv_exporter.py     ← append to reports/history.csv
  json_exporter.py    ← save reports/run_id.json
  sheets_exporter.py  ← mock: print Google Sheets API call
notifiers/
  slack_mock.py       ← mock: print Slack webhook payload
  email_mock.py       ← mock: print email content
ops_dashboard.py      ← Streamlit: история runs, графики, dead letters
scheduler.py          ← APScheduler cron wrapper
```

---

*Неделя 10 из 12 | AI Product Engineer Journey*
