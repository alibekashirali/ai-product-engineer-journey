# Reflection — Week 7
**Week:** 7 of 12 — Multi-Agent Systems
**Status:** ✅ Complete — pipeline работает, brief 658 слов, named competitors + pricing data

---

## Что было сделано за неделю

| Артефакт | Статус |
|---|---|
| `theory-notes-week7.md` — Think-Act-Observe, supervisor, swarm | ✅ |
| `agents/base_agent.py` — BaseAgent + AgentStep | ✅ |
| `agents/planner.py` — декомпозиция задачи | ✅ |
| `agents/researcher.py` — сбор данных, text format | ✅ |
| `agents/analyst.py` — структурированный анализ, text format | ✅ |
| `agents/critic.py` — PASS/FAIL с rubric, text format | ✅ |
| `agents/writer.py` — markdown brief | ✅ |
| `agents/orchestrator.py` — conditional routing + retry | ✅ |
| `pipeline.py` — запуск одной командой | ✅ |
| Research brief (658 words) | ✅ |

---

## Главный инсайт недели

**Текстовые форматы надёжнее JSON для LLM output в агентных системах.**

Это был главный практический урок. Все три попытки сделать JSON output закончились `JSONDecodeError` при truncation — сначала у researcher, потом у analyst, потом у critic. Переход на `KEY: value` текстовый формат решил проблему радикально. JSON требует замыкающих скобок — текст не требует ничего.

Второй инсайт: **Conditional routing работает — но feedback loop нужно направлять правильно.** Critic давал правильный feedback ("sections cut off mid-sentence"), но orchestrator отправлял его researcher'у — а проблема была в analyst. Это архитектурный баг: feedback от critic должен идти к тому агенту который создал проблему, а не всегда к researcher.

Третий инсайт: **Writer спас pipeline даже при FAIL quality gate.** Brief получился отличным несмотря на то что analyst output был неполным. Это правильный дизайн — fallback behavior должен давать useful output, не падать.

---

## История итераций

| Итерация | Проблема | Фикс |
|---|---|---|
| 1 | researcher.py: JSONDecodeError (trailing comma) | Добавил `_parse_json()` с 3 уровнями защиты |
| 2 | researcher.py: JSONDecodeError (unterminated string) | Переписал на текстовый формат `FINDING_N:` |
| 3 | analyst.py: JSONDecodeError (truncation) | Переписал на текстовый формат `SECTION_N_TITLE:` |
| 4 | critic.py: JSONDecodeError (unterminated string) | Переписал на текстовый формат `VERDICT:` |
| 5 | planner.py: потенциальная проблема | Превентивно переписал на текстовый формат |
| **6** | **Pipeline работает, brief готов** | ✅ |

---

## Анализ финального pipeline run

**Метрики:**
```
Total steps:   48
Retries:       3 (все три — по причине analyst truncation)
Quality Gate:  FAIL (score=0.55)
Elapsed:       333.7s
Brief:         658 words
```

**Что сработало хорошо:**
- Researcher: 20 findings (5 per subtask), confidence=high для 3 из 4
- Analyst: 3 sections, confidence=0.7 — данные есть, но обрезанные
- Writer: отличный brief с $1.5-2.0B market size, named players, pricing $12-59/mo
- Conditional routing: orchestrator правильно ретраил при FAIL

**Что не сработало:**
- Quality Gate FAIL (0.55) — Critic видел "sections cut off mid-sentence" в analyst output
- Retry feedback ошибочно направлялся researcher'у, не analyst'у — проблема не решалась
- 333 секунды на полный run — слишком долго для production

---

## Failure Mode Analysis

### Failure 1: JSON truncation cascade
**Симптом:** JSONDecodeError в 4 из 5 агентов последовательно
**Причина:** LLM генерирует большой JSON → max_tokens обрезает → нет закрывающей `}`
**Fix:** Текстовый формат — нет закрывающих скобок, нет truncation

### Failure 2: Wrong retry target
**Симптом:** Critic говорил "sections cut off" → orchestrator рефинировал researcher → analyst снова обрезал
**Причина:** orchestrator.py всегда рефинирует researcher при любом failure mode
**Fix нужен:** orchestrator должен анализировать feedback и направлять к нужному агенту:
```python
if "cut off" in feedback or "incomplete" in feedback:
    analyst.increase_budget()  # увеличить max_tokens
else:
    researcher.refine(subtask, feedback)
```

### Failure 3: Latency (333s)
**Симптом:** 14 LLM calls из-за 3 retry циклов × 4 subtasks
**Причина:** retry рефинирует все subtasks, не только проблемные
**Fix нужен:** параллельный research (asyncio), selective retry

---

## Known Issues → Backlog

| Priority | Issue | Fix |
|---|---|---|
| 🔴 High | Retry направляется всегда к researcher, не к проблемному агенту | Анализировать feedback → routing decision |
| 🔴 High | 333s latency — слишком долго | Параллельный research с asyncio |
| 🟡 Medium | Analyst sections обрезаются при большом input | Ограничить findings_text до 2000 chars |
| 🟡 Medium | Quality Gate никогда не PASS в текущей конфигурации | Снизить порог до 0.5 или улучшить analyst |
| 🟢 Low | Плохой critic feedback передаётся в refine task | Очищать feedback от технических деталей |

---

## Что показал brief

Несмотря на FAIL quality gate, brief получился production-quality:
- **Market size:** $1.5-2.0B USD (2022-2023)
- **Named competitors:** Jasper, Grammarly, Copy.ai, Writesonic, Notion AI
- **Pricing:** $12-59/mo individual, $5k-100k+ enterprise
- **Trends:** freemium conversion, GTM platform pivot, platform encroachment
- **Opportunities:** regulated industries, vertical specialization, API plays

Writer агент спас pipeline — это правильный дизайн fallback behavior.

---

## Связь с реальными проектами

### GainScore — multi-agent pipeline
```
Planner    → определяет что оценивать (TA/CC/LR/GRA)
Researcher → достаёт историю студента из memory_pipeline (Week 3)
Analyst    → оценивает эссе по 4 критериям + tools (Week 6)
Critic     → проверяет оценки через LLM judge (Week 5)
Writer     → форматирует финальный фидбек
```

---

## Неделя 8 — что планирую

**Тема:** LangGraph vs CrewAI vs AutoGen сравнение

**Тот же сценарий** (research brief) → две реализации → matrix trade-offs.

**Ключевые вопросы:**
- Как LangGraph state graphs решают проблему wrong retry target?
- Как CrewAI упрощает agent definition?
- Который framework лучше для capstone (AI Market Intelligence Copilot)?

---

*Week 7 of 12 | AI Product Engineer Journey | GainScore*
