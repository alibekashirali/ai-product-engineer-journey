# Case Study: GainScore IELTS Writing Coach
**Тип:** AI-powered EdTech product  
**Стек:** Claude API · LangGraph · SQLite · pytest · Streamlit  
**Статус:** Production-ready agent, deployed on Railway  
**Длительность разработки:** Weeks 1-6 (6 недель итеративно)

---

## Проблема

Казахстанские студенты готовятся к IELTS без качественного письменного фидбека. Репетиторы стоят $30-80/час, онлайн-инструменты дают generic советы без привязки к тексту эссе.

**Ключевые ограничения:**
- Фидбек должен цитировать конкретные фразы из эссе (не общие советы)
- Band score должен быть из официальной IELTS шкалы (4.0, 4.5, 5.0... 9.0)
- Агент не должен писать эссе за студента
- Должна быть персональная память — прогресс между сессиями

---

## Решение

Специализированный LLM агент с tool calling, памятью студента и LLM judges для контроля качества.

### Архитектура

```
Essay Input
    ↓
word_count tool         ← детерминированный подсчёт слов
    ↓
4 Criteria Scoring      ← TA / CC / LR / GRA по IELTS шкале
  ↓ (для каждого критерия)
verify_citation tool    ← проверяет что цитата существует в эссе
    ↓
calculator tool         ← Overall Band = avg(4 scores), band cap при <150 слов
    ↓
csv_query tool          ← официальные IELTS дескрипторы для обоснования
    ↓
Feedback + Exercise     ← конкретное письменное задание
    ↓
notifier tool           ← уведомление студенту (idempotency key)
    ↓
Memory Save             ← SQLite: essay_sessions + user_profiles
```

### Memory Pipeline (3 режима)

| Режим | Токены | Качество | Когда |
|---|---|---|---|
| full_context | 701 | Baseline | sessions ≤ 2 |
| compressed_context | 524 (-25%) | -15% GRA | ❌ Не используем |
| retrieved_context | 470 (-33%) | = Full | sessions > 2 |

**Решение:** retrieved_context — hybrid BM25 + cosine search по истории. Находит сессии с похожими ошибками → модель видит конкретный прогресс "было/стало".

---

## Ключевые инженерные решения

### 1. Band Cap в коде, не в промпте

**Проблема:** промпт "NEVER award Overall Band above 4.5 if essay < 150 words" нарушался 3/83 раз (3.6%). Агент сам писал "hard ceiling rule" — и всё равно ставил 5.5.

**Решение:**
```python
def apply_band_cap(response: str, essay: str) -> str:
    wc = len(essay.split())
    if wc >= 150:
        return response
    band = extract_overall_band(response)
    if band is None or band <= 4.5:
        return response
    # Заменяем число в ответе программно
    return re.sub(r'(\*\*Overall Band[:\*]*\*?\*?)\s*([\d.]+)',
                  lambda m: f'{m.group(1)} 4.5', response, count=1)
```

**Результат:** Run 1 → 80/83. Run 4 (с кодом) → **83/83 (100%)**.

**Принцип:** детерминированные правила всегда в коде. Промпт управляет стилем и педагогикой — не числовыми ограничениями.

### 2. verify_citation — anti-fabrication guard

**Проблема:** в Week 5 calibration, cal_018 — агент процитировал "yields returns across generations". Эта фраза не существует в эссе. Fabricated citation.

**Решение:** `verify_citation(quote, essay)` tool вызывается перед включением любой цитаты в фидбек:
```
PARTIAL match: "technology has both advantages" → 
suggest: "advantages and disadvantages and we should use it"
```

Агент использует suggested_action и корректирует цитату. В реальном trace c6af9933 — 4 вызова verify_citation, 0 fabrications.

### 3. LLM Judges для контроля качества

Три независимых судьи с 93% agreement с ручной разметкой:

| Judge | Что проверяет | Agreement |
|---|---|---|
| judge_correctness | Band scores в диапазоне | 100% |
| judge_groundedness | Цитаты из реального текста | 90% |
| judge_usefulness | Exercise — задание, не совет | 90% |

Correctness — reference-based (сравнение с ожидаемым диапазоном). Groundedness и Usefulness — reference-free.

---

## Eval Results

### Eval Harness (Week 4)

| Run | Passed | Failed | Fix |
|---|---|---|---|
| Run 1 | 80/83 | band cap u003/u004/u006 | промпт → код |
| Run 2 | 79/83 | e006 не детектируется | rubric расширен |
| Run 3 | 79/83 | b7006 занижен | dataset скорректирован |
| **Run 4** | **83/83** | — | **apply_band_cap() ✅** |

### LLM Judge Calibration (Week 5)

```
Calibration на 20 outputs:
  judge_correctness:  17/17 = 100% ✅
  judge_groundedness: 18/20 = 90%  ✅
  judge_usefulness:   18/20 = 90%  ✅
  Overall:            53/57 = 93%  ✅ (threshold: 80%)
```

### Tool Calling Trace (Week 6)

```
Trace c6af9933 (56-word essay):
  Step 1:  word_count      → 56 words, cap=true        0.0ms
  Step 2-5: csv_query ×4   → IELTS дескрипторы         0.0ms each
  Step 6-9: verify_citation×4 → 3 partial, 1 exact     0.1ms each
  Step 10: calculator      → band=4.0, capped=false     0.1ms
  Step 11: notifier        → sent=true (idempotent)     0.1ms

Tool Selection Accuracy: 100%
Invalid Args Rate:       0%
Fabricated Citations:    0
Total Tool Latency:      0.5ms
```

---

## Что узнал

**Техническое:**
- Retrieval quality > generation quality. Retrieved context нашёл похожие ошибки → LR дал 7.0 вместо 6.5 у Full context.
- JSON ломается при truncation. Text format (`KEY: value`) — надёжнее для агентных систем.
- Один tool call = один ответ на один вопрос. 11 tool calls, 0.5ms — это правильный granularity.

**Продуктовое:**
- Студент хочет знать конкретно что исправить — не абстрактный совет. Exercise с "Submit here" = следующий шаг в одном клике.
- Band score — это социальный сигнал ("я Band 6.5!"). Точность критична для доверия.

**Для PhD Research:**
- Knowledge Tracing через LLM memory: можно предсказывать следующую ошибку студента по паттернам прошлых.
- Adaptive exercise generation: difficulty level основан на текущем score — не на fixed curriculum.

---

## Roadmap

- [ ] PostgreSQL + Alembic миграции (вместо SQLite)
- [ ] FastAPI endpoint для мобильного приложения
- [ ] A/B тест prompt v1 vs v4 на реальных студентах
- [ ] Multilingual support (Казахский, Русский)
- [ ] Stripe subscription ($9/mo student, $29/mo teacher)

---

*Week 1-6 of AI Product Engineer Journey*
