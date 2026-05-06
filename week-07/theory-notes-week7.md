# Theory Notes — Week 7
**Тема:** Multi-Agent Systems in Python
**Источники:** Polarix (SOTA 2025), Redis AI Agent Patterns, SitePoint Agentic Design 2026, AppsTek Corp, DataFlair

---

## Главный сдвиг в мышлении

| Single Agent (Недели 1-6) | Multi-Agent (Неделя 7) |
|---|---|
| Один LLM решает всё | Специализированные агенты в цепочке |
| Один context window | Каждый агент — чистый контекст |
| Линейное выполнение | Параллельное + условная маршрутизация |
| Один промпт | Система промптов с явными ролями |
| Ломается при сложных задачах | Масштабируется через декомпозицию |

> **Ключевой тезис:** не каждая задача требует fleet of agents. Лучший дизайн — минимально достаточный для задачи. Single agent с хорошими tools часто лучше сложного multi-agent pipeline.

---

## 3 Принципа

### Принцип 1 — Think-Act-Observe Loop (ReAct)

Think-Act-Observe паттерн разбивает agentic loop на три фазы в непрерывном цикле.

```
┌─────────────────────────────────────────────┐
│           AGENTIC LOOP (ReAct)              │
│                                             │
│  THINK  → агент оценивает контекст,         │
│            выбирает следующий шаг           │
│     ↓                                       │
│  ACT    → вызывает tool / API / subagent    │
│     ↓                                       │
│  OBSERVE → результат попадает в контекст    │
│     ↓                                       │
│  повторяем до достижения цели               │
└─────────────────────────────────────────────┘
```

ReAct отлично подходит для исследовательских задач где следующий шаг зависит от наблюдений. Plan-and-execute лучше для хорошо определённых multi-step задач где заранее декомпозированный план снижает количество лишних LLM вызовов.

### Принцип 2 — Изоляция контекста = точность

Изоляция обеспечивает что "Coder" агент не нуждается в знании инструментов веб-поиска — это держит context window чистым и выполнение точным.

Каждый субагент получает только то что ему нужно:
```
Planner    → видит: задачу пользователя + доступные агенты
Researcher → видит: подзадачу + search tools
Analyst    → видит: данные от researcher + схему анализа
Critic     → видит: output analyst + rubric качества
Writer     → видит: одобренный анализ + формат вывода
```

### Принцип 3 — Tool definitions важнее промптов

Когда команда Anthropic оптимизировала своего агента для SWE-bench в 2024, они тратили больше времени на определения инструментов, чем на промпты. Этот принцип остаётся актуальным по мере взросления разработки агентов.

---

## 2 Паттерна

### Паттерн 1 — Hierarchical Supervisor

Supervisor — это routing агент без внешних инструментов. Его единственная функция — анализировать входящий запрос и делегировать управление подходящему worker'у.

```
                    SUPERVISOR
                    (только routing)
                   /     |      \
              Planner  Analyst  Writer
              (search) (structure) (format)
```

**Когда использовать:** задачи с чёткими ролями, нужна предсказуемость, enterprise-scale.

### Паттерн 2 — Sequential Pipeline с Conditional Routing

```
Input
  ↓
Planner (декомпозиция)
  ↓
Researcher (сбор данных)
  ↓
Analyst (структурирование)
  ↓
Critic (оценка качества)
  ├── [PASS] → Writer (финальный output)
  └── [FAIL] → Researcher (повторный сбор)
```

**Когда использовать:** исследовательские задачи, creative workflows, нужна self-critique.

---

## 1 Антипаттерн

### ❌ Agent Soup — агенты без чётких ролей

Лучший дизайн — тот который соответствует конкретной задаче и ограничениям. Не каждая проблема требует fleet of agents.

Признаки Agent Soup:
- Агенты дублируют функции друг друга
- Нет чёткого ownership — кто отвечает за что
- Context передаётся весь, а не только нужная часть
- Нет stop condition — агенты зацикливаются

