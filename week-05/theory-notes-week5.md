# Theory Notes — Week 5
**Тема:** LLM-as-a-Judge
**Источники:** Monte Carlo Data (7 Best Practices), Survey on LLM-as-Judge (Gu et al. 2025), Cameron Wolfe PhD


---

## Главный сдвиг в мышлении

| Неделя 4 (Eval Harness) | Неделя 5 (LLM-as-Judge) |
|---|---|
| Code проверяет детерминированное | LLM проверяет субъективное |
| "Есть ли ⚠️ в ответе?" | "Цитирует ли ответ нужный фрагмент?" |
| Regex/string matching | Семантическое понимание |
| 100% надёжно, 0% нюансов | ~85% надёжно, 100% нюансов |
| Быстро, дёшево | Медленнее, дороже |

**Вывод:** Code eval + LLM-judge = полное покрытие. Не "или", а "и".

---

## Часть 1 — Reference-free vs Reference-based

```
┌────────────────────────────────────────────────────────────┐
│  REFERENCE-FREE                                            │
│  Оцениваем output сам по себе, без эталонного ответа      │
│                                                            │
│  Вопросы: Связно ли? Полезно ли? Соответствует ли тону?   │
│  Когда: нет правильного ответа, субъективные качества      │
│  Пример GainScore: "Полезен ли Exercise для студента?"     │
│  Риск: judge может придумывать критерии                    │
├────────────────────────────────────────────────────────────┤
│  REFERENCE-BASED                                           │
│  Сравниваем output с эталоном (reference answer)          │
│                                                            │
│  Вопросы: Совпадает ли с ожидаемым? Точнее или хуже?      │
│  Когда: есть правильный ответ или golden standard          │
│  Пример GainScore: "Правильно ли определён band score?"    │
│  Риск: эталон может быть неполным или спорным             │
└────────────────────────────────────────────────────────────┘
```

**Для GainScore используем оба:**
- Reference-free: groundedness (цитирует ли текст), usefulness (Exercise конкретный?)
- Reference-based: correctness (band score близок к ожидаемому диапазону?)

---

## Часть 2 — Три режима оценки

Три методологии: Pointwise, Pairwise и Pass/Fail.

```
POINTWISE    → Оцениваем один output по шкале (1-5, 0/1)
               Просто, масштабируется
               Слабость: не улавливает относительное качество

PAIRWISE     → Сравниваем два output, выбираем лучший
               Лучше улавливает разницу
               Слабость: медленнее (2x API calls), position bias

PASS/FAIL    → Бинарное решение с объяснением
               Легко интегрируется с pytest
               Слабость: теряет градации качества
```

**Для GainScore:** Pass/Fail с объяснением — легко интегрируется с существующим runner.py.

---

## Часть 3 — Judge Biases (что ломает судью)

MT-Bench и Chatbot Arena выявили систематические проблемы — position bias и verbosity bias.

### 4 главных bias:

**1. Verbosity Bias** — судья предпочитает длинные ответы
```
Фикс: в judge промпте явно указать "длина не является критерием качества"
```

**2. Position Bias** — в pairwise судья предпочитает первый ответ
```
Фикс: менять порядок и брать среднее (swap augmentation)
```

**3. Self-Enhancement Bias** — модель предпочитает ответы похожие на свои
```
Фикс: использовать другую модель как judge (не ту же что генерирует)
```

**4. Sycophancy Bias** — судья соглашается с оценкой в запросе
```
Фикс: не включать предыдущие оценки в judge промпт
```

---

## Часть 4 — 7 Best Practices (Monte Carlo)

### 1. Few-shot prompting
Исследователи обнаружили, что все модели работали лучше с одним примером, но при добавлении большего их количества качество снижалось.

**Правило:** 1-2 примера оптимально. Больше 3 — overfitting.

### 2. Step Decomposition (Chain-of-Thought)
Сначала judge думает → потом выносит вердикт:
```
Step 1: Find quotes from the essay in the feedback
Step 2: Check if they are specific (>4 words)
Step 3: Check if they relate to the criterion being discussed
Step 4: Output PASS or FAIL with explanation
```

### 3. Criteria Decomposition
Один judge = один критерий. Не смешивать.
```
❌ "Оцени правильность, полезность и тон одновременно"
✅ judge_groundedness.py  ← только цитаты
✅ judge_usefulness.py    ← только Exercise
✅ judge_tone.py          ← только тон
```

