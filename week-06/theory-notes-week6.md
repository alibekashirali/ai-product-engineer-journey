# Theory Notes — Week 6
**Тема:** Tool Calling & Agent Harness
**Источники:** Inductivee (40+ production deployments analysis), Statsig Tool Calling Optimization, ML Mastery, n8n Blog, Composio 2026 Guide

---

## Главный сдвиг в мышлении

| До Tool Calling | После Tool Calling |
|---|---|
| LLM генерирует ответ из памяти | LLM вызывает внешние функции |
| Статичные знания (cutoff date) | Динамические данные в реальном времени |
| Промпт-инструкции для правил | Детерминированный код для правил |
| "Чёрный ящик" | Полная трассировка каждого шага |

> **Ключевой тезис:** Tool calling — это первичная точка отказа production агентов. LLM reasoning layer надёжен. Tool execution layer ломается.

---

## 3 Принципа

### Принцип 1 — Tool как контракт, не как функция

Производственный стандарт: определяй Pydantic input schema для каждого tool со строгой валидацией. Возвращай ToolResult объекты, а не сырые значения или исключения.

Каждый tool — это явный контракт:
```python
# НЕ ТАК: сырая функция
def word_count(text):
    return len(text.split())

# ТАК: структурированный контракт
@dataclass
class ToolResult:
    success: bool
    data: Any
    error: Optional[str]
    suggested_action: Optional[str]  # для LLM self-correction

def word_count(text: str) -> ToolResult:
    ...
```

### Принцип 2 — Два типа ошибок, два разных обработчика

Для технических ошибок (rate limits) система должна делать retry автоматически. Для логических ошибок (validation failure) ошибка должна быть возвращена LLM чтобы он мог "рассуждать" к другому решению.

```
Transient errors  → retry (exponential backoff) → молча
Logic errors      → feed back to LLM           → с объяснением
Permission errors → escalate                   → к человеку
```

### Принцип 3 — Observability = трассировка каждого шага

Перед вызовом tool требуй одну строку обоснования и ID инструмента. После вызова — короткое наблюдение. Это небольшое количество структуры повышает трассируемость и снижает количество зацикливаний.

```json
{
  "timestamp": "2026-05-01T10:23:45",
  "tool": "word_count",
  "reason": "need to check if essay meets 250 word minimum",
  "args": {"text": "..."},
  "result": {"count": 83, "flag": true},
  "latency_ms": 2,
  "status": "success"
}
```

---

## 2 Паттерна

### Паттерн 1 — Read vs Write классификация

Классифицируй каждый tool как read или write. Read tools получают кеш результатов. Write tools получают принудительное соблюдение идемпотентности. Никогда не пропускай эту классификацию.

| Тип | Примеры | Поведение |
|---|---|---|
| **Read** | word_count, verify_citation, csv_query | Кеш, повторный вызов безопасен |
| **Write** | notifier, database_write | Идемпотентность, один раз |

### Паттерн 2 — Structured Error Response для LLM self-correction

Поле suggested_action — самое важное добавление. "Подождите 30 секунд и повторите с теми же аргументами" для rate limit, "поле customer_id должно быть 7-значной строкой начинающейся с C-" для validation error — это направляет следующее действие агента с конкретикой, снижающей количество итераций восстановления.

```python
# Плохо: Python traceback (бесполезен для LLM)
raise ValueError("invalid input")

# Хорошо: structured error
ToolResult(
    success=False,
    error="validation_error",
    message="essay text cannot be empty",
    suggested_action="Provide the essay text as a non-empty string",
    example_valid_call='word_count(text="Technology is important...")'
)
```

---

## 1 Антипаттерн

### ❌ Tool Explosion — слишком много tools в одном контексте

Внутреннее тестирование Anthropic показало, что 58 инструментов могут потреблять ~55k токенов. По мере роста числа вариантов инструментов способность модели выбирать правильный снижается.

**Фикс:** минимальный жизнеспособный набор tools. Для GainScore — 5-6 tools с чёткими границами, не 20+. Если tools > 10 → embedding-based tool routing.

---

## Анатомия Tool Calling цикла

```
User Input
    ↓
LLM (reason + select tool)
    ↓
Tool Call Request {name, args}
    ↓
Schema Validation (Pydantic)
    ↓ (если ошибка → feed back to LLM)
Tool Execution
    ↓ (если transient error → retry с backoff)
ToolResult {success, data, error, suggested_action}
    ↓
LLM (observe + decide next action)
    ↓
Final Response / Next Tool Call
```

