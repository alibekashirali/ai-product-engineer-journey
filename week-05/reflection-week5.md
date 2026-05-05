# Reflection — Week 5
**Week:** 5 of 12 — LLM-as-a-Judge
**Status:** ✅ Complete — 93% agreement, Quality Gate passed

---

## Что было сделано за неделю

| Артефакт | Статус |
|---|---|
| `theory-notes-week5.md` — reference-free/based, biases, calibration, 7 best practices | ✅ |
| `judge_groundedness.py` — citations quality judge | ✅ |
| `judge_usefulness.py` — exercise quality judge | ✅ |
| `judge_correctness.py` — band score accuracy judge | ✅ |
| `calibration.py` — 20-case calibration pipeline | ✅ |
| `manual_labels.json` — ручная разметка с обоснованием | ✅ |
| `calibration_report.md` — 93% agreement, 4 bugs found | ✅ |

---

## Главный инсайт недели

**Reference-based judges надёжнее reference-free.**

Correctness judge (reference-based, сравнивает с диапазоном) дал 100% agreement. Groundedness и usefulness (reference-free) дали 90%. Разница в том, что у correctness есть чёткий anchor — ожидаемый диапазон из dataset.json. У groundedness и usefulness якоря нет — только описание критериев в промпте.

Второй инсайт: **LLM-judge находит баги которые тесты не поймают.** Cal_018 — judge обнаружил fabricated citation ("yields returns across generations" не существует в эссе). Rubric.py с regex этого не поймает никогда — только семантический judge.

Третий инсайт: **Infrastructure bugs проявляются в eval раньше чем в production.** max_tokens=1000 truncated 3 responses из 20 (15%). Без judge calibration это осталось бы незамеченным до первой жалобы реального пользователя.

---

## Что нашёл calibration

### Правильные решения judges (53/57)

Judges хорошо справились с:
- Всеми Band 5-7 эссе на groundedness (14/14 correct)
- Всеми correctness проверками (17/17)
- Обнаружением слабых Exercise у Gemini-style фидбека (cal_012, cal_013, cal_014)
- Fabricated citation в cal_018

### Disagreements (4/57)

| Case | Judge | Human | Judge | Root Cause |
|---|---|---|---|---|
| cal_019 | groundedness | PASS | FAIL | Edge case: нечего цитировать при правильном отказе |
| cal_020 | groundedness | PASS | FAIL | Edge case: языковой отказ |
| cal_007 | usefulness | PASS | FAIL | max_tokens truncation |
| cal_020 | usefulness | PASS | FAIL | Edge case: нет Exercise при языковом отказе |

**Вывод:** все 4 disagreements объяснимы и решаемы. Ни один не указывает на принципиальную неработоспособность judge'а.

### Bugs найденные через calibration

**Bug 1 (Critical): max_tokens=1000 truncation**
Три response обрезаны: cal_017, cal_018 (полностью), cal_007 (частично). Следствие: truncated Exercise, fabricated citation, score deflation. Fix: max_tokens → 1500.

**Bug 2: Score deflation на Band 7 эссе**
Агент давал Band 5.0-6.0 для эссе с очевидной Band 7 лингвистикой (~155 слов). Word count penalty перевешивал качество письма. Fix нужен в промпте: "Word count affects TA only — not GRA, LR, CC scores."

**Bug 3: Edge case blindspot в judge промптах**
Judges не понимают что правильный отказ агента = PASS, не FAIL. Fix: добавить в judge промпт исключение для edge cases.

---

## Три judge'а — итоговая оценка

### Judge Groundedness (90%)
- Отлично находит отсутствие цитат (все 4 bad feedback кейса)
- Не справляется с edge case отказами (2 disagreements)
- **Production ready** с фиксом edge case exception

### Judge Usefulness (90%)
- Правильно отловил 4 слабых Exercise (cal_012, cal_013, cal_014, cal_020)
- Не может отличить truncation от плохого Exercise
- **Production ready** с фиксом edge case + max_tokens

### Judge Correctness (100%)
- Лучший judge — 17/17 correct
- Reference-based архитектура самая надёжная
- **Production ready без дополнительных фиксов**

---

## Эволюция eval системы

```
Неделя 4: rubric.py
  → Проверяет детерминированное (шкала, флаги, schema)
  → 83/83 = 100% на pytest
  → Не видит: качество цитат, полезность Exercise, уровень оценки

Неделя 5: + LLM judges
  → Проверяет субъективное (citations, exercise, accuracy)
  → 93% agreement с человеком
  → Нашёл: fabricated citation, score deflation, truncation bug

Полная система:
  Code eval (rubric.py)  →  детерминированное  →  100% надёжно
  LLM judges (3 judges)  →  субъективное       →  93% надёжно
  = production-ready eval pipeline
```

---

## Связь с реальными проектами

### GainScore
Calibration report дал конкретный backlog:
1. `max_tokens: 1500` — фикс в одну строку, критический
2. Word count rule fix — в промпте, 1 предложение
3. Edge case exception — в judge промптах

Следующий шаг из calibration_report: **два из найденных багов становятся Tool Calling задачами** в Неделе 6:
- `check_word_count(essay)` → детерминированный tool
- `verify_citation(quote, essay)` → tool предотвращающий fabrication

---

## Открытые вопросы → следующие недели

| Вопрос | Когда |
|---|---|
| Как автоматически детектировать truncation в responses? | Неделя 6: Tool Calling |
| Нужен ли judge для multi-agent систем (Неделя 7)? | Неделя 7-8 |
| Как добавить judges в CI/CD pipeline? | Неделя 11 |
| Score smoothing (n_runs=3) — стоит ли оно стоимости? | Требует эксперимента |

---

## Метрика недели

**Quality Gate из плана:** judge agreement с ручной оценкой ≥ 80%.

| Judge | Agreement | Gate |
|---|---|---|
| groundedness | 90% | ✅ |
| usefulness | 90% | ✅ |
| correctness | 100% | ✅ |
| **Overall** | **93%** | **✅ PASSED** |

---

## Неделя 6 — что планирую

**Тема:** Tool Calling & Agent Harness

**Что строю:**
```
tools/
  word_count.py       ← детерминированный, заменяет промпт-инструкцию
  verify_citation.py  ← предотвращает fabrication (найдено в cal_018)
  csv_query.py        ← query IELTS scoring data
  summarizer.py       ← compress long essay history
  notifier.py         ← mock notification tool
  tool_registry.py    ← регистр всех tools + logging + traces
```

**Связь с Неделями 4-5:** два бага из calibration_report становятся первыми двумя tools.

---

*Week 5 of 12 | AI Product Engineer Journey | GainScore*
