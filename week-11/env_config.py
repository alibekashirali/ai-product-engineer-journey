"""
env_config.py — environment management и validation.

Загружает .env, валидирует обязательные переменные,
предоставляет typed config объект.

Usage:
  from env_config import config
  client = anthropic.Anthropic(api_key=config.anthropic_api_key)
"""
import os
from dataclasses import dataclass
from typing import Optional


def _load_env_file(path: str = ".env"):
    """Простой .env parser без зависимостей."""
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key not in os.environ:  # не перезаписываем существующие
                os.environ[key] = val


@dataclass
class Config:
    # Required
    anthropic_api_key: str

    # Optional — fallback providers
    openai_api_key:    Optional[str] = None
    google_api_key:    Optional[str] = None

    # Pipeline settings
    quality_threshold:    float = 0.65
    auto_approve_score:   float = 0.85
    max_retries:          int   = 2
    max_tokens:           int   = 1500
    model_primary:        str   = "claude-sonnet-4-6"
    model_critic:         str   = "claude-sonnet-4-6"   # в prod: gpt-4o
    model_fallback:       str   = "claude-sonnet-4-6"   # в prod: gemini-1.5-flash

    # Cost settings
    daily_budget_usd:     float = 5.0

    # Notifications
    slack_webhook_url:    Optional[str] = None
    email_to:             Optional[str] = None
    email_from:           Optional[str] = None

    # Storage
    reports_dir:          str = "reports"
    db_path:              str = "pipeline.db"

    @property
    def has_fallback_providers(self) -> bool:
        return bool(self.openai_api_key or self.google_api_key)

    def validate(self) -> list[str]:
        """Возвращает список проблем конфигурации."""
        issues = []
        if not self.anthropic_api_key:
            issues.append("ANTHROPIC_API_KEY не установлен")
        if not self.anthropic_api_key.startswith("sk-ant-"):
            issues.append("ANTHROPIC_API_KEY выглядит некорректно (должен начинаться с sk-ant-)")
        if not self.has_fallback_providers:
            issues.append("⚠️  Нет fallback провайдеров (OPENAI_API_KEY или GOOGLE_API_KEY)")
        if self.quality_threshold < 0.5 or self.quality_threshold > 1.0:
            issues.append(f"QUALITY_THRESHOLD должен быть 0.5-1.0, текущий: {self.quality_threshold}")
        return issues

    def print_status(self):
        print(f"\n{'─'*50}")
        print(f"ENVIRONMENT CONFIG STATUS")
        print(f"{'─'*50}")
        print(f"  Anthropic:  {'✅ set' if self.anthropic_api_key else '❌ missing'}")
        print(f"  OpenAI:     {'✅ set' if self.openai_api_key else '⚠️  not set (fallback)'}")
        print(f"  Google:     {'✅ set' if self.google_api_key else '⚠️  not set (fallback)'}")
        print(f"  Slack:      {'✅ set' if self.slack_webhook_url else '⚠️  not set (mock)'}")
        print(f"  Model:      {self.model_primary}")
        print(f"  Threshold:  {self.quality_threshold}")
        print(f"  Budget/day: ${self.daily_budget_usd}")
        issues = self.validate()
        if issues:
            print(f"\n  Issues:")
            for issue in issues:
                print(f"    - {issue}")
        else:
            print(f"\n  ✅ Config valid")


def load_config(env_file: str = ".env") -> Config:
    """Загружает конфиг из env файла и переменных окружения."""
    _load_env_file(env_file)

    return Config(
        anthropic_api_key  = os.environ.get("ANTHROPIC_API_KEY", ""),
        openai_api_key     = os.environ.get("OPENAI_API_KEY"),
        google_api_key     = os.environ.get("GOOGLE_API_KEY"),
        quality_threshold  = float(os.environ.get("QUALITY_THRESHOLD", "0.65")),
        auto_approve_score = float(os.environ.get("AUTO_APPROVE_SCORE", "0.85")),
        max_retries        = int(os.environ.get("MAX_RETRIES", "2")),
        max_tokens         = int(os.environ.get("MAX_TOKENS", "1500")),
        model_primary      = os.environ.get("MODEL_PRIMARY", "claude-sonnet-4-6"),
        model_critic       = os.environ.get("MODEL_CRITIC",  "claude-sonnet-4-6"),
        model_fallback     = os.environ.get("MODEL_FALLBACK","claude-sonnet-4-6"),
        daily_budget_usd   = float(os.environ.get("DAILY_BUDGET_USD", "5.0")),
        slack_webhook_url  = os.environ.get("SLACK_WEBHOOK_URL"),
        email_to           = os.environ.get("EMAIL_TO"),
        email_from         = os.environ.get("EMAIL_FROM"),
        reports_dir        = os.environ.get("REPORTS_DIR", "reports"),
        db_path            = os.environ.get("DB_PATH", "pipeline.db"),
    )


def generate_env_template() -> str:
    """Генерирует шаблон .env файла."""
    return """# AI Market Intelligence Copilot — Environment Config
# Скопируй в .env и заполни значения

# ─── Required ───────────────────────────────
ANTHROPIC_API_KEY=sk-ant-...

# ─── Fallback Providers (рекомендуется) ─────
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...

# ─── Pipeline Settings ───────────────────────
QUALITY_THRESHOLD=0.65
AUTO_APPROVE_SCORE=0.85
MAX_RETRIES=2
MAX_TOKENS=1500
MODEL_PRIMARY=claude-sonnet-4-6
MODEL_CRITIC=claude-sonnet-4-6
MODEL_FALLBACK=claude-sonnet-4-6

# ─── Cost Control ────────────────────────────
DAILY_BUDGET_USD=5.0

# ─── Notifications (optional) ─────────────── 
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
EMAIL_TO=team@example.com
EMAIL_FROM=pipeline@yourdomain.com

# ─── Storage ─────────────────────────────────
REPORTS_DIR=reports
DB_PATH=pipeline.db
"""


# Глобальный config объект
config = load_config()

if __name__ == "__main__":
    config.print_status()
    print(f"\n{'─'*50}")
    print("ENV TEMPLATE (.env):")
    print(generate_env_template())
