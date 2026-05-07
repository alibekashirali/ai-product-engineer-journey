"""
crewai_pipeline.py — Week 8
Research pipeline на настоящем CrewAI 1.14.4.

Архитектура: 5 агентов с ролями → sequential Process → один kickoff().
Ключевое отличие от LangGraph: нет conditional routing — 
CrewAI передаёт контекст через output предыдущих Tasks.
"""

import json
import os
import re
import sys
import time
from datetime import datetime

from crewai import Agent, Task, Crew, Process
from crewai.llm import LLM


# ─────────────────────────────────────────────
# LLM — Claude через crewai LLM wrapper
# ─────────────────────────────────────────────
llm = LLM(model="anthropic/claude-sonnet-4-6", temperature=0.3)


# ─────────────────────────────────────────────
# AGENTS — каждый с ролью, целью, backstory
# ─────────────────────────────────────────────

planner = Agent(
    role="Research Planning Specialist",
    goal="Break down research topics into 3 specific, actionable subtasks",
    backstory=(
        "You are an expert at structuring complex research into focused components. "
        "You always produce exactly 3 numbered subtasks with clear research questions "
        "and specific focus areas."
    ),
    llm=llm,
    verbose=True
)

researcher = Agent(
    role="Market Research Analyst",
    goal="Gather specific, data-driven market intelligence with named companies and numbers",
    backstory=(
        "You are a specialist in competitive intelligence with deep knowledge of SaaS markets. "
        "You always name specific companies, cite approximate revenue or user numbers, "
        "and identify concrete trends backed by examples."
    ),
    llm=llm,
    verbose=True
)

analyst = Agent(
    role="Business Intelligence Analyst",
    goal="Transform raw research into structured strategic analysis",
    backstory=(
        "You are an expert at synthesizing market data into clear sections. "
        "You produce structured output covering: competitive landscape, pricing models, "
        "growth trends, opportunities and risks — always with specific evidence."
    ),
    llm=llm,
    verbose=True
)

critic = Agent(
    role="Quality Assurance Specialist",
    goal="Verify research quality and give clear PASS/FAIL verdict",
    backstory=(
        "You are a senior research editor who checks for specificity, evidence quality, "
        "and actionability. You give honest PASS if score >= 0.65, FAIL otherwise, "
        "with concrete improvement feedback."
    ),
    llm=llm,
    verbose=True
)

writer = Agent(
    role="Business Report Writer",
    goal="Produce a professional 400-500 word markdown market research brief",
    backstory=(
        "You are an expert business writer who transforms analysis into clear, "
        "decision-ready reports. You write in professional markdown with sections: "
        "Executive Summary, Competitive Landscape, Pricing, Trends, Opportunities, "
        "Risks, Next Steps."
    ),
    llm=llm,
    verbose=True
)


# ─────────────────────────────────────────────
# TASKS
# ─────────────────────────────────────────────