### 4. Evaluation Template (Grading Rubric)
Структурированный шаблон вместо свободного описания:
```
CRITERIA: [что именно проверяем]
PASS condition: [конкретное описание что значит PASS]
FAIL condition: [конкретное описание что значит FAIL]
EVIDENCE: [что надо процитировать из ответа]
```

### 5. Constrain to Structured Outputs
```python
# Judge возвращает только JSON:
{
  "verdict": "PASS" | "FAIL",
  "score": 0.0-1.0,
  "evidence": "конкретная цитата из ответа агента",
  "reasoning": "1-2 предложения объяснения"
}
```

### 6. Provide Explanations
Judge должен объяснять решение — это помогает калибровке и debugging.
Prometheus достиг корреляции Pearson 0.897 с оценками людей именно благодаря объяснениям.

### 7. Score Smoothing
Запускай judge несколько раз (N=3) и бери среднее — снижает variance:
```python
scores = [judge(response) for _ in range(3)]
final = sum(scores) / len(scores)  # PASS если > 0.66
```

---

## Часть 5 — Calibration (как проверить что judge работает)

**Calibration = judge agreement с ручной оценкой человека.**

Quality Gate Недели 5: agreement ≥ 80% на 20 outputs.

### Процесс:
```
1. Генерируем 20 outputs от агента (разные кейсы из dataset.json)
2. Размечаем вручную: PASS/FAIL по каждому критерию
3. Запускаем judge на тех же 20 outputs
4. Считаем agreement rate = совпадения / 20
5. Анализируем disagreements — где judge ошибается?
```

### Метрики agreement:
```python
# Simple agreement
agreement = sum(human[i] == judge[i] for i in range(20)) / 20

# Cohen's Kappa (учитывает случайное совпадение)
from sklearn.metrics import cohen_kappa_score
kappa = cohen_kappa_score(human_labels, judge_labels)
# κ > 0.6 = substantial agreement
# κ > 0.8 = almost perfect agreement
```

---

## Когда НЕ использовать LLM-judge

Оценка outputs без опоры на предопределённые референсы — для числовых ограничений это ненадёжно.

```
❌ Детерминированные правила (band score из шкалы)    → код
❌ Наличие конкретного слова/символа (⚠️)             → regex
❌ Математические проверки (word count)                → код
❌ Критически важные safety проверки                   → код

✅ Качество цитирования (правильные ли слова выбраны?) → judge
✅ Педагогическая ценность Exercise                    → judge
✅ Тон (честный vs лесть vs грубость)                 → judge
✅ Семантическое соответствие теме                    → judge
```

---

## Применение к GainScore — 3 judge'а

### Judge 1: Groundedness
**Вопрос:** Цитирует ли фидбек конкретные фразы из эссе студента?
**Почему важно:** rubric.py уже проверяет наличие кавычек — но не проверяет что цитата релевантна критерию.

### Judge 2: Usefulness
**Вопрос:** Exercise — конкретное письменное задание или общий совет?
**Почему важно:** Gemini в Неделе 2 давал списки идей вместо конкретного задания. Regex этого не поймает.

### Judge 3: Correctness
**Вопрос:** Соответствуют ли band scores уровню эссе?
**Почему важно:** агент может давать правильный формат (из IELTS шкалы) но неправильный уровень (6.5 для Band 5 эссе).

---

## Сравнение с предыдущими неделями

| | Неделя 2 | Неделя 4 | Неделя 5 |
|---|---|---|---|
| Как проверяем | Вручную, глазами | pytest, regex | LLM judge |
| Что проверяем | Всё субъективно | Детерминированное | Субъективное |
| Масштаб | 3 модели × 1 эссе | 30 кейсов автоматически | 20 outputs с calibration |
| Можно в CI/CD | ❌ | ✅ | ✅ (с порогом) |

---

## Что дальше — День 2

Пишем 3 judge промпта:
1. `judge_groundedness.py` — citations quality
2. `judge_usefulness.py` — exercise quality
3. `judge_correctness.py` — band score accuracy

Каждый возвращает JSON: `{verdict, score, evidence, reasoning}`

---

*Неделя 5 из 12 | AI Product Engineer Journey | GainScore*
