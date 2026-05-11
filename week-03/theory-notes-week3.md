# Long Context + Memory + RAG: Theory Notes — Week 3
**Источники:** Anthropic Contextual Retrieval, ML Mastery Memory Types, Edinburgh LTM paper

---

## Главный сдвиг в мышлении

| Неделя 1 | Неделя 2 | Неделя 3 |
|---|---|---|
| Что писать в промпте | Что передавать в контексте | Как хранить и извлекать нужное |
| System prompt | Context Pack | Memory + RAG pipeline |
| Одна сессия | Одна сессия с историей | Множество сессий, персистентная память |

---

## Часть 1 — Типы памяти агента

Строить агентов, которые учатся на опыте, требует трёх типов долгосрочной памяти: эпизодической, семантической и процедурной.

```
┌─────────────────────────────────────────────────────────┐
│                    ПАМЯТЬ АГЕНТА                        │
├─────────────────────────────────────────────────────────┤
│  SHORT-TERM (контекстное окно)                          │
│  → Текущий разговор, инструкции, данные сессии          │
│  → Аналог RAM: исчезает после закрытия сессии           │
├─────────────────────────────────────────────────────────┤
│  LONG-TERM (персистентное хранилище)                    │
│                                                         │
│  Episodic  → Конкретные прошлые события                 │
│              "3 сессии назад — ошибки с артиклями"      │
│              Хранится: vector DB или structured store   │
│                                                         │
│  Semantic  → Обобщённые факты о пользователе            │
│              "Пользователь — B2, цель 7.0, казах"       │
│              Хранится: JSON / PostgreSQL                │
│                                                         │
│  Procedural → Усвоенные паттерны поведения              │
│              "Этот пользователь отвечает на упражнения" │
│              Хранится: в промпте / fine-tuning          │
└─────────────────────────────────────────────────────────┘
```

### Для GainScore — что какой тип хранит:

| Тип | Что хранить | Где |
|---|---|---|
| Episodic | История эссе: текст, дата, оценки по 4 критериям | PostgreSQL таблица `essays` |
| Semantic | Профиль: уровень, цель, recurring ошибки, streak | PostgreSQL таблица `user_profiles` |
| Procedural | Тон агента, стиль фидбека | System prompt (уже есть) |

---

## Часть 2 — RAG: как это работает

### Базовая схема

```
User Query
    │
    ▼
┌─────────┐    ┌──────────────┐    ┌─────────────┐
│ Retrieve │───▶│   Augment    │───▶│  Generate   │
│ (поиск) │    │ (добавить в  │    │ (LLM даёт   │
│         │    │  контекст)   │    │  ответ)     │
└─────────┘    └──────────────┘    └─────────────┘
```

### Три метода retrieval:

**1. Keyword Search (BM25)**
- Ищет точные совпадения слов
- Быстрый, работает без GPU
- Слабый на семантику ("автомобиль" ≠ "машина")

**2. Semantic Search (Embeddings)**
- Текст → вектор → поиск ближайших векторов
- Понимает смысл, не слова
- Требует embedding модели

**3. Hybrid Search (Anthropic рекомендует)**
Интеграция контекстных эмбеддингов с контекстным BM25 привела к снижению частоты ошибок поиска в топ-20 чанках на 49% — с 5.7% до 2.9%.

```python
# Hybrid score = w1 * semantic_score + w2 * bm25_score
# Anthropic default: w1=0.8, w2=0.2
final_score = 0.8 * semantic_rank + 0.2 * bm25_rank
```

---

## Часть 3 — Contextual Retrieval (главная идея Anthropic)

### Проблема обычного RAG

Документ режется на чанки → контекст теряется:

```
Оригинал:
"Alibek получил 5.5 за Task Achievement в эссе от 28 апреля.
 Главная ошибка: не раскрыл вторую часть промпта."

Чанк после нарезки:
"Главная ошибка: не раскрыл вторую часть промпта."
← Непонятно: чья ошибка? Когда? За что оценка?
```

### Решение: Contextual Chunks

Anthropic предложила добавлять релевантный контекст к каждому чанку перед созданием эмбеддинга, чтобы сохранить более широкое понимание в рамках RAG.

```python
# Промпт для обогащения чанка контекстом:
contextualize_prompt = """
Here is the document:
<document>{full_document}</document>

Here is a chunk from the document:
<chunk>{chunk}</chunk>

Give a short 1-2 sentence context explaining where this chunk fits 
in the overall document. Answer only with the context, nothing else.
"""

# Результат:
# "Alibek (user_id=42), session 2026-04-28.
#  Main error: did not address the second part of the Task 2 prompt."
```

### Три режима работы с контекстом (твои три режима для Недели 3)

