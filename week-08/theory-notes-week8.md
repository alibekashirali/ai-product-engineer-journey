# Theory Notes — Week 8
**Тема:** LangGraph vs CrewAI — Framework Comparison
**Источники:** DataCamp, DEV Community (2026), OpenAgents Blog, Gurusup, instinctools

---

## Главный сдвиг в мышлении

| Week 7 (Pure Python) | Week 8 (Frameworks) |
|---|---|
| Сам пишешь orchestration | Framework берёт это на себя |
| Ручной state management | Built-in state persistence |
| Самодельный retry | Conditional edges / process types |
| print() для debugging | LangSmith / built-in logging |
| Полный контроль | Меньше кода, больше conventions |

> **Ключевой вопрос:** какой framework решает главный баг Week 7 — wrong retry target?

---

## 2 Принципа

### Принцип 1 — Две философии, два разных mental model

CrewAI делает акцент на распределении ролей, LangGraph — на структуре workflow. Это не просто API разница — это разный способ думать о проблеме.

```
CrewAI    → "У меня есть команда. Кто за что отвечает?"
LangGraph → "У меня есть граф. Куда идём после этого шага?"
```

### Принцип 2 — Форма workflow определяет выбор framework

Если workflow линейный с чёткими ролями — CrewAI. Если workflow имеет циклы, ветвление и условную маршрутизацию — LangGraph. Главная ошибка — выбирать framework по YouTube туториалу, а не по форме задачи.

**Вывод для Недели 8:** наш research pipeline имеет цикл (critic → retry), поэтому LangGraph — естественный выбор. CrewAI протестируем как альтернативу для сравнения.

### Принцип 3 — Learning curve определяет время до первого результата

У CrewAI самый низкий порог входа — role-based DSL, 20 строк для старта. У LangGraph выше — нужно понять концепции графов и управления состоянием.

```
CrewAI:    30 минут до working prototype
LangGraph: несколько часов до working prototype
           (но потом гораздо лучше debuggability)
```

---

## 2 Паттерна

### Паттерн 1 — LangGraph: State Machine с conditional edges

LangGraph рассматривает агентные workflow как направленный граф: узлы — это функции или LLM вызовы, рёбра определяют управление потоком между ними. Состояние передаётся через граф как типизированный словарь.

```python
# Решение бага Week 7 (wrong retry target) через conditional edges:
def route_after_critic(state: State) -> str:
    feedback = state["critique"]["feedback"]
    if "cut off" in feedback or "incomplete" in feedback:
        return "analyst"      # ← направляем к analyst, не researcher
    elif "insufficient data" in feedback:
        return "researcher"   # ← направляем к researcher
    else:
        return "writer"       # ← PASS → writer

graph.add_conditional_edges("critic", route_after_critic, {
    "analyst":    "analyst",
    "researcher": "researcher",
    "writer":     "writer"
})
```

**Ключевые фичи:**
- **Checkpointing** — возобновление после сбоя с любой точки
- **Time travel** — повтор с любого узла с другими входными данными
- **LangSmith** — пошаговые трассировки с количеством токенов на каждый узел
- Устойчивое выполнение — агенты могут пережить сбой и возобновить работу автоматически

### Паттерн 2 — CrewAI: Role-based Crews + Flows (обновление 2025)

CrewAI моделирует агентов как команду — каждый с определённой ролью, предысторией и целью. В 2025 году CrewAI добавил Flows — режим event-driven пайплайнов для более предсказуемых, production-ориентированных рабочих процессов.

```python
# Тот же pipeline в CrewAI:
researcher = Agent(
    role="Market Research Specialist",
    goal="Gather comprehensive market data",
    backstory="Expert in competitive intelligence",
    tools=[search_tool]
)

research_task = Task(
    description="Research AI writing tools market",
    agent=researcher,
    expected_output="Structured findings with named competitors"
)

crew = Crew(
    agents=[planner, researcher, analyst, critic, writer],
    tasks=[plan_task, research_task, analyze_task, critique_task, write_task],
    process=Process.sequential
)

result = crew.kickoff()
```

**Ключевые фичи:**
- Минимальный boilerplate — 20 строк для работающего прототипа
- Встроенное управление памятью
- Бесшовное управление состоянием с координацией агентов из коробки
- **Слабость:** логирование — огромная боль. Обычные print и log функции плохо работают внутри Task, что делает дебаггинг крайне сложным.

---

## 1 Антипаттерн

### ❌ Выбирать framework по популярности, не по задаче

Самая распространённая ошибка команд — выбрать framework из YouTube туториала, а потом бороться с ним когда форма workflow не совпадает с тем для чего он создан.

**Decision tree:**

```
У тебя есть циклы и conditional routing?
  → ДА → LangGraph

Нужен working prototype за день (линейный workflow)?
  → ДА → CrewAI

Нужна production durability + observability?
  → LangGraph (+ LangSmith)
```

---

## Полная матрица trade-offs

| Критерий | LangGraph | CrewAI |
|---|---|---|
| **Архитектура** | Направленный граф, state machine | Ролевые crews + Flows |
| **Learning curve** | Высокий | Низкий |
| **Setup time** | Часы | 30 минут |
| **State persistence** | Встроенный checkpointing + time travel | Результаты задач последовательно |
| **Debugging** | LangSmith — отличный | Логирование очень плохое |
| **Conditional routing** | Нативный (conditional edges) | Ограниченный |
| **Retry logic** | Явный через graph edges | Ручной или через Flows |
| **Циклы (A→B→A)** | ✅ Нативный | ⚠️ Болезненный |
| **Параллелизм** | ✅ | ⚠️ |
| **Model agnostic** | ✅ | ✅ |
| **Production матurity** | Klarna, Replit, Elastic | SMB/Enterprise |
| **Строк кода** | Больше | Меньше |
| **Главный use case** | Сложные workflow с ветвлением | Линейные ролевые пайплайны |

---

## Как каждый решает баг Week 7

**Баг:** orchestrator всегда ретраит researcher при любом failure mode от critic.

| Framework | Решение |
|---|---|
| **Week 7 (pure Python)** | Ручная логика в `orchestrator.py` — сложно и хрупко |
| **LangGraph** | `route_after_critic()` — conditional edge анализирует feedback и направляет к нужному узлу |
| **CrewAI** | Task delegation через `context` — менее гибко, требует ручного управления |

**LangGraph побеждает** на этом конкретном сценарии — conditional edges это его native сила.

---

## Что строим в Week 8

**Вариант A — LangGraph:**
```python
StateGraph(ResearchState)
  .add_node("planner",    planner_node)
  .add_node("researcher", researcher_node)
  .add_node("analyst",    analyst_node)
  .add_node("critic",     critic_node)
  .add_node("writer",     writer_node)
  .add_conditional_edges("critic", route_after_critic)
  .compile()
```

**Вариант B — CrewAI:**
```python
Crew(
    agents=[planner, researcher, analyst, critic, writer],
    tasks=[...],
    process=Process.sequential
).kickoff()
```

**Измеряем:**
- Количество строк кода
- Время на настройку
- Задержка (vs Week 7: 333s)
- Удобство дебаггинга
- Решён ли баг с wrong retry target?

---

## Рекомендация для capstone

**Capstone (Week 12):** AI Market Intelligence Copilot — research + analysis + report.

| Критерий | Вес | LangGraph | CrewAI |
|---|---|---|---|
| Conditional routing (критично для retry) | 30% | ✅ 10/10 | ⚠️ 5/10 |
| Production observability | 25% | ✅ 10/10 | ❌ 3/10 |
| Сложность настройки | 20% | ⚠️ 6/10 | ✅ 9/10 |
| Удобство дебаггинга | 15% | ✅ 10/10 | ❌ 4/10 |
| Экосистема / сообщество | 10% | ✅ 8/10 | ✅ 7/10 |
| **Итоговый балл** | | **8.8** | **5.7** |

**Рекомендация: LangGraph для capstone.**

Причины: capstone требует conditional routing (critic → правильный агент), production observability (LangSmith), и reliability. CrewAI — для быстрых прототипов, не для production-grade capstone.

---

## Связь с твоими проектами

### GainScore
LangGraph: `evaluate → judge → route: [pass→format | fail→re-evaluate]`
Conditional edges решают проблему нестабильного band cap из Week 4.


---

*Неделя 8 из 12 | AI Product Engineer Journey*
