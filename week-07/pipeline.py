"""
pipeline.py — Запуск multi-agent pipeline одной командой.
Сохраняет brief + полный лог шагов.

Usage:
  python3 pipeline.py
  python3 pipeline.py "Research AI writing tools market"
"""
import json, sys, os, re
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "agents"))
from orchestrator import Orchestrator

OUTPUTS_DIR = os.path.join(os.path.dirname(__file__), "outputs")
os.makedirs(OUTPUTS_DIR, exist_ok=True)

DEFAULT_TOPIC = "Research the SaaS project management market: key players, trends, pricing models, and growth opportunities for a new entrant"


def run_pipeline(topic: str = DEFAULT_TOPIC) -> dict:
    orchestrator = Orchestrator()
    result = orchestrator.run(topic)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_topic = re.sub(r'[^a-zA-Z0-9]', '_', topic[:30]).lower()

    # Сохраняем brief (markdown)
    brief_path = os.path.join(OUTPUTS_DIR, f"brief_{safe_topic}_{timestamp}.md")
    with open(brief_path, "w") as f:
        f.write(f"# Research Brief\n**Topic:** {topic}\n**Date:** {timestamp}\n\n")
        f.write(result["brief"])
    print(f"\n📄 Brief saved: {brief_path}")

    # Сохраняем полный лог
    log_path = os.path.join(OUTPUTS_DIR, f"log_{safe_topic}_{timestamp}.json")
    log_data = {
        "topic": topic,
        "metadata": result["metadata"],
        "run_log": result["run_log"],
        "steps": result["steps"],
        "critique": result["critique"],
    }
    with open(log_path, "w") as f:
        json.dump(log_data, f, indent=2, ensure_ascii=False)
    print(f"📋 Log saved: {log_path}")

    # Печатаем summary
    m = result["metadata"]
    print(f"\n{'='*55}")
    print(f"PIPELINE SUMMARY")
    print(f"{'='*55}")
    print(f"Quality Gate:  {m['quality_gate']} (score={m['final_score']})")
    print(f"Total steps:   {m['total_steps']}")
    print(f"Retries:       {m['retries']}")
    print(f"Elapsed:       {m['elapsed_seconds']:.1f}s")
    print(f"\nBRIEF PREVIEW:")
    print("─"*55)
    print(result["brief"][:600] + "...")

    return result


if __name__ == "__main__":
    topic = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else DEFAULT_TOPIC
    run_pipeline(topic)
