# Theory Notes — Week 4
**Тема:** Eval-Driven Development / Harness Engineering
**Источники:** OpenAI Evaluation Best Practices, Pragmatic Engineer (Hamel Husain), OpenAI Cookbook

---

## Главный сдвиг в мышлении

| Vibes-based development | Eval-driven development |
|---|---|
| "Выглядит нормально → запускаем" | "Метрика зелёная → запускаем" |
| Ручная проверка 5 примеров | Автоматический прогон 30+ кейсов |
| Ломается незаметно при изменении промпта | Регрессия выявляется сразу |
| Нет данных о том где именно плохо | Точный roadmap по failure modes |

> **Vibes-based development trap:** меняешь промпт, тестируешь пару входов, "LGTM" — и запускаешь. Потом продукт ломается в продакшене на edge cases которые ты не проверял.

---

## 3 Принципа

### Принцип 1 — Три Gulf'а (разрыва)

Любой LLM проект страдает от трёх фундаментальных разрывов:

```
Gulf of Comprehension  → разрыв между тем что делает модель и твоим пониманием
                          "невозможно вручную прочитать все запросы и ответы"

Gulf of Specification  → разрыв между тем что ты хочешь и что написано в промпте
                          "LLM не читает мысли — underspecified prompt = непредсказуемый output"

Gulf of Generalization → разрыв между хорошим промптом и поведением на новых данных
                          "даже идеальные инструкции могут сломаться на необычных входах"
```

**Evals закрывают все три разрыва** — дают систематическое измерение вместо интуиции.

### Принцип 2 — Error Analysis первым делом

Прежде чем писать тесты — сначала найди реальные failure modes через **error analysis**:

```
1. Open coding    → просматриваешь 50-100 outputs, пишешь свободные заметки
                    "агент не попросил уточнить" / "оценка завышена" / "цитата отсутствует"

2. Axial coding   → группируешь заметки в 5-10 тем (LLM помогает кластеризовать)
                    "word count issues" / "score inflation" / "missing citations"

3. Pivot table    → считаешь частоту каждой категории
                    → получаешь data-driven roadmap что фиксить первым
```

**Антипаттерн:** брать готовые метрики ("hallucination score", "helpfulness 1-5") без понимания что они означают для твоего продукта. Команды оптимизируют скоры которые не коррелируют с тем что важно пользователям.

### Принцип 3 — Два типа evaluators, не один

| Тип | Когда использовать | Пример для GainScore |
|---|---|---|
| **Code-based eval** | Детерминированные, объективные проверки | Band score из IELTS шкалы? Word count посчитан правильно? |
| **LLM-as-judge** | Субъективные, нюансированные оценки | Цитирует ли фидбек конкретный текст? Полезен ли Exercise? |

---

## 2 Паттерна

### Паттерн 1 — Golden Dataset

Золотой стандарт eval — это **заранее размеченный датасет** с ожидаемым поведением:

```json
{
  "id": "test_001",
  "category": "short_essay",
  "input": "Technology is good. People use phones. (45 words)",
  "expected": {
    "overall_band_max": 4.5,
    "word_count_flag": true,
    "schema_complete": true,
    "cites_text": true
  }
}
```

Структура хорошего golden dataset:
- Покрывает все **категории** входных данных (короткие/длинные, слабые/сильные, edge cases)
- Содержит **ожидаемое поведение**, а не ожидаемый точный ответ (LLM недетерминирован)
- Включает **граничные случаи** которые обычно ломают агентов

### Паттерн 2 — Eval Flywheel

```
Analyze (смотришь на outputs)
    ↓
Measure (пишешь тесты под найденные failure modes)
    ↓
Improve (фиксишь промпт / pipeline)
    ↓
Automate (добавляешь в CI/CD)
    ↓
Analyze снова (production data добавляет новые кейсы)
```

Evals не останавливаются на деплое — это **непрерывный процесс**. Production data → новые eval кейсы → улучшение модели.

---

## 1 Антипаттерн

### ❌ Generic метрики без domain-специфики

Команда mental health стартапа заполнила дашборд "helpfulness 1-5" и "factuality 1-5". Скоры выглядели хорошо. Но команда не могла объяснить разницу между 3 и 4 — и метрики не коррелировали с тем что важно пользователям.

**Фикс:** пусть failure modes выходят из твоих данных, не из готовых чеклистов. Для GainScore правильные метрики: "score_in_ielts_scale", "cites_text", "exercise_has_scope", "no_score_inflation" — не абстрактная "accuracy".

---

## Анатомия Eval Harness

