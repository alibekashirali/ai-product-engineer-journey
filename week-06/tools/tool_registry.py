"""
tool_registry.py — Tool Registry + Logging + Trace Export
Центральный регистр всех tools с автоматической трассировкой.
"""
import sys, os, json, time, uuid
from datetime import datetime
from typing import Any, Callable

# Ensure tools directory is in path regardless of where script is called from
_TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

from base import ToolResult
from word_count import word_count, SCHEMA as WC_SCHEMA
from verify_citation import verify_citation, SCHEMA as VC_SCHEMA
from calculator import calculator, SCHEMA as CALC_SCHEMA
from csv_query import csv_query, SCHEMA as CSV_SCHEMA
from summarizer import summarizer, SCHEMA as SUM_SCHEMA
from notifier import notifier, SCHEMA as NOT_SCHEMA

# ── Регистр ──────────────────────────────────────────
TOOL_FUNCTIONS: dict[str, Callable] = {
    "word_count":       word_count,
    "verify_citation":  verify_citation,
    "calculator":       calculator,
    "csv_query":        csv_query,
    "summarizer":       summarizer,
    "notifier":         notifier,
}

TOOL_SCHEMAS: list[dict] = [
    WC_SCHEMA, VC_SCHEMA, CALC_SCHEMA, CSV_SCHEMA, SUM_SCHEMA, NOT_SCHEMA
]

# Read vs Write classification
TOOL_TYPES: dict[str, str] = {
    "word_count":      "read",
    "verify_citation": "read",
    "calculator":      "read",
    "csv_query":       "read",
    "summarizer":      "read",
    "notifier":        "write",  # idempotency enforced
}


# ── Trace Storage ────────────────────────────────────
TRACES_DIR = os.path.join(os.path.dirname(__file__), "..", "traces")
os.makedirs(TRACES_DIR, exist_ok=True)

_current_trace: dict = {}


def start_trace(session_id: str = None) -> str:
    """Начинает новую трассировку. Возвращает trace_id."""
    global _current_trace
    trace_id = str(uuid.uuid4())[:8]
    _current_trace = {
        "trace_id": trace_id,
        "session_id": session_id or f"session_{trace_id}",
        "started_at": datetime.utcnow().isoformat(),
        "steps": [],
        "metrics": {
            "total_tool_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "total_retries": 0,
            "tool_selection_counts": {},
            "invalid_args_count": 0,
            "recovery_count": 0,
        }
    }
    return trace_id


def execute_tool(tool_name: str, args: dict, reason: str = "", retries: int = 2) -> ToolResult:
    """
    Выполняет tool с:
    - Валидацией существования
    - Retry для transient errors
    - Автоматической трассировкой
    """
    global _current_trace
    step_num = len(_current_trace.get("steps", [])) + 1
    started = time.time()
    attempt = 0
    result = None

    # Проверяем что tool существует
    if tool_name not in TOOL_FUNCTIONS:
        result = ToolResult(
            success=False,
            error="unknown_tool",
            message=f"Tool '{tool_name}' not found in registry",
            suggested_action=f"Use one of: {list(TOOL_FUNCTIONS.keys())}"
        )
        _log_step(step_num, tool_name, args, result, reason, 0, time.time()-started)
        return result

    fn = TOOL_FUNCTIONS[tool_name]

    # Retry loop
    while attempt <= retries:
        try:
            result = fn(**args)
            if result.success:
                break
            # Logic error — не ретраим, возвращаем LLM
            if result.error == "validation_error":
                _current_trace.get("metrics", {})["invalid_args_count"] = \
                    _current_trace.get("metrics", {}).get("invalid_args_count", 0) + 1
                break
            # Transient error — ретраим
            if attempt < retries:
                attempt += 1
                time.sleep(0.5 * (2 ** attempt))
                continue
            break
        except TypeError as e:
            # Неверные аргументы
            result = ToolResult(
                success=False,
                error="validation_error",
                message=f"Invalid arguments for {tool_name}: {e}",
                suggested_action=f"Check required parameters for {tool_name}",
                example_valid_call=TOOL_SCHEMAS[list(TOOL_FUNCTIONS.keys()).index(tool_name)].get("name", tool_name)
            )
            _current_trace.get("metrics", {})["invalid_args_count"] = \
                _current_trace.get("metrics", {}).get("invalid_args_count", 0) + 1
            break
        except Exception as e:
            if attempt < retries:
                attempt += 1
                time.sleep(0.5 * (2 ** attempt))
            else:
                result = ToolResult(
                    success=False,
                    error="api_failure",
                    message=str(e),
                    suggested_action="Retry the tool call"
                )
            continue

    latency = time.time() - started
    _log_step(step_num, tool_name, args, result, reason, attempt, latency)
    return result


def _log_step(step: int, tool: str, args: dict, result: ToolResult, reason: str, retries: int, latency: float):
    """Логирует шаг в текущую трассировку."""
    if not _current_trace:
        return

    m = _current_trace["metrics"]
    m["total_tool_calls"] += 1
    m["tool_selection_counts"][tool] = m["tool_selection_counts"].get(tool, 0) + 1
    m["total_retries"] += retries

    if result and result.success:
        m["successful_calls"] += 1
    else:
        m["failed_calls"] += 1

    _current_trace["steps"].append({
        "step": step,
        "tool": tool,
        "tool_type": TOOL_TYPES.get(tool, "unknown"),
        "reason": reason,
        "args": {k: str(v)[:100] for k, v in args.items()},  # truncate для читаемости
        "result": result.to_dict() if result else {},
        "status": "success" if (result and result.success) else "failed",
        "retries": retries,
        "latency_ms": round(latency * 1000, 1)
    })


def finish_trace() -> dict:
    """Завершает трассировку, сохраняет в файл, возвращает metrics."""
    global _current_trace
    if not _current_trace:
        return {}

    m = _current_trace["metrics"]
    total = m["total_tool_calls"]

    # Финальные метрики
    _current_trace["finished_at"] = datetime.utcnow().isoformat()
    _current_trace["summary"] = {
        "tool_selection_accuracy": round(m["successful_calls"] / total, 2) if total else 0,
        "invalid_args_rate":       round(m["invalid_args_count"] / total, 2) if total else 0,
        "success_rate":            round(m["successful_calls"] / total, 2) if total else 0,
        "total_latency_ms":        sum(s["latency_ms"] for s in _current_trace["steps"])
    }

    # Сохраняем trace
    trace_path = os.path.join(TRACES_DIR, f"{_current_trace['trace_id']}.json")
    with open(trace_path, "w") as f:
        json.dump(_current_trace, f, indent=2, default=str)

    trace = _current_trace.copy()
    _current_trace = {}
    return trace


def print_trace_summary(trace: dict):
    """Выводит читаемый summary трассировки."""
    print(f"\n{'='*50}")
    print(f"TRACE {trace['trace_id']} | {trace['session_id']}")
    print(f"{'='*50}")
    for step in trace.get("steps", []):
        status = "✅" if step["status"] == "success" else "❌"
        retry = f" (retry×{step['retries']})" if step["retries"] else ""
        print(f"  {step['step']}. {status} {step['tool']}{retry} — {step['latency_ms']}ms")
        if step["reason"]:
            print(f"     reason: {step['reason']}")
    s = trace.get("summary", {})
    print(f"\nMetrics:")
    print(f"  Tool selection accuracy: {s.get('tool_selection_accuracy', 0)*100:.0f}%")
    print(f"  Invalid args rate:       {s.get('invalid_args_rate', 0)*100:.0f}%")
    print(f"  Total latency:           {s.get('total_latency_ms', 0):.1f}ms")