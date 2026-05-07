# LangGraph vs CrewAI — Comparison Note
**Topic:** Research AI writing tools market
**Week:** 8 of 12

---

## Результаты реальных запусков

| Метрика | LangGraph | CrewAI |
|---|---|---|
| **Quality Gate** | ✅ PASS | ✅ PASS |
| **Score** | 0.72 | **0.87** |
| **Elapsed** | **86.7s** | 235.2s |
| **Retries** | 0 | 0 |
| **Steps / Tasks** | 10 steps | 5 tasks |
| **Brief length** | 471 слов | ~650 слов |
| **Строк кода** | ~270 | ~180 |
| **Pricing data** | Общий ($1.5-2.2B) | **Конкретный** ($1.67B→$8.5B, 26.3% CAGR) |
| **Named companies** | ChatGPT, Claude (обобщённо) | **Jasper ($75M→$45M ARR), Harvey AI ($715M), Grammarly ($400M ARR)** |

---

## Качество brief — сравнение

### LangGraph brief
**Сильные стороны:**
- Чёткая структура (3 trend + 2 opportunity + 2 risk)
- Хороший анализ "post-hype recalibration"
- Профессиональный тон

**Слабые стороны:**
- Мало конкретных данных — "$1.5B–$2.2B" без источника
- Нет названий конкретных компаний с цифрами
- Секция "Research Objectives" выглядит как заглушка, не как инсайт
- Score 0.72 — Critic правильно оценил

### CrewAI brief
**Сильные стороны:**
- Конкретные цифры везде: $1.67B, 26.3% CAGR, $715M, 30M DAU, 345M seats
- Таблица pricing с 7 сегментами — сразу actionable
- 4 структурных тира конкурентов с named examples
- Jasper как "cautionary case" — сильный инсайт
- Score 0.87 — заслуженно

**Слабые стороны:**
- В 2.7x медленнее LangGraph (235s vs 87s)
- Нет conditional retry — если бы качество было ниже, не смог бы автоматически исправить

---

## Архитектурное сравнение

### Conditional Routing — главный баг Week 7

| | Week 7 (pure Python) | LangGraph | CrewAI |
|---|---|---|---|
| Retry target | Всегда → researcher ❌ | `route_after_critic()` → нужный агент ✅ | Нет retry loop ⚠️ |
| Как настроить | Ручная if-else логика | `add_conditional_edges()` | Нужен отдельный Flow |

LangGraph решает баг нативно. CrewAI в sequential process не имеет встроенного retry — нужен CrewAI Flows (более сложный API).

### State Management

```python
# LangGraph — явный typed state
class ResearchState(TypedDict):
    topic: str
    findings: list
    analysis: dict
    critique: dict
    retry_count: int    # ← явный счётчик
    retry_reason: str   # ← явная причина для routing

# CrewAI — неявный context через Task outputs
Task(
    context=[previous_task]  # ← автоматически передаётся
)
```

LangGraph: полный контроль над state, каждое поле явное.
CrewAI: автоматическая передача контекста, меньше boilerplate.

### Debugging

```
LangGraph:
  [14:46:50] [Planner] decompose → plan_ready: 3 subtasks
  [14:46:55] [Researcher] research → findings_ready: 12 findings
  [14:47:39] [Analyst] analyze → analysis_ready: 2 sections
  [14:47:49] [Critic] verdict: PASS (score=0.72)
  [14:47:57] [Writer] brief_ready: 471 words
  Полный JSON log с timestamps ✅

CrewAI:
  Verbose output в консоль (crewai встроенный)
  Нет структурированного JSON step log ⚠️
  LangSmith интеграция — отдельная настройка
```

---

## Trade-offs матрица

| Критерий | LangGraph | CrewAI | Победитель |
|---|---|---|---|
| **Скорость** | 86.7s | 235.2s | 🏆 LangGraph (2.7x быстрее) |
| **Качество brief** | 0.72 | 0.87 | 🏆 CrewAI (+21% качество) |
| **Conditional routing** | Нативный | Отсутствует | 🏆 LangGraph |
| **Строк кода** | ~270 | ~180 | 🏆 CrewAI (-33%) |
| **Debugging** | JSON log + timestamps | Verbose console | 🏆 LangGraph |
| **Setup time** | Часы | Минуты | 🏆 CrewAI |
| **State control** | Полный (TypedDict) | Автоматический | 🏆 LangGraph |
| **Agent context** | Явный (state поля) | Автоматический (context=[]) | 🏆 CrewAI (проще) |

**Счёт: LangGraph 4 — CrewAI 4** (ничья по отдельным критериям)

---

## Почему CrewAI дал лучший brief

Интересный парадокс: CrewAI в 2.7x медленнее, но качество выше (0.87 vs 0.72). Причина — **накопленный контекст**.

В CrewAI каждый агент видит полный output всех предыдущих задач:
```
Writer видит: plan + research + analysis + critique
```

В LangGraph writer видит только `state["analysis"]` — researcher и planner outputs не передаются напрямую.

**Вывод:** CrewAI's automatic context accumulation помогает writer агенту синтезировать все данные. Но это же замедляет pipeline — каждый последующий агент получает всё больший контекст.

---

## Когда использовать что

| Сценарий | Выбор | Причина |
|---|---|---|
| Прототип за день | CrewAI | Меньше кода, быстрый старт |
| Нужен conditional retry | LangGraph | Нативные conditional edges |
| Production observability | LangGraph | JSON traces, LangSmith |
| Линейный pipeline | CrewAI | Меньше overhead |
| Сложный workflow с циклами | LangGraph | State machine — его сильная сторона |
| Максимальное качество brief | CrewAI | Накопленный контекст = лучший writer output |
| Минимальная latency | LangGraph | 86s vs 235s |

---

## Рекомендация для capstone (Week 12)

**AI Market Intelligence Copilot → LangGraph**

Причины:
1. Capstone требует conditional routing (judge → правильный агент)
2. Нужна production observability (JSON traces для portfolio)
3. Latency важна для interactive demo
4. Явный state control упрощает debugging при презентации

**Но** — взять у CrewAI идею accumulated context: передавать researcher findings напрямую в writer через state, не только через analyst.

---

## Итог

Оба фреймворка решили задачу. CrewAI дал лучший brief. LangGraph дал лучшую архитектуру. Для production capstone — LangGraph с паттерном accumulated context из CrewAI.

---

*Week 8 of 12 | AI Product Engineer Journey*
