# Production Readiness Checklist
**Project:** AI Market Intelligence Copilot  
**Week:** 11 of 12

---

## Top-10 Failure Modes + Mitigation Plan

### FM-01 — Multi-step Reasoning Drift
**Описание:** В длинных агентных цепочках агент теряет исходную цель.  
**Наш пример:** Week 7 — Analyst делал 3 retry с одинаковым плохим результатом.  
**Статус:** ⚠️ Частично решён

| Mitigation | Реализация | Статус |
|---|---|---|
| Max retries с явным счётчиком | `retry_count` в LangGraph state | ✅ Week 8 |
| Conditional routing по issue_type | `route_after_critic()` | ✅ Week 8 |
| При analyst_retries > 1 → researcher.refine() | — | ❌ TODO |

---

### FM-02 — Latent Inconsistency
**Описание:** Один промпт → разные ответы при повторе.  
**Наш пример:** Week 4 — band cap 4.0 vs 4.5 для одного эссе в разных run.  
**Статус:** ✅ Решён

| Mitigation | Реализация | Статус |
|---|---|---|
| Детерминированные правила в коде | `apply_band_cap()`, `calculator` tool | ✅ Week 4, 6 |
| temperature=0 для критических шагов | `temperature=0` в critic node | ✅ Week 8 |
| Eval harness на стабильность | `runner.py` 83/83 | ✅ Week 4 |

---

### FM-03 — Overconfident Hallucination
**Описание:** Модель уверена, но неверна. Fluent ≠ correct.  
**Наш пример:** Week 5 cal_018 — fabricated citation "yields returns across generations".  
**Статус:** ✅ Решён

| Mitigation | Реализация | Статус |
|---|---|---|
| verify_citation tool | `tools/verify_citation.py` | ✅ Week 6 |
| LLM groundedness judge | `judge_groundedness.py` | ✅ Week 5 |
| Citation check перед сохранением | В agent_with_tools.py flow | ✅ Week 6 |

---

### FM-04 — Context-Boundary Degradation
**Описание:** При длинном контексте модель теряет начало.  
**Наш пример:** Week 3 — context rot при полной истории >20k токенов.  
**Статус:** ✅ Решён

| Mitigation | Реализация | Статус |
|---|---|---|
| Retrieved context mode | `retrieved_context()` -33% токенов | ✅ Week 3 |
| Compaction для длинной истории | `summarizer` tool | ✅ Week 6 |
| max_tokens=1500 (не 1000) | Увеличено после cal_017 failure | ✅ Week 5 |

---

### FM-05 — Incorrect Tool Invocation
**Описание:** Агент вызывает не тот tool или с неверными аргументами.  
**Наш пример:** Week 6 — calculator получал string вместо float.  
**Статус:** ✅ Решён

| Mitigation | Реализация | Статус |
|---|---|---|
| ToolResult с validation_error | `base.py` ToolResult | ✅ Week 6 |
| suggested_action в ошибке | LLM self-correction | ✅ Week 6 |
| invalid_args_rate метрика | `tool_registry.py` traces | ✅ Week 6 |

---

### FM-06 — Partial Success Masking
**Описание:** Tool выполнен частично, агент считает что полностью.  
**Наш пример:** Week 3 — truncated response в cal_017, Exercise обрезан.  
**Статус:** ⚠️ Частично решён

| Mitigation | Реализация | Статус |
|---|---|---|
| max_tokens=1500 | Увеличено | ✅ Week 5 |
| Truncation detection в judge | `judge_usefulness` — TRUNCATED flag | ⚠️ Задокументировано |
| Response length validation | — | ❌ TODO |

---

### FM-07 — Schema Drift
**Описание:** Модель возвращает правильный формат но не те поля.  
**Наш пример:** Week 7 — все агенты переписаны с JSON на text format из-за JSONDecodeError.  
**Статус:** ✅ Решён

| Mitigation | Реализация | Статус |
|---|---|---|
| Текстовый формат вместо JSON | `KEY: value` format во всех агентах | ✅ Week 7 |
| Robust parser с fallback | `_parse_text()` + sentence extractor | ✅ Week 7 |
| Pydantic validation для tools | ToolResult dataclass | ✅ Week 6 |

---

