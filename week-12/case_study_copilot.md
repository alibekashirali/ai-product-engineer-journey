# Case Study: AI Market Intelligence Copilot
**Тип:** Multi-agent research pipeline + Streamlit MVP  
**Стек:** LangGraph · CrewAI · Streamlit · APScheduler · SQLite · Anthropic API  
**Статус:** Live MVP + weekly automation  
**Длительность разработки:** Weeks 7-11 (5 недель)

---

## Проблема

Маркетологи и стратеги тратят 4-8 часов на ручной research рынка. Результат — неструктурированные заметки без единого формата, без контроля качества, без автоматизации.

**Ключевые ограничения:**
- Brief должен содержать named companies с конкретными цифрами (не "крупные игроки")
- Quality gate: автоматическая проверка перед доставкой
- Automation: weekly scheduled runs без ручного запуска
- Observability: ops dashboard с историей и алертами

---

## Решение

5-агентная LangGraph система с conditional routing, weekly automation и Streamlit UI.

### Архитектура pipeline

```
Topic Input
    ↓
Planner Agent      ← 3-4 subtasks с конкретными research вопросами
    ↓
Researcher Agent   ← данные по каждой подзадаче (text format, не JSON)
    ↓
Analyst Agent      ← structured analysis: sections, trends, opportunities
    ↓
Critic Agent       ← PASS/FAIL по rubric (specificity, evidence, actionability)
    ↓
route_after_critic():
  PASS → Writer
  FAIL (issue_type=data)     → Researcher (retry)
  FAIL (issue_type=analysis) → Analyst   (retry ← фикс бага Week 7)
  retries > 2               → Writer (best effort)
    ↓
Writer Agent       ← markdown brief 400-650 слов
    ↓
RunResult → CSVExporter + JSONExporter + SlackNotifier + EmailNotifier
```

### Ключевое архитектурное решение: text format вместо JSON

**Проблема:** все 4 агента ломались с JSONDecodeError при truncation. LLM генерирует большой JSON → max_tokens обрезает → нет закрывающей `}`.

**Решение:**
```
# НЕ ТАК (ломается при truncation):
{"findings": [{"point": "Jasper AI leads...", "detail": "...

# ТАК (не ломается никогда):
FINDING_1: Jasper AI leads enterprise market
DETAIL_1: $75M ARR declined to $45M after ChatGPT launch
FINDING_2: Copy.ai pivoted to GTM AI Platform
DETAIL_2: 10M+ users, escape commoditization strategy
```

**Результат:** 0 JSONDecodeError после переписывания всех агентов.

---

## LangGraph vs CrewAI Comparison (Week 8)

Один топик, два фреймворка, реальные данные:

| Метрика | LangGraph | CrewAI |
|---|---|---|
| Quality Score | 0.72 | **0.87** |
| Elapsed | **86.7s** | 235.2s |
| Brief length | 471 слов | ~650 слов |
| Conditional routing | ✅ Native | ❌ Нет |
| Debugging | ✅ JSON traces | ⚠️ Verbose console |
| Setup complexity | Высокая | **Низкая** |

**Парадокс:** CrewAI медленнее, но качество выше. Причина — accumulated context: Writer видит outputs всех предыдущих агентов, не только Analyst. Результат: конкретные данные (Jasper $75M ARR, Harvey AI $715M valuation) попадают в brief.

**Решение для production:** LangGraph + паттерн accumulated context. Добавить `raw_findings` поле в state → передавать напрямую в Writer.

### Почему LangGraph для capstone

```python
# Фикс бага Week 7 в 5 строках:
def route_after_critic(state: ResearchState) -> str:
    if state["critique"]["verdict"] == "PASS":
        return "writer"
    if state["critique"]["issue_type"] == "data":
        return "researcher"   # ← правильная цель
    return "analyst"          # ← не всегда researcher!
```

В pure Python (Week 7) эта логика была ручной if-else которая всегда шла к researcher. LangGraph кодифицирует это как conditional edges.

---

## Streamlit MVP (Week 9)

5 экранов, dark theme (Space Mono + DM Sans), full demo flow за ~3 минуты:

```
Landing     → hero + 3 feature cards
Onboarding  → textarea + 4 quick-pick examples
Pipeline    → animated agent steps + progress bar
Report      → metrics + 3 tabs (Brief / Trace / Export)
Feedback    → star rating + 3 dimension sliders
```

**Quality Gate:** пользователь прошёл "EdTech platforms in Central Asia" → PASS · 0.84 · 87s · 10 steps · 289 words.

---

## Automation Stack (Week 10)

```python
# Одна команда запускает весь цикл:
python3 weekly_pipeline.py "Research AI writing tools market"

# Результат:
→ RunResult(run_id, topic, quality, score, elapsed, cost_tokens)
→ CSVExporter    → reports/history.csv  (строка в таблицу)
→ JSONExporter   → reports/run_id.json  (полный лог)
→ SheetsExporter → mock Google Sheets
→ SlackNotifier  → "✅ PASS · score=0.87 · 235s"
→ EmailNotifier  → weekly summary
→ DeadLetter     → при FAIL или score < 0.65
```

**Реальные данные из 8 runs:**

| Run | Topic | Quality | Score | Elapsed |
|---|---|---|---|---|
| 111602 | AI writing tools | PASS | 0.68 | 105s |
| 111747 | SaaS PM tools | FAIL | 0.35 | 117s |
| 111944 | EdTech Central Asia | PASS | 0.68 | 82s |
| 112218 | B2B analytics (demo) | PASS | 0.82 | 1.2s |

**Failure mode обнаружен:** SaaS PM tools получил FAIL при 2 retries потому что Analyst стабильно возвращал 1 секцию. Conditional routing правильно шёл к Analyst — но данные не менялись. Fix: при analyst_retries > 1 → researcher.refine().

---

## Production Readiness (Week 11)

5 из 10 failure modes решены:

| Failure Mode | Решение |
|---|---|
| Latent inconsistency | `apply_band_cap()` в коде |
| Hallucination | `verify_citation` tool |
| Context degradation | retrieved_context -33% |
| Tool invocation errors | ToolResult validation |
| Schema drift | text format вместо JSON |

**Cost:** ~$0.059/run (~8100 токенов). При 1000 users → $236/month. С context caching → ~$80/month.

**Human Review Queue:** score 0.65-0.85 → SQLite очередь → CLI review:
```bash
python3 human_review_queue.py list
python3 human_review_queue.py review run_20260508_111747
```

---

## Что узнал

**Техническое:**
- Multi-agent systems имеют cascading failure: плохой Researcher → плохой Analyst → плохой brief. Изоляция контекста критична.
- Frameworks решают реальные проблемы: conditional routing в LangGraph = 5 строк vs 50 строк ручной логики.
- Production ≠ demo: 3 провайдера + circuit breaker + dead letter queue — это минимум.

**Продуктовое:**
- Brief с конкретными цифрами (Jasper $75M ARR, Harvey AI $715M) — воспринимается совершенно иначе чем "крупные игроки".
- Demo flow за 3 минуты — это не компромисс, это product requirement.
- Weekly automation превращает pipeline в продукт — от CLI инструмента к сервису.

---

## Roadmap

- [ ] Deploy на Railway с real-time SSE streaming
- [ ] Подключить web_search tool (реальный research вместо LLM knowledge)
- [ ] Google Sheets интеграция (gspread)
- [ ] Slack bot для on-demand research
- [ ] Подписка: $49/mo для маркетологов, $199/mo для команд

---

*AI Market Intelligence Copilot · Week 7-11 of AI Product Engineer Journey*
