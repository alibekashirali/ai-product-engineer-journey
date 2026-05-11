# Theory Notes — Week 11
**Тема:** Productization and Reliability
**Источники:** Microsoft Research (taxonomy 15 failure modes), ZenML (1200 deployments), Medium (Dec 2025), Galileo AI, arxiv "Fail Fast or Ask"

---

## Главный сдвиг в мышлении

| Demo (Weeks 1-10) | Production (Week 11) |
|---|---|
| Работает на твоих данных | Работает на любых данных |
| Ломается громко (Exception) | Ломается тихо (fluent but wrong) |
| Один пользователь | Множество одновременных |
| API ключ в `.env` | Secrets management + rotation |
| Один провайдер | Fallback на несколько моделей |
| Ты знаешь когда сломалось | Алерт приходит раньше тебя |

> **Ключевой тезис из 1200 production deployments:** традиционный software ломается громко. LLM системы ломаются убедительно — ответ может быть плавным, грамматически правильным и при этом полностью неверным.

---

## 3 Принципа

### Принцип 1 — Infrastructure over prompts для надёжности

Самые надёжные guardrails реализованы в коде, а не в промптах. Архитектурные подходы — session tainting, dual-layer permissions, API-based authorization — дают гарантии, которые prompt engineering не может обеспечить.

```
Промпт говорит: "Не пиши эссе за студента"
→ Модель иногда нарушает при unusual inputs

Код проверяет: if "Here is your essay:" in response → block
→ Всегда работает, независимо от промпта
```

Мы уже это знаем из Week 4: `apply_band_cap()` в коде надёжнее band cap в промпте.

### Принцип 2 — Graceful Degradation вместо hard failure

Circuit breakers, human handoffs и confidence thresholds — признание того, что идеальная надёжность невозможна.

```
Tier 1: Основная модель (Claude Sonnet)
Tier 2: Fallback модель (GPT-4o) при timeout/error
Tier 3: Simplified prompt + основная модель при Tier 2 fail
Tier 4: Cached/demo response
Tier 5: Human review queue
```

Никогда не показывать пустой экран. Всегда давать что-то полезное.

### Принцип 3 — "Fail Fast, or Ask" для высокорисковых решений

Система, которая ставит медленную reasoning модель за быстрой non-reasoning моделью, сохраняет точность 90%+ при скорости на 40% быстрее. Дефер сложных запросов к human expert даёт +2% точности.

```python
def route_request(query: str, confidence: float) -> str:
    if confidence >= 0.85:
        return "auto_approve"      # быстрый путь
    elif confidence >= 0.65:
        return "reasoning_model"   # медленный, но точный
    else:
        return "human_review"      # не рисковать
```

---

## 15 Failure Modes — Taxonomy (Microsoft Research)

Из системного анализа реальных LLM приложений выделены 15 hidden failure modes:

### Группа 1 — Reasoning Failures (модель думает неправильно)

| # | Failure Mode | Описание | Наш пример |
|---|---|---|---|
| 1 | **Multi-step reasoning drift** | В длинных цепочках агент теряет исходную цель | Week 7: analyst делал 3 retry, не улучшая результат |
| 2 | **Latent inconsistency** | Один и тот же промпт → разные ответы при повторе | Week 4: band cap 4.0 vs 4.5 для одного эссе |
| 3 | **Overconfident hallucination** | Модель уверена, но неверна. Fluent ≠ correct | Cal_018: fabricated citation "yields returns..." |

### Группа 2 — Integration Failures (система ломается)

| # | Failure Mode | Описание | Наш пример |
|---|---|---|---|
| 4 | **Context-boundary degradation** | При длинном контексте модель "теряет" начало | Week 3: context rot при >20k токенов |
| 5 | **Incorrect tool invocation** | Агент вызывает не тот tool или с неверными args | Week 6: calculator получил string вместо float |
| 6 | **Partial success masking** | Tool выполнен на 3/5 шагах, агент считает что полностью | Week 3: truncated response в cal_017 |
| 7 | **Schema drift** | Модель возвращает правильный формат, но не те поля | Week 7: Researcher возвращал text вместо JSON |

### Группа 3 — Operational Failures (в production)

| # | Failure Mode | Описание | Наш пример |
|---|---|---|---|
| 8 | **Version drift** | После обновления модели поведение изменилось | claude-sonnet-4-20250514 → deprecated |
| 9 | **Cost-driven performance collapse** | При высокой нагрузке → урезание контекста → деградация | max_tokens=1000 → truncation в Week 7 |
| 10 | **Silent quality degradation** | Метрики зелёные, контент плохой | Demo brief score=0.82 но содержание шаблонное |

### Группа 4 — Trust Failures (пользователь доверяет неправильно)

| # | Failure Mode | Описание | Наш пример |
|---|---|---|---|
| 11 | **Sycophantic compliance** | Модель соглашается с неверным утверждением пользователя | E006: меняет band score по просьбе |
| 12 | **Authority impersonation** | Модель принимает "системные" инструкции из user input | Prompt injection через essay текст |
| 13 | **Cascading agent errors** | Ошибка одного агента накапливается через цепочку | Week 7: плохой researcher → плохой analyst → плохой brief |
| 14 | **Non-idempotent side effects** | Write tool вызван дважды → дублирование | Week 6: notifier без idempotency key |
| 15 | **Update-induced regression** | Промпт работал с model v1, сломался с model v2 | Context Pack v1 → v4: каждая версия фиксила regression |

