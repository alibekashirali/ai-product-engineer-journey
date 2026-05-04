# Reflection — Week 3
**Week:** 3 of 12 — Long Context + Memory + RAG
**Status:** ✅ Complete

---

## Что было сделано за неделю

| Артефакт | Статус |
|---|---|
| `theory-notes-week3.md` — RAG, память, contextual retrieval | ✅ |
| `memory_pipeline.py` — три режима с SQLite | ✅ |
| Бенчмарк — реальный запуск на API | ✅ |
| `benchmark-memory.md` — анализ результатов | ✅ |

---

## Главный инсайт недели

**Память — это не промпт. Это архитектура.**

До этой недели `{{user_memory}}` в Context Pack был просто плейсхолдером. Теперь это реальная таблица `essay_sessions` в SQLite, функция `retrieved_context()` с hybrid search, и понятная логика: какой режим когда использовать.

Второй инсайт: **качество retrieval важнее качества генерации.** Retrieved режим дал LR 7.0 против 6.5 у Full — не потому что модель "умнее", а потому что hybrid search нашёл правильные сессии. Модель увидела конкретный контраст "было 5.0 → стало 7.0" и дала точный фидбек. Мусор на входе → мусор на выходе.

---

## Что узнал из бенчмарка

### 1. Retrieved Context — production winner
- Токенов: 470 (−33% vs Full)
- Quality: идентично Full по всем критериям, LR даже лучше
- Причина: hybrid BM25 + cosine нашёл сессии с аналогичными ошибками → модель видит чёткий "было/стало"

### 2. Compressed Context ломается на деталях
- GRA упал на 1.0 балл (15%) — превысил Quality Gate в 10%
- Суммаризация сгладила конкретику про article errors
- Модель начала галлюцинировать исправления там где их нет
- **Вывод:** summary prompt нужно явно требовать сохранять дословные recurring errors

### 3. Quality Gate — итог

| Режим | Результат |
|---|---|
| Retrieved | ✅ Пройден (все критерии ≤ 10% от Full) |
| Compressed | ❌ Не пройден (GRA −15%) |

---

## Что было сложно

**Hybrid search без внешних библиотек.** Хотел использовать `sentence-transformers` для настоящих эмбеддингов, но решил сначала сделать работающий baseline на чистом Python (BM25 + cosine через TF). Это правильное решение — сначала простое рабочее, потом улучшение. В Неделе 6 (Tool Calling) подключу настоящие эмбеддинги через pgvector.

**Word count расхождение.** Скрипт считал разное количество слов для одного эссе в разных режимах (158/178/189). Причина — разные способы токенизации. Нужна единая функция `count_words()` — зафиксировал в списке фиксов.

---

## Связь с реальными проектами

### GainScore
`memory_pipeline.py` — это уже прототип реального memory layer. Следующий шаг: заменить SQLite на PostgreSQL (уже в стеке), добавить Alembic миграцию для таблиц `essay_sessions` и `user_profiles`, подключить к FastAPI endpoint.

Production логика режимов:
```python
if sessions_count <= 2:   → full_context
if sessions_count <= 10:  → retrieved_context  # оптимум
if sessions_count > 10:   → retrieved + background compression
```

### Segmentic / TanimAI
Та же архитектура, другие данные:
- `essay_sessions` → `creative_tests` (результаты тестов рекламных креативов)
- `user_profiles` → `persona_profiles` (сегмент, поведенческие паттерны)
- Retrieved режим: находит похожие тесты по типу креатива/аудитории

---

## Открытые вопросы → следующие недели

| Вопрос | Когда отвечу |
|---|---|
| Как автоматически проверить качество фидбека без ручной оценки? | Неделя 5: LLM-as-a-Judge |
| Как убедиться что retrieved режим стабилен на 30+ разных эссе? | Неделя 4: Eval Harness |
| Настоящие эмбеддинги vs TF cosine — разница в качестве retrieval? | Неделя 6: Tool Calling + pgvector |
| Как сжать старые сессии (>10) без потери GRA деталей? | Доработка compressed prompt |

---

## Метрика недели

**Quality Gate из плана:** accuracy в compressed/retrieved режиме ≤ 10% хуже full context.

✅ **Retrieved Context: пройден** — production-ready режим для GainScore
❌ **Compressed Context: не пройден** — требует доработки summary prompt

---

*Week 3 of 12 | AI Product Engineer Journey | GainScore*