---

## 4 Архитектурных паттерна (полный список)

| Паттерн | Структура | Когда |
|---|---|---|
| **Sequential** | A → B → C | Шаги зависят друг от друга |
| **Parallel** | A, B, C одновременно → merge | Независимые подзадачи |
| **Supervisor** | Router → Workers | Динамическая маршрутизация |
| **Debate/Critic** | Agent ↔ Critic → consensus | Нужна проверка качества |

**Для Недели 7:** Sequential с Conditional Routing (Critic может отправить назад на Researcher).

---

## Think-Act-Observe в нашем pipeline

```python
# Planner — THINK
task = "Research SaaS market for project management tools"
plan = planner.think(task)
# → ["gather_market_data", "analyze_competitors", "identify_trends"]

# Researcher — ACT
data = researcher.act(plan["gather_market_data"])
# → вызывает web_search tools, возвращает raw data

# Analyst — OBSERVE + THINK + ACT
analysis = analyst.observe_and_analyze(data)
# → структурирует данные, выявляет паттерны

# Critic — OBSERVE + EVALUATE
critique = critic.evaluate(analysis)
# → PASS / FAIL с объяснением

# Writer — ACT (только если PASS)
brief = writer.write(analysis, critique)
# → финальный research brief
```

---

## Isolation Strategy для нашего pipeline

| Агент | Получает | НЕ получает |
|---|---|---|
| Planner | Тема исследования | Данные, историю |
| Researcher | Конкретную подзадачу | План других агентов |
| Analyst | Raw данные | Промпт researcher |
| Critic | Output analyst + rubric | Raw данные |
| Writer | Одобренный анализ | Всю переписку |

---

## Conditional Routing — когда Critic говорит FAIL

```python
MAX_RETRIES = 2
retries = 0

while retries <= MAX_RETRIES:
    data = researcher.gather(subtask)
    analysis = analyst.analyze(data)
    critique = critic.evaluate(analysis)
    
    if critique["verdict"] == "PASS":
        break
    
    # Critic объясняет что не так
    subtask = researcher.refine(subtask, critique["feedback"])
    retries += 1

if retries > MAX_RETRIES:
    # Fallback: writer работает с лучшим из имеющегося
    brief = writer.write(analysis, note="quality_gate_not_passed")
```

---

## Swarm vs Hierarchical vs Mesh

На практике большинство production систем используют гибридные паттерны: иерархическая система где leaf-level команды используют mesh координацию внутри. Pipeline где одна стадия запускает swarm для параллельного сбора данных.

| Тип | Масштаб | Наш выбор |
|---|---|---|
| **Sequential** | 2-5 агентов | ✅ Week 7 |
| **Hierarchical** | 5-20 агентов | Week 8 (LangGraph) |
| **Swarm** | 20-50+ агентов | Enterprise only |
| **Mesh** | Любой | Исследования |

---

## Связь с GainScore (применение)

Для GainScore multi-agent pipeline:

```
Planner       → определяет что именно оценивать в эссе
Researcher    → достаёт историю студента из memory_pipeline (Week 3)
Analyst       → оценивает эссе по 4 критериям (использует tools Week 6)
Critic        → проверяет оценки через LLM judge (Week 5)
Writer        → форматирует финальный фидбек
```

Каждый агент маленький, специализированный, с чистым контекстом.

---

## Что дальше — День 2-3

Строим Multi-agent Research Assistant:

```
orchestrator.py  ← координирует flow + conditional routing
planner.py       ← декомпозирует задачу исследования
researcher.py    ← собирает данные через web search
analyst.py       ← структурирует и анализирует
critic.py        ← self-critique с verdict PASS/FAIL
writer.py        ← финальный research brief
pipeline.py      ← запуск одной командой + лог шагов
```

**Сценарий:** "Research the SaaS project management market: key players, trends, pricing models" → финальный brief с логом всех шагов.

---

*Неделя 7 из 12 | AI Product Engineer Journey | GainScore*
