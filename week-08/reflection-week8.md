# Reflection — Week 8
**Date:** 2026-05-07
**Week:** 8 of 12 — LangGraph vs CrewAI
**Status:** ✅ Complete — оба фреймворка запущены, реальные данные получены

---

## Что было сделано за неделю

| Артефакт | Статус |
|---|---|
| `theory-notes-week8.md` — state graphs, crews, trade-offs | ✅ |
| `langgraph_pipeline.py` — StateGraph с conditional edges | ✅ |
| `crewai_pipeline.py` — настоящий crewai 1.14.4 | ✅ |
| Два реальных run на одном топике | ✅ |
| `comparison_note.md` — матрица trade-offs с реальными данными | ✅ |

---

## Главный инсайт недели

**Парадокс скорости vs качества.**

LangGraph в 2.7x быстрее (87s vs 235s). CrewAI дал лучший brief (score 0.87 vs 0.72). Это не случайность — это архитектурное следствие.

В CrewAI каждый агент видит accumulated context всех предыдущих задач. Writer получил plan + research + analysis + critique → написал Jasper ($75M→$45M ARR), Harvey AI ($715M valuation), 7-сегментную pricing таблицу. В LangGraph writer видел только `state["analysis"]` — более изолированный контекст дал более абстрактный brief.

**Вывод:** accumulated context = лучшее качество, но больше токенов = медленнее. Это fundamental trade-off, не баг.

Второй инсайт: **условная маршрутизация — главное преимущество LangGraph.** `route_after_critic()` в 5 строках решил баг Week 7 который мы неделю пытались починить в pure Python. Это и есть смысл frameworks — они кодифицируют паттерны которые иначе пишешь вручную.

---

## Реальные данные сравнения

| Метрика | LangGraph | CrewAI |
|---|---|---|
| Quality Gate | PASS (0.72) | PASS (0.87) |
| Elapsed | **86.7s** | 235.2s |
| Retries | 0 | 0 |
| Steps/Tasks | 10 steps | 5 tasks |
| Brief length | 471 слов | ~650 слов |
| Named companies | Обобщённо | Конкретно с цифрами |
| Conditional routing | ✅ Нативный | ❌ Нет в sequential |
| Строк кода | ~270 | ~180 |

**Итог:** LangGraph 4 побед — CrewAI 4 побед (ничья по разным критериям)

---

## Почему CrewAI дал лучший brief несмотря на то что медленнее

Ключевое архитектурное различие:

```
LangGraph writer:
  state["analysis"] → brief
  (видит только synthesis)

CrewAI writer:
  plan_output + research_output + analysis_output + critique_output → brief
  (видит всё накопленное)
```

CrewAI writer увидел сырые данные researcher'а напрямую — Jasper ARR collapse, Harvey AI valuation, конкретные pricing benchmarks. LangGraph writer видел уже синтезированный анализ, потеряв конкретику.

**Фикс для capstone:** добавить в LangGraph state поле `raw_findings` и передавать его в writer node напрямую.

---

## Баг Week 7 — решён в LangGraph

Conditional routing в 5 строк:
```python
def route_after_critic(state) -> str:
    if state["critique"]["verdict"] == "PASS":
        return "writer"
    if state["critique"]["issue_type"] == "data":
        return "researcher"   # ← правильная маршрутизация
    return "analyst"          # ← а не всегда researcher
```

В Week 7 это была ручная if-else логика которая всегда шла к researcher. LangGraph кодифицирует этот паттерн как conditional edges — стандартный, тестируемый, переиспользуемый.

---

## Проблема с Python версией

CrewAI 1.14.4 требует Python 3.10+ из-за синтаксиса `Type | None`. У меня Python 3.9. Решил через обновление Python на машине. Это реальный production риск — указывать `python_requires >= "3.10"` в зависимостях.

---

## Связь с реальными проектами

### GainScore — capstone architecture
На основе сравнения определилась финальная архитектура:

```
LangGraph StateGraph:
  essay_input
    → word_count (tool, детерминированный)
    → evaluator (4 критерия + цитаты)
    → judge (LLM-as-judge из Week 5)
    → route_after_judge:
        PASS → formatter
        FAIL (citations) → evaluator (retry)
        FAIL (scores) → evaluator (retry)
    → formatter
    → notifier (tool, write)

State: {essay, word_count, scores, citations, critique, feedback, retries}
```

Плюс добавить `raw_findings` паттерн из CrewAI — передавать memory summary напрямую в formatter.

### Segmentic / TanimAI
CrewAI подходит для быстрого прототипирования persona pipeline:
- Меньше кода
- Накопленный контекст естественен для persona evaluation
- Линейный flow: profile_loader → persona → evaluator → reporter

---

## Открытые вопросы → следующие недели

| Вопрос | Когда |
|---|---|
| Как добавить `raw_findings` в LangGraph state? | Capstone (Week 12) |
| LangSmith setup для production tracing? | Week 11 |
| Как параллелизовать research tasks в LangGraph? | Week 12 оптимизация |

---

## Метрика недели

**Quality Gate из плана:** матрица trade-offs и рекомендация для capstone.

✅ Матрица создана на основе реальных данных (не теоретическая)
✅ Рекомендация: LangGraph для capstone + accumulated context паттерн из CrewAI

---

## Неделя 9 — что планирую

**Тема:** Lovable MVP — строим интерфейс

**Что строю:**
Первый полноценный UI для GainScore Writing Coach с tool calling из Week 6 и memory pipeline из Week 3. FastAPI backend + React frontend или Streamlit для быстрого MVP.

**Ключевые вопросы:**
- Как подключить LangGraph pipeline к FastAPI endpoint?
- Как отобразить tool traces в UI?
- Как сделать memory (история эссе) видимой для студента?

---

*Week 8 of 12 | AI Product Engineer Journey | GainScore*
