# Benchmark Memory — Week 3
**User:** user_id=42 (3 прошлых сессии, прогресс Band 4.5 → 6.0)
**Test essay:** 158-189 слов (Technology: easier or more complicated?)
**Script:** memory_pipeline.py

---

## Токены — сравнение режимов

| Mode | Tokens | vs Full | Экономия |
|---|---|---|---|
| Full Context | 701 | 100% | — |
| Compressed Context | 524 | 75% | **-25%** |
| Retrieved Context | 470 | 67% | **-33%** |

---

## Quality Gate — accuracy по ключевым критериям

Quality Gate: accuracy в compressed/retrieved режиме ≤ 10% хуже full context.

### Overall Band

| Mode | Overall Band | Отклонение от Full |
|---|---|---|
| Full Context | **6.5** | baseline |
| Compressed Context | **6.0** | -0.5 (-8%) ⚠️ |
| Retrieved Context | **6.5** | 0 ✅ |

### Оценки по критериям

| Критерий | Full | Compressed | Retrieved |
|---|---|---|---|
| TA | 6.0 | 5.5 (-0.5) ⚠️ | 6.0 ✅ |
| CC | 6.5 | 6.0 (-0.5) ⚠️ | 6.5 ✅ |
| LR | 6.5 | 6.5 ✅ | **7.0** (+0.5) ↑ |
| GRA | 6.5 | 5.5 (-1.0) ❌ | 6.5 ✅ |

### Quality Gate — результат

| Mode | Пройден? | Комментарий |
|---|---|---|
| Full Context | ✅ baseline | — |
| Compressed Context | ⚠️ **Частично** | GRA упал на 1.0 (15%) — превышает порог |
| Retrieved Context | ✅ **Пройден** | Все отклонения ≤ 0 (точнее или равно) |

---

## Анализ качества фидбека

### Full Context — лучший по глубине
- Явно ссылается на прогресс между сессиями: *"directly addresses your Session 2 and 3 recurring error"*
- Знает историю детально: *"Article usage is now consistently accurate — this addresses your recurring error"*
- Exercise самый развёрнутый: relative clause + conditional + named example
- **Слабость:** самый дорогой, при 10+ сессиях начнётся context rot

### Compressed Context — слабейший
- GRA: галлюцинировал ошибку — *"the pressure to remain..."* сам исправил как ошибку, хотя это правильно
- Оценки занижены: TA 5.5 вместо 6.0, GRA 5.5 вместо 6.5
- Summary потерял детали о реальном прогрессе пользователя по артиклям
- Exercise хороший, но расхождение в оценках критично
- **Причина:** суммаризация сглаживает конкретные детали → модель теряет уверенность → занижает

### Retrieved Context — лучший баланс
- LR дал **7.0** (выше full!) — нашёл конкретную сессию с LR 5.0 и отметил прогресс
- Прямо цитирует прошлую ошибку: *"article errors from previous sessions (2026-05-04: 'plays crucial role') are no longer present"*
- Exercise самый конкретный: 3 конкретных шага для body paragraph
- Токенов на 33% меньше чем full
- **Причина:** hybrid search нашёл релевантные сессии с похожими ошибками → модель видит конкретный контраст

---

## Детальное сравнение Exercise

| Аспект | Full | Compressed | Retrieved |
|---|---|---|---|
| Конкретность задания | 5/5 | 4/5 | 5/5 |
| Follow-up запрошен? | ✅ | ✅ | ✅ |
| Связь с прошлыми ошибками | ✅ | ⚠️ Частично | ✅ |
| Объём (слова) | 65 слов | 52 слова | 71 слово |
| Структура (шаги) | 3 требования | 2 требования | 3 чётких шага |

**Победитель по Exercise:** Retrieved (3 конкретных пронумерованных шага + наименьший риск галлюцинации)

---

## Ключевые находки

### 1. Retrieved > Full по обнаружению прогресса
Hybrid search нашёл сессии с аналогичными ошибками (GRA article errors) → модель увидела конкретный контраст "было/стало" → дала LR 7.0 и явную похвалу. Full context тоже это видит, но через бо́льший шум из всей истории.

### 2. Compressed ломается на GRA
Суммаризация потеряла конкретику об article errors → модель в compressed режиме продолжает их "исправлять" даже там, где их нет (галлюцинация исправления). Это критический failure mode для педагогического агента.

### 3. Токены vs Качество
```
Full:       701 токенов → качество 10/10
Compressed: 524 токенов → качество 7/10  (GRA галлюцинация)
Retrieved:  470 токенов → качество 10/10 (LR даже лучше!)
```
**Вывод:** Retrieved — оптимальный режим. -33% токенов при том же или лучшем качестве.

### 4. Quality Gate
- Retrieved: ✅ пройден по всем критериям
- Compressed: ❌ не пройден (GRA -15%, превышает порог 10%)

---

## Рекомендация для GainScore Production

```python
# Логика выбора режима:

if len(history) == 0:
    mode = "no_memory"       # первая сессия
elif len(history) <= 2:
    mode = "full_context"    # мало данных, полный контекст дёшев
elif len(history) <= 10:
    mode = "retrieved"       # ✅ оптимально: качество = full, токены -33%
else:
    mode = "retrieved"       # при большой истории full невозможен
    # + background job: compress old sessions > 10 в semantic summary
```

---

## Что фиксить в prompts/pipeline (→ День 4 Недели 3)

1. **Compressed режим:** добавить в summary prompt явное требование сохранять конкретные recurring errors дословно, не перефразировать
2. **Retrieved режим:** добавить score tracking — сохранять какой режим использовался в каждой сессии для будущего анализа
3. **Word count:** скрипт считал 158/178/189 слов для одного эссе — нужна единая функция `count_words()` используемая везде

---

## Метрика недели

**Quality Gate из плана:** accuracy в compressed/retrieved режиме ≤ 10% хуже full context.

| Режим | Результат | Статус |
|---|---|---|
| Compressed | GRA -15% от full | ❌ Не пройден |
| Retrieved | Все критерии ≤ 0% хуже full | ✅ Пройден |

**Общий вывод:** Retrieved Context — production-ready режим для GainScore.
Compressed требует доработки summary prompt перед использованием.

---

*Week 3 of 12 | AI Product Engineer Journey*
