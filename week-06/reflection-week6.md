# Reflection — Week 6
**Date:** 2026-05-05
**Week:** 6 of 12 — Tool Calling & Agent Harness
**Status:** ✅ Complete — 11/11 tool calls, 100% quality gates

---

## Что было сделано за неделю

| Артефакт | Статус |
|---|---|
| `theory-notes-week6.md` — schemas, retry, traces, failure categories | ✅ |
| `tools/base.py` — ToolResult контракт | ✅ |
| `tools/word_count.py` — детерминированный подсчёт | ✅ |
| `tools/verify_citation.py` — anti-fabrication guard | ✅ |
| `tools/calculator.py` — точный band score | ✅ |
| `tools/csv_query.py` — официальные IELTS дескрипторы | ✅ |
| `tools/summarizer.py` — сжатие истории | ✅ |
| `tools/notifier.py` — mock уведомление с idempotency | ✅ |
| `tools/tool_registry.py` — регистр + tracing | ✅ |
| `agent_with_tools.py` — агент с tool calling | ✅ |
| `eval_report_week6.md` — анализ реального trace | ✅ |

---

## Главный инсайт недели

**Детерминированные правила в коде — это не ограничение, это архитектура.**

До Недели 6 band cap был в промпте. Нарушался 3/83 раз. После переноса в `calculator` tool — 0 нарушений, детерминированно. Это прямое продолжение вывода Недели 4: промпт управляет поведением, код управляет правилами.

Второй инсайт: **tools меняют природу ошибок**. Без tools агент мог галлюцинировать цитаты (cal_018), давать нестабильные band scores, не иметь трассировки. С tools каждое действие явное, проверяемое и логируемое. Debugging занял минуты, не часы.

Третий инсайт: **агент самостоятельно выбирает правильный порядок**. word_count первым, notifier последним — без жёсткого принуждения, просто из описаний tools. Хорошие tool descriptions работают лучше жёстких инструкций.

---

## Что показал реальный trace (c6af9933)

### Tool sequence агента
```
word_count → csv_query ×4 → verify_citation ×4 → calculator → notifier
```

Агент сам вывел логику: сначала контекст (длина), потом знания (дескрипторы), потом верификация (цитаты), потом математика (band), потом действие (уведомление).

### verify_citation — главная находка
Агент попытался процитировать "technology has both advantages and disadvantages and we should use it carefully" — полной фразы нет в эссе. Tool вернул `partial match` + `suggested_action`. Агент скорректировал цитату. Fabrication закрыта без дополнительного промптинга.

### calculator — детерминированный band cap
56-слов эссе → все критерии 4.0 → среднее 4.0 → cap не нужен (4.0 ≤ 4.5). Корректно. При любом другом результате (например, критерии 5.0) cap сработал бы автоматически.

### notifier — Write tool с idempotency
Первый вызов: `sent: true`. Повторный вызов с тем же session_id: `sent: false, reason: duplicate`. Идемпотентность работает без дополнительной логики в промпте.

---

## Эволюция системы

```
Week 1-2: Промпт управляет всем (включая числовые правила)
          → Нестабильный band cap, нет трассировки

Week 3:   + Memory pipeline
          → Персистентная история, 3 режима контекста

Week 4:   + Eval harness (pytest)
          → 83/83, нашли band cap как системную проблему

Week 5:   + LLM judges
          → 93% agreement, нашли fabrication (cal_018)

Week 6:   + Tool calling
          → calculator закрыл band cap
          → verify_citation закрыл fabrication
          → tool_registry даёт полную трассировку
          → 100% quality gates
```

---

## Связь с реальными проектами

### GainScore
Tool calling превращает агента из "умного промпта" в реальный production компонент:
- `word_count` → заменить промпт-инструкцию в FastAPI endpoint
- `calculator` → PostgreSQL function или Python сервис
- `verify_citation` → middleware перед сохранением фидбека в БД
- `notifier` → интегрировать с SendGrid (уже в стеке)
- `tool_registry` → Datadog или CloudWatch для tracing

---

## Known Issues (для backlog)

| Issue | Severity | Fix |
|---|---|---|
| `user_id=0` в notifier — агент не знает реального ID | Medium | Передавать через system prompt или context |
| `summarizer` не вызывался — нет истории у test user | Low | Ожидаемо, нужен тест с реальной историей |
| Trace args truncated до 100 символов | Low | Дизайн-решение для читаемости, не баг |

---

## Открытые вопросы → следующие недели

| Вопрос | Когда |
|---|---|
| Как координировать несколько агентов параллельно? | Неделя 7: Multi-Agent |
| Как передавать tool results между агентами? | Неделя 7-8: LangGraph |
| Как добавить tool_registry в CI/CD для мониторинга? | Неделя 11 |

---

## Метрика недели

**Quality Gate из плана:** tool selection accuracy, invalid args rate, recovery rate в eval отчёте.

| Метрика | Результат | Gate |
|---|---|---|
| Tool Selection Accuracy | 100% | ✅ |
| Invalid Args Rate | 0% | ✅ |
| Success Rate | 100% | ✅ |
| Fabrication Prevention | 0 fabricated | ✅ |

---

## Неделя 7 — что планирую

**Тема:** Multi-Agent Systems

**Что строю:**
```
agents/
  planner.py      ← разбивает задачу на подзадачи
  researcher.py   ← собирает данные (с tools из Week 6)
  analyst.py      ← анализирует результаты
  critic.py       ← проверяет качество
  writer.py       ← генерирует финальный output
  orchestrator.py ← координирует всех агентов
```

**Связь с Week 6:** каждый подагент использует tool_registry — tracing работает через всю цепочку.

**Связь с GainScore:** multi-agent pipeline для GainScore:
planner (определяет что оценивать) → researcher (достаёт историю студента) → analyst (оценивает эссе) → critic (проверяет оценки) → writer (форматирует фидбек).

---

*Week 6 of 12 | AI Product Engineer Journey | GainScore*