---

## 4 Failure Categories из 40+ production deployments

После анализа production failures в 40+ agentic system deployments были выявлены четыре основных категории ошибок tool calls.

| # | Тип | Пример | Фикс |
|---|---|---|---|
| 1 | **Wrong arg types** | date field получает "next Monday" вместо "2026-05-01" | Pydantic strict validation |
| 2 | **Transient API failure** | timeout, 500 error, rate limit | Exponential backoff retry |
| 3 | **Partial success** | агент думает что tool сработал, а он упал на шаге 3 из 5 | Atomic ToolResult с полным статусом |
| 4 | **Non-idempotent retry** | write tool вызван дважды → дублирование | Idempotency keys для write tools |

---

## Метрики для eval отчёта (Quality Gate Недели 6)

| Метрика | Что измеряет | Как считать |
|---|---|---|
| **Tool Selection Accuracy** | Агент выбрал правильный tool? | правильные_выборы / всего_вызовов |
| **Invalid Args Rate** | Как часто args не прошли валидацию? | invalid_calls / всего_вызовов |
| **Recovery Rate** | После ошибки агент восстановился? | успешных_recovery / всего_ошибок |
| **Tool Latency** | Среднее время выполнения | avg(latency_ms) по каждому tool |

---

## 5 Tools для GainScore (план Недели 6)

| Tool | Тип | Зачем |
|---|---|---|
| `word_count` | Read | Детерминированный подсчёт, заменяет промпт-инструкцию |
| `verify_citation` | Read | Проверяет что цитата существует в эссе (фикс cal_018 fabrication) |
| `csv_query` | Read | Query IELTS band descriptors из CSV |
| `calculator` | Read | Точное вычисление overall band (avg + round) |
| `summarizer` | Read | Compress essay history для memory pipeline |
| `notifier` | Write | Mock уведомление студенту о готовом фидбеке |

---

## Retry Logic — exponential backoff с jitter

Интеллектуальные, контекстно-зависимые стратегии: экспоненциальный backoff с jitter, адаптивная обработка ошибок и интеграция observability.

```python
import random, time

def retry_with_backoff(func, max_retries=3, base_delay=1.0):
    for attempt in range(max_retries + 1):
        try:
            return func()
        except TransientError as e:
            if attempt == max_retries:
                raise
            # Jitter предотвращает "thundering herd"
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            time.sleep(delay)
```

---

## Traces — формат для Tool Harness

```json
{
  "trace_id": "uuid",
  "session_id": "user_42_2026-05-01",
  "steps": [
    {
      "step": 1,
      "tool": "word_count",
      "reason": "check if essay meets minimum length",
      "args": {"text": "Technology is..."},
      "result": {"count": 83, "meets_minimum": false, "flag": "⚠️ 83 words < 250"},
      "latency_ms": 2,
      "status": "success",
      "retries": 0
    },
    {
      "step": 2,
      "tool": "calculator",
      "reason": "compute overall band from criteria scores",
      "args": {"scores": [4.0, 5.0, 4.5, 4.5]},
      "result": {"overall": 4.5, "capped": true, "cap_reason": "essay < 150 words"},
      "latency_ms": 1,
      "status": "success",
      "retries": 0
    }
  ],
  "tool_selection_accuracy": 1.0,
  "invalid_args_rate": 0.0,
  "recovery_rate": null,
  "total_latency_ms": 3
}
```

---

## Связь с предыдущими неделями

| Неделя | Что даёт для Tool Calling |
|---|---|
| 3 (Memory) | `summarizer` tool заменяет compressed_context() функцию |
| 4 (Eval) | Tool selection accuracy → новый тест в runner.py |
| 5 (Judge) | `verify_citation` tool устраняет fabrication из cal_018 |

---

## Что дальше — День 2-3

Пишем все 6 tools + tool_registry.py:
```
tools/
  word_count.py       ← 30 строк, детерминированный
  verify_citation.py  ← semantic check
  csv_query.py        ← pandas query по IELTS данным
  calculator.py       ← band score math
  summarizer.py       ← LLM summary через API
  notifier.py         ← mock webhook
  tool_registry.py    ← регистр + logging + trace export
```

---

*Неделя 6 из 12 | AI Product Engineer Journey | GainScore*