def build_tasks(topic: str) -> list[Task]:

    plan_task = Task(
        description=(
            f"Create a research plan for this topic: {topic}\n\n"
            "Break it into exactly 3 specific subtasks. For each subtask provide:\n"
            "- A specific research question\n"
            "- A clear focus area (what data to look for)\n\n"
            "Format:\n"
            "SUBTASK 1: [question]\nFOCUS 1: [what to research]\n"
            "SUBTASK 2: [question]\nFOCUS 2: [what to research]\n"
            "SUBTASK 3: [question]\nFOCUS 3: [what to research]"
        ),
        expected_output="3 numbered research subtasks with specific questions and focus areas",
        agent=planner
    )

    research_task = Task(
        description=(
            f"Execute market research for: {topic}\n\n"
            "For each subtask from the plan, provide 4-5 specific findings:\n"
            "- Name specific companies, products, or technologies\n"
            "- Include approximate numbers (users, revenue, pricing, market size)\n"
            "- Give concrete examples\n\n"
            "Format per subtask:\n"
            "SUBTASK [N]: [name]\n"
            "FINDING 1: [finding] — DETAIL: [supporting data]\n"
            "FINDING 2: [finding] — DETAIL: [supporting data]\n"
            "..."
        ),
        expected_output="Structured findings for each subtask with named companies and specific data points",
        agent=researcher,
        context=[plan_task]
    )

    analyze_task = Task(
        description=(
            f"Analyze all research findings for: {topic}\n\n"
            "Synthesize into structured analysis:\n"
            "EXECUTIVE SUMMARY: [2-3 sentence market overview]\n"
            "COMPETITIVE LANDSCAPE: [key players and positioning]\n"
            "PRICING MODELS: [pricing patterns and benchmarks]\n"
            "MARKET TRENDS: [3 key trends]\n"
            "OPPORTUNITIES: [2-3 specific opportunities]\n"
            "RISKS: [2 key risks]\n"
            "CONFIDENCE: [0.0-1.0]\n\n"
            "Be specific — name companies, cite numbers."
        ),
        expected_output="Structured analysis with executive summary, competitive landscape, "
                        "pricing, trends, opportunities, risks, and confidence score",
        agent=analyst,
        context=[research_task]
    )

    critique_task = Task(
        description=(
            f"Evaluate the quality of the market analysis for: {topic}\n\n"
            "Check these criteria (each 0.0-1.0):\n"
            "- Specificity: named companies, concrete numbers?\n"
            "- Evidence: claims backed by data?\n"
            "- Actionability: insights lead to clear actions?\n"
            "- Completeness: topic covered comprehensively?\n\n"
            "PASS if all criteria >= 0.6, FAIL otherwise.\n\n"
            "Format:\n"
            "VERDICT: PASS or FAIL\n"
            "SCORE: [0.0-1.0]\n"
            "SPECIFICITY: [score]\n"
            "EVIDENCE: [score]\n"
            "ACTIONABILITY: [score]\n"
            "COMPLETENESS: [score]\n"
            "FEEDBACK: [specific actionable feedback]"
        ),
        expected_output="VERDICT, SCORE, criteria scores, and specific FEEDBACK",
        agent=critic,
        context=[analyze_task]
    )

    write_task = Task(
        description=(
            f"Write a professional market research brief in markdown for: {topic}\n\n"
            "Use all previous research, analysis, and quality feedback.\n\n"
            "Required sections:\n"
            "## Executive Summary (3-4 sentences)\n"
            "## Competitive Landscape\n"
            "## Pricing Models\n"
            "## Market Trends\n"
            "## Opportunities\n"
            "## Risks\n"
            "## Next Steps (3 concrete actions)\n\n"
            "Target: 400-500 words. Professional tone. Use **bold** for key terms and numbers."
        ),
        expected_output="Complete 400-500 word markdown research brief ready for executive review",
        agent=writer,
        context=[analyze_task, critique_task]
    )

    return [plan_task, research_task, analyze_task, critique_task, write_task]


# ─────────────────────────────────────────────
# RUN
# ─────────────────────────────────────────────

def run(topic: str) -> dict:
    print(f"\n{'='*55}")
    print(f"CREWAI RESEARCH PIPELINE (real crewai {__import__('crewai').__version__})")
    print(f"Topic: {topic}")
    print(f"{'='*55}")

    tasks = build_tasks(topic)

    crew = Crew(
        agents=[planner, researcher, analyst, critic, writer],
        tasks=tasks,
        process=Process.sequential,
        verbose=True
    )

    started = time.time()
    result = crew.kickoff()
    elapsed = time.time() - started

    # Извлекаем brief и critique из результата
    brief = str(result)

    # Парсим verdict из critique task output
    critique_output = tasks[3].output.raw if hasattr(tasks[3].output, 'raw') else str(tasks[3].output)
    verdict = "PASS" if "PASS" in critique_output.upper() else "FAIL"
    score_match = re.search(r'SCORE:\s*([\d.]+)', critique_output, re.IGNORECASE)
    score = float(score_match.group(1)) if score_match else 0.0

    print(f"\n{'='*55}")
    print(f"РЕЗУЛЬТАТ")
    print(f"{'='*55}")
    print(f"Quality Gate:  {verdict} (score={score})")
    print(f"Tasks:         {len(tasks)}")
    print(f"Elapsed:       {elapsed:.1f}s")
    print(f"\nBRIEF PREVIEW:")
    print("─"*55)
    print(brief[:500] + "...")

    return {
        "framework": "CrewAI",
        "crewai_version": __import__('crewai').__version__,
        "topic": topic,
        "brief": brief,
        "quality_gate": verdict,
        "score": score,
        "retries": 0,
        "tasks": len(tasks),
        "elapsed_seconds": elapsed,
        "note": "Sequential process — no built-in conditional retry loop"
    }


if __name__ == "__main__":
    topic = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else \
        "Research AI writing tools market: competitors, pricing, growth"

    result = run(topic)

    os.makedirs("outputs", exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    with open(f"outputs/crewai_brief_{ts}.md", "w") as f:
        f.write(f"# Research Brief (CrewAI {result['crewai_version']})\n"
                f"**Topic:** {topic}\n\n{result['brief']}")
    with open(f"outputs/crewai_log_{ts}.json", "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Saved to outputs/crewai_brief_{ts}.md")
