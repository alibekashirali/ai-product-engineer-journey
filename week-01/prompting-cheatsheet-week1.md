# Prompting Cheat Sheet — Week 1
> Выжимка из официальных гайдов: Claude, GPT-5, Gemini

[Claude prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)
[GPT-5 prompting guide](https://developers.openai.com/cookbook/examples/gpt-5/gpt-5_prompting_guide)
[Gemini prompt design strategies](https://ai.google.dev/gemini-api/docs/prompting-strategies) 

---

## Универсальные принципы (работают везде)

### 1. Будь конкретным и явным
Модель — это умный новый сотрудник без контекста о твоих нормах. Чем точнее объяснишь — тем лучше результат.

**Плохо:** "Напиши что-нибудь про маркетинг"  
**Хорошо:** "Напиши 3 заголовка для email-кампании об AI-продукте, целевая аудитория — B2B SaaS founders, стиль — прямой, без buzzwords"

> 💡 **Тест:** покажи промпт коллеге без контекста. Если он запутается — Claude тоже запутается.

---

### 2. Примеры (few-shot prompting)
Один из самых надёжных способов управлять форматом и тоном.

```
Правила:
- 3–5 примеров — оптимально
- Оборачивай в <example> теги (Claude)
- Формат всех примеров должен быть одинаковым (Gemini: особенно важно)
- Разнообразие примеров > монотонность (чтобы не было overfitting)
```

**Когда примеры не нужны:** если задача очевидна и результат стабилен без них.

---

### 3. Добавляй контекст (мотивацию)
Объясни _почему_ важна инструкция — модель умеет обобщать из объяснений.

**Пример для Claude:**
```
Не используй маркдаун в ответах. Это API-интеграция, и символы форматирования 
появятся как артефакты в UI конечного пользователя.
```

---

### 4. Управляй форматом явно
Говори что делать, а не что не делать:

| Плохо | Хорошо |
|-------|--------|
| "Не используй markdown" | "Пиши сплошным текстом, без заголовков и списков" |
| "Будь краткий" | "Ответ — максимум 3 предложения" |

---

### 5. Роль / система
Задай роль в system prompt — это фокусирует поведение и тон:

```python
system="You are a senior product manager specializing in B2B SaaS."
```

---

## Claude — специфика

### XML-теги для структурирования
Claude особенно хорошо понимает XML-разметку промптов:

```xml
<instructions>
  Проанализируй текст и выдели 3 ключевых инсайта.
</instructions>

<context>
  Аудитория: технические founders на ранней стадии.
</context>

<input>
  {{текст пользователя}}
</input>
```

Используй теги: `<instructions>`, `<context>`, `<input>`, `<examples>`, `<output_schema>`

---

### Long context (20k+ токенов)
- **Данные — в начале промпта**, вопрос и инструкции — в конце (улучшает качество до 30%)
- Несколько документов — оборачивай в `<document index="n">` теги
- Попроси модель сначала процитировать релевантные части, потом отвечать

---

### Thinking / Adaptive Thinking (Claude Opus)
- `effort: "high"` или `"xhigh"` — для сложных, многошаговых задач
- `effort: "low"` — для быстрых, latency-sensitive задач
- Можно подсказать когда думать: `"Thinking adds latency. Use it only for multi-step reasoning tasks."`

---

### Параллельные tool calls
```
Если несколько tool calls независимы друг от друга — вызывай их одновременно, 
не последовательно. Это ускоряет выполнение.
```

---

### Антипаттерны Claude
- ❌ Агрессивные инструкции типа "КРИТИЧНО: ОБЯЗАТЕЛЬНО используй этот инструмент" → переспросит
- ❌ Слишком сложные промпты без XML-структуры → теряет контекст
- ❌ Prefilled responses (устарело с Claude 4.6+)

---

## GPT-5 — специфика

### reasoning_effort — главный рычаг
| Уровень | Когда использовать |
|---------|-------------------|
| `low` | Быстрые задачи, latency-sensitive |
| `medium` | Большинство задач |
| `high` | Сложный анализ, агентные задачи |
| `max` | Самые сложные задачи |

---

### verbosity — отдельный параметр для длины ответа
GPT-5 первая модель с отдельным API-параметром `verbosity`. Можно задать глобально низкий, а в конкретном месте промпта — высокий:

```
Write code for clarity first. Use high verbosity for writing code and code tools.
```
*(Cursor использует именно эту связку: verbosity=low глобально, high для code tools)*

---

### Agentic persistence prompt
Для длинных автономных задач добавляй:

```
You are an agent. Keep going until the user's query is completely resolved 
before ending your turn. Only terminate when the problem is solved.
Never stop at uncertainty — research the most reasonable approach and continue.
```

---

### Tool preambles (прогресс-апдейты)
GPT-5 умеет давать чёткие промежуточные обновления:

```
Always begin by rephrasing the user's goal clearly.
Outline a structured plan before calling tools.
Narrate each step succinctly as you execute.
Finish by summarizing completed work.
```

---

### Metaprompting (GPT-5 о GPT-5)
GPT-5 умеет улучшать собственные промпты:

```
When asked to optimize prompts, explain what phrases could be added or deleted 
to more consistently elicit the desired behavior.

Here's a prompt: [PROMPT]
The desired behavior is: [DO X], but instead it [DOES Y].
What minimal edits would encourage it to address these shortcomings?
```

---

### Антипаттерны GPT-5
- ❌ Противоречащие инструкции — GPT-5 тратит reasoning tokens на их reconciliation
- ❌ Агрессивные "ALWAYS DO X" для действий, которые модель и так делает
- ❌ Размытые инструкции (ambiguous) — GPT-5 следует буквально, включая неточности

---

## Gemini — специфика

### Zero-shot vs Few-shot
Gemini рекомендует **всегда включать примеры**. Промпты без few-shot примеров значительно слабее.

- Минимум 1–2 примера
- Слишком много примеров → overfitting
- Единый формат во всех примерах (одинаковые теги, пробелы, переносы)

---

### Completion strategy (продолжение паттерна)
Вместо того чтобы описывать формат словами — начни сам:

```
Create an outline for an essay about hummingbirds.
I. Introduction
   *
```
Gemini продолжит по заданному паттерну.

---

### Constraints (ограничения)
Задавай явные ограничения в промпте:

```
Summarize this text in one sentence:
Text: [текст]
```

```
Respond with only the text provided. Do not add your own interpretation.
```

---

### Параметры модели
| Параметр | Что делает |
|----------|-----------|
| `temperature` | Случайность (0 = детерминировано). Для Gemini 3 — оставляй 1.0 |
| `topK` | Сколько токенов рассматривается на каждом шаге |
| `topP` | Порог вероятности (обычно 0.95) |
| `stop_sequences` | Где остановить генерацию |
| `max_output_tokens` | Максимальная длина ответа |

---

### Разбивай сложные промпты
1. **Один промпт — одна инструкция** (не перегружай)
2. **Chain prompts:** output одного → input следующего
3. **Aggregate:** параллельные задачи → финальная агрегация

---

### Антипаттерны Gemini
- ❌ Нет примеров → нестабильный формат
- ❌ Менять `temperature` у Gemini 3 (вызывает looping и деградацию)
- ❌ Инструкции на естественном языке вместо structured output для сложных JSON-схем

---

## Сравнительная таблица

| Аспект | Claude | GPT-5 | Gemini |
|--------|--------|-------|--------|
| Структура промпта | XML-теги (`<instructions>`) | Секции с заголовками / XML | Явные constraints + примеры |
| Управление глубиной | `effort` параметр | `reasoning_effort` | `temperature`, `topK/P` |
| Управление длиной | Инструкция в промпте | `verbosity` API параметр | `max_output_tokens` + инструкция |
| Примеры (few-shot) | Рекомендованы | Важны при `minimal` reasoning | Критически важны |
| Агентность | Adaptive thinking + subagents | Persistence prompts + Responses API | Chain prompts |
| Лучшее для | Сложный контекст, длинные документы, агенты | Кодинг, frontend, agentic workflows | Мультимодальность, structured output |

---

## Context Pack Template (Неделя 1 → Неделя 2)

Используй этот шаблон для каждого нового промпта:

```markdown
## Goal
Что должна сделать модель — одно предложение.

## User Profile
Кто пользователь, какой уровень, что ему важно.

## Task
Конкретный запрос с деталями.

## Constraints
- Формат вывода
- Длина
- Что нельзя делать

## Context / Data
[Вставить данные или документы]

## Examples
<example>
Input: ...
Output: ...
</example>

## Output Schema
```json
{ "field": "type" }
```

## Eval Criteria
- Что считается хорошим ответом?
- По каким критериям проверять?
```

---

*Неделя 1 из 12 | AI Product Engineer Journey*