```
┌──────────────────────────────────────────────────────────────┐
│  FULL CONTEXT                                                │
│  Весь документ → в контекст                                 │
│  ✅ Максимальная точность                                    │
│  ❌ Дорого (токены), медленно, context rot при >20k         │
│  Когда: одно эссе, короткая история                         │
├──────────────────────────────────────────────────────────────┤
│  COMPRESSED CONTEXT                                          │
│  История → LLM суммаризирует → summary в контекст           │
│  ✅ Дёшево, быстро                                          │
│  ❌ Теряет детали, accuracy может упасть                    │
│  Когда: 5+ сессий, нужен только профиль пользователя        │
├──────────────────────────────────────────────────────────────┤
│  RETRIEVED CONTEXT (RAG)                                     │
│  Запрос → поиск релевантных чанков → только они в контекст  │
│  ✅ Точечно, масштабируется                                 │
│  ❌ Качество зависит от retrieval                           │
│  Когда: большая история, конкретный вопрос                  │
└──────────────────────────────────────────────────────────────┘
```

---

## Часть 4 — Ключевые метрики RAG

Качество LLM становится неважным, если поиск работает плохо — это помешает найти нужную информацию и прийти к верным выводам.

| Метрика | Что измеряет | Как посчитать |
|---|---|---|
| **Context Precision** | Из всего retrieved — сколько реально нужно? | retrieved_relevant / total_retrieved |
| **Context Recall** | Из всего нужного — сколько нашли? | retrieved_relevant / total_relevant |
| **Faithfulness** | Ответ основан на контексте или галлюцинирует? | LLM-as-judge |
| **Answer Relevance** | Ответ отвечает на вопрос? | LLM-as-judge |

**Quality Gate Недели 3:** accuracy в compressed/retrieved режиме ≤ 10% хуже full context.

---

## Часть 5 — Важный вывод из исследований

Memory-augmented подходы снижают использование токенов более чем на 90% при сохранении сопоставимой точности.

Это значит: **RAG не просто дешевле — он сопоставим по качеству с full context**, если retrieval настроен правильно.

Сложность архитектуры памяти должна соответствовать возможностям модели: маленькие модели выигрывают от RAG, а более сильные — от эпизодической памяти и богатых семантических структур.

---

## Применение к GainScore

### Что строим на Дне 2-3:

```python
# memory_pipeline.py — три функции:

def full_context(user_id, essay):
    """Загружает всю историю пользователя в контекст"""
    history = db.get_all_essays(user_id)
    return format_full_history(history) + essay

def compressed_context(user_id, essay):
    """Сжимает историю через LLM summary"""
    history = db.get_all_essays(user_id)
    summary = llm.summarize(history)  # ~200 токенов вместо ~2000
    return summary + essay

def retrieved_context(user_id, essay, query):
    """RAG: достаёт только релевантные сессии"""
    chunks = db.get_essay_chunks(user_id)
    relevant = retriever.search(query, chunks, top_k=3)
    return format_chunks(relevant) + essay
```

### Что храним в PostgreSQL:

```sql
-- Episodic memory
CREATE TABLE essay_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    essay_text TEXT,
    overall_band FLOAT,
    ta_score FLOAT, cc_score FLOAT,
    lr_score FLOAT, gra_score FLOAT,
    feedback_summary TEXT,  -- сжатый фидбек для RAG
    created_at TIMESTAMP
);

-- Semantic memory
CREATE TABLE user_profiles (
    user_id INTEGER PRIMARY KEY,
    current_level FLOAT,
    target_band FLOAT,
    recurring_errors JSONB,  -- {"GRA": "article errors", "LR": "repetition"}
    sessions_count INTEGER,
    last_session TIMESTAMP
);
```

---

## 3 Принципа, 2 Паттерна, 1 Антипаттерн

### 3 Принципа
1. **Память = архитектурное решение**, не промпт. Episodic/Semantic/Procedural — три разных хранилища с разной логикой доступа.
2. **Contextual chunks > raw chunks**. Всегда добавляй контекст к чанку перед embedding — это снижает retrieval failure на 49%.
3. **Hybrid search > pure semantic**. BM25 + embeddings вместе лучше каждого по отдельности.

### 2 Паттерна
1. **Compress-then-retrieve**: сначала суммаризируй старые сессии, потом делай retrieval по summary — экономит токены, сохраняет точность.
2. **Structured episodic store**: храни эпизоды как структурированные записи (scores + summary), не полный текст — дешевле и легче искать.

### 1 Антипаттерн
❌ **Dumping everything into context** — загружать всю историю пользователя в каждый запрос. Добавление большого количества нерелевантной информации может привести к галлюцинациям модели или эффекту "Lost in the Middle", когда критические детали забываются.

---

## Что дальше — День 2

Пишем `memory_pipeline.py`:
1. Mock PostgreSQL через SQLite (без деплоя)
2. Три функции: `full_context`, `compressed_context`, `retrieved_context`
3. Тест на 5 эссе разного уровня
4. Сравнение точности трёх режимов

---

*Неделя 3 из 12 | AI Product Engineer Journey*