```
evals/
├── dataset.json       ← Golden dataset: 30 кейсов, 5 категорий
├── rubric.py          ← Функции pass/fail для каждого критерия
├── runner.py          ← pytest: вызывает агента, применяет rubric
└── results.json       ← Результаты: pass/fail + детали по каждому кейсу
```

### dataset.json — структура кейса

```json
{
  "id": "test_001",
  "category": "under_150_words",
  "description": "Очень короткое эссе, должен сработать band cap",
  "input_essay": "...",
  "expected": {
    "overall_band_max": 4.5,
    "word_count_flag": true,
    "all_criteria_scored": true,
    "uses_ielts_scale": true,
    "cites_text": true,
    "has_priority_focus": true,
    "has_exercise": true,
    "exercise_has_followup": true,
    "no_essay_written": true
  }
}
```

### rubric.py — функции проверки

```python
def check_ielts_scale(score: float) -> bool:
    """Band score должен быть из официальной шкалы"""
    valid = {4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0}
    return score in valid

def check_word_count_flag(response: str, essay: str) -> bool:
    """Если эссе < 250 слов — флаг должен быть в ответе"""
    wc = len(essay.split())
    if wc < 250:
        return "⚠️" in response or "word count" in response.lower()
    return True

def check_band_cap(overall: float, essay: str) -> bool:
    """Overall Band ≤ 4.5 если эссе < 150 слов"""
    if len(essay.split()) < 150:
        return overall <= 4.5
    return True

def check_cites_text(response: str, essay: str) -> bool:
    """Каждый критерий должен цитировать текст эссе"""
    # Ищем слова из эссе в кавычках внутри фидбека
    words = set(essay.lower().split())
    quoted = re.findall(r'"([^"]+)"', response)
    for quote in quoted:
        if any(w in quote.lower() for w in words if len(w) > 4):
            return True
    return False
```

### runner.py — pytest структура

```python
import pytest
import json

dataset = json.load(open("evals/dataset.json"))

@pytest.mark.parametrize("case", dataset)
def test_schema_complete(case, agent_response):
    """Все поля output schema заполнены"""
    assert "Overall Band" in agent_response
    assert "Priority Focus" in agent_response
    assert "Exercise" in agent_response

@pytest.mark.parametrize("case", dataset)
def test_band_cap_short_essays(case, agent_response):
    """Band cap для коротких эссе"""
    if len(case["input_essay"].split()) < 150:
        band = extract_overall_band(agent_response)
        assert band <= 4.5, f"Band {band} > 4.5 for {len(case['input_essay'].split())} word essay"
```

---

## 5 Категорий для dataset.json (30 кейсов = 6 × 5)

| Категория | Кол-во | Что тестирует |
|---|---|---|
| `under_150_words` | 6 | Band cap, word count flag |
| `band_5_essays` | 6 | Baseline quality, цитаты |
| `band_6_essays` | 6 | Nuanced feedback, улучшения |
| `band_7_essays` | 6 | Не завышает, видит тонкие ошибки |
| `edge_cases` | 6 | Отказ писать эссе, не-английский, Task 1 |

---

## Применение к GainScore

### Что проверяем детерминированно (code-based):
- Band score из официальной IELTS шкалы
- Overall Band = среднее 4 критериев ± 0.25
- Word count flag при < 250 слов
- Band cap ≤ 4.5 при < 150 слов
- Schema complete (все поля присутствуют)
- Exercise заканчивается на "Submit your work here..."
- Отказ написать эссе (нет "Here is your essay:")

### Что проверяем через LLM-judge (Неделя 5):
- Цитирует ли конкретные фразы из эссе
- Полезен ли Exercise (конкретное задание vs общие советы)
- Тон (честный, не грубый)
- Прогресс из памяти упомянут если есть

---

## Сравнение с прошлыми неделями

| | Неделя 1-2 | Неделя 3 | Неделя 4 |
|---|---|---|---|
| Как проверяем качество | Вручную | Ручной бенчмарк | Автоматически (pytest) |
| Количество тестов | 3-9 кейсов | 1 эссе × 3 режима | 30 кейсов автоматически |
| Что ловим | Очевидные ошибки | Режимы памяти | Регрессии + edge cases |
| Можно в CI/CD? | ❌ | ❌ | ✅ |

---

## Что дальше — День 2

Строим `dataset.json` — 30 кейсов по 5 категориям.
Каждый кейс содержит: эссе + expected поведение (не точный ответ).
Используем синтетические эссе — GPT/Claude генерирует разные уровни.

---

*Неделя 4 из 12 | AI Product Engineer Journey*