---

## 2 Паттерна

### Паттерн 1 — Multi-Model Fallback Strategy

```
PRIMARY:   Claude Sonnet 4.6   (качество, скорость, наш default)
CRITIC:    GPT-4o              (независимая проверка — другая архитектура)
FALLBACK:  Gemini 1.5 Pro      (long-context задачи, альтернатива при outage)
LAST:      Demo/Cached         (при полном outage всех провайдеров)
```

Почему разные провайдеры для primary и critic:
- Self-Enhancement Bias (Week 5): Claude-as-judge Claude предпочитает Claude outputs
- Anthropic outage не ломает всю систему
- Разные training data → разные blind spots

```python
def call_with_fallback(prompt: str, models: list) -> str:
    for model in models:
        try:
            return call_model(model, prompt, timeout=30)
        except (TimeoutError, RateLimitError, APIError) as e:
            log_failure(model, e)
            continue
    return get_cached_response(prompt)  # последний resort
```

### Паттерн 2 — Human Review Queue

Не все решения должны принимать автоматически. Human-in-the-loop улучшает точность на 2%+ на сложных задачах.

```python
AUTO_APPROVE_THRESHOLD  = 0.85  # автоматически
HUMAN_REVIEW_THRESHOLD  = 0.65  # в очередь на проверку
AUTO_REJECT_THRESHOLD   = 0.40  # автоматически отклонить

def route_result(result: RunResult) -> str:
    if result.score >= AUTO_APPROVE_THRESHOLD:
        return "auto_approve"
    elif result.score >= HUMAN_REVIEW_THRESHOLD:
        human_review_queue.add(result)
        return "pending_review"
    else:
        dead_letter_queue.add(result)
        return "auto_reject"
```

---

## 1 Антипаттерн

### ❌ Single point of failure — один провайдер без fallback

```
Anthropic outage → весь pipeline стоит → пользователи видят 500
```

Решение — circuit breaker + multi-provider:
```python
class CircuitBreaker:
    def __init__(self, threshold=5, timeout=60):
        self.failures = 0
        self.threshold = threshold
        self.state = "closed"  # closed, open, half-open

    def call(self, fn, *args):
        if self.state == "open":
            raise CircuitOpenError("Circuit breaker open — using fallback")
        try:
            result = fn(*args)
            self.reset()
            return result
        except Exception as e:
            self.failures += 1
            if self.failures >= self.threshold:
                self.state = "open"
            raise
```

---

## Production Readiness Checklist (наш Top-10)

Перед деплоем ответить "да" на каждый пункт:

```
□ 1. Fallback chain: ≥2 провайдера + demo cache
□ 2. Failure taxonomy: все 15 failure modes задокументированы
□ 3. Human review queue: автоматический роутинг по score
□ 4. Cost tracking: токены и бюджет на каждый run
□ 5. Dead letter queue: failed runs не теряются
□ 6. Alerts: Slack/email при score < threshold или Exception
□ 7. Secrets: API ключи в env, не в коде
□ 8. Privacy: PII не логируется, retention policy есть
□ 9. Eval regression: pytest runner на каждый деплой
□ 10. Rollback plan: как вернуться к предыдущей версии
```

---

## Cost Notes для нашего pipeline

| Компонент | Tokens/run | Cost @ Claude Sonnet rates |
|---|---|---|
| Planner | ~800 | ~$0.003 |
| Researcher ×3 | ~3000 | ~$0.009 |
| Analyst | ~2800 | ~$0.008 |
| Critic | ~1000 | ~$0.003 |
| Writer | ~2500 | ~$0.008 |
| **Total** | **~10100** | **~$0.03/run** |

При 100 runs/неделя: ~$3/неделю, ~$12/месяц. Дёшево сейчас, но при 10k users:
- 10k × $0.03 = $300/день = $9k/месяц
- Context caching (Anthropic) снижает до 50-90% на повторяющихся промптах
- Fallback на Gemini 1.5 Flash для некритичных шагов: -70% cost

---

## Применение к GainScore

```
Failure Mode 2 (latent inconsistency):
  Band score нестабилен → apply_band_cap() в коде ✅ (решено Week 4)

Failure Mode 3 (overconfident hallucination):
  Fabricated citations → verify_citation() tool ✅ (решено Week 6)

Failure Mode 10 (silent quality degradation):
  Demo brief score=0.82 но шаблонный → judge_groundedness ✅ (Week 5)

Failure Mode 13 (cascading errors):
  Плохой researcher → плохой analyst → conditional routing ✅ (Week 8)

Failure Mode 14 (non-idempotent):
  Notifier дублирует → idempotency_key ✅ (Week 6)
```

5 из 15 failure modes уже решены в предыдущих неделях. Это portfolio сильная сторона.

---

## Что строим в Days 2-3

```
production_checklist.md  ← top-10 failure modes + mitigation
fallback_strategy.py     ← multi-model с circuit breaker
failure_taxonomy.py      ← классификация и роутинг
human_review_queue.py    ← SQLite очередь + CLI review
cost_tracker.py          ← учёт токенов per run
env_config.py            ← .env management + validation
```

---

*Неделя 11 из 12 | AI Product Engineer Journey | GainScore*