### FM-08 — Version Drift
**Описание:** После обновления модели поведение изменилось без предупреждения.  
**Наш пример:** `claude-sonnet-4-20250514` → deprecated warning.  
**Статус:** ⚠️ Требует внимания

| Mitigation | Реализация | Статус |
|---|---|---|
| MODEL константа в одном месте | `MODEL = "claude-sonnet-4-6"` | ✅ |
| Eval regression на каждый деплой | `pytest runner.py` | ✅ Week 4 |
| Model version pinning | В requirements.txt | ❌ TODO |
| Deprecation alerts мониторинг | — | ❌ TODO |

---

### FM-09 — Cost-Driven Performance Collapse
**Описание:** При высокой нагрузке урезание контекста → деградация качества.  
**Наш пример:** max_tokens=1000 → truncation в Week 7 → fabricated citations.  
**Статус:** ⚠️ Мониторинг нужен

| Mitigation | Реализация | Статус |
|---|---|---|
| Cost tracking per run | `cost_tracker.py` | ✅ Week 11 |
| Budget alert при превышении | `cost_tracker.py` | ✅ Week 11 |
| Context caching для повторных промптов | — | ❌ TODO |
| Fallback на cheaper model при overload | `fallback_strategy.py` | ✅ Week 11 |

---

### FM-10 — Silent Quality Degradation
**Описание:** Метрики зелёные, но контент плохой.  
**Наш пример:** Week 10 — demo brief score=0.82, но содержание шаблонное.  
**Статус:** ⚠️ Частично решён

| Mitigation | Реализация | Статус |
|---|---|---|
| LLM judges (groundedness, usefulness) | `judge_*.py` | ✅ Week 5 |
| Human review queue при score < 0.85 | `human_review_queue.py` | ✅ Week 11 |
| Groundedness check на demo briefs | — | ❌ TODO |

---

## Privacy Checklist

| Item | Status | Notes |
|---|---|---|
| PII не логируется в traces | ✅ | args truncated до 100 chars |
| API ключи только в `.env` | ✅ | `env_config.py` validation |
| Run history не содержит полный текст эссе | ✅ | CSV только метрики |
| Dead letter queue — retention policy | ❌ | 30 дней → auto-delete TODO |
| User data isolation | ❌ | Нет multi-tenancy пока |

---

## Cost Notes

| Сценарий | Runs/week | Cost/run | Weekly | Monthly |
|---|---|---|---|---|
| Current (dev) | 5-10 | ~$0.03 | ~$0.25 | ~$1 |
| Small prod (100 users) | 100 | ~$0.03 | ~$3 | ~$12 |
| Scale (1k users) | 1000 | ~$0.03 | ~$30 | ~$120 |
| Scale + caching | 1000 | ~$0.01 | ~$10 | ~$40 |

**Главный lever:** context caching снижает стоимость повторяющихся system prompts на 50-90%.

---

## Fallback Chain

```
Primary:   Claude Sonnet 4.6     (default, лучшее качество)
Critic:    GPT-4o                (независимая архитектура для judge)
Fallback:  Gemini 1.5 Flash      (дешевле, для некритичных шагов)
Last:      Demo cache            (при полном outage)
Human:     Review queue          (при score < 0.65)
```

---

## Rollback Plan

1. `git revert` последнего коммита с изменением промпта
2. `pytest runner.py` — убедиться что regression устранён
3. Редеплой через Railway/Railway CLI
4. Мониторинг ops_dashboard.py первые 30 минут

---

## Summary

| Failure Mode | Статус |
|---|---|
| FM-01 Multi-step drift | ⚠️ Частично |
| FM-02 Latent inconsistency | ✅ Решён |
| FM-03 Hallucination | ✅ Решён |
| FM-04 Context degradation | ✅ Решён |
| FM-05 Tool invocation | ✅ Решён |
| FM-06 Partial success | ⚠️ Частично |
| FM-07 Schema drift | ✅ Решён |
| FM-08 Version drift | ⚠️ Мониторинг |
| FM-09 Cost collapse | ⚠️ Мониторинг |
| FM-10 Silent degradation | ⚠️ Частично |

**Итого: 5/10 полностью решены, 5/10 — мониторинг или TODO.**

---

*Week 11 of 12 | AI Product Engineer Journey*
