"""
langgraph_pipeline.py — Week 8
Research pipeline реализованный через LangGraph StateGraph.

Ключевое отличие от Week 7:
- Состояние передаётся через typed dict (ResearchState)
- Conditional edges решают баг "wrong retry target"
- Каждый узел получает только нужную часть state
"""

import json
import os
import sys
import time
from typing import TypedDict, Optional
from datetime import datetime

from langgraph.graph import StateGraph, END
import anthropic

client = anthropic.Anthropic()
MODEL = "claude-sonnet-4-6"

# ─────────────────────────────────────────────
# STATE — typed dict, передаётся через граф
# ─────────────────────────────────────────────
class ResearchState(TypedDict):
    topic:         str
    subtasks:      list
    findings:      list
    analysis:      dict
    critique:      dict
    brief:         str
    retry_count:   int
    retry_reason:  str   # ← key для conditional routing
    started_at:    str
    steps_log:     list


# ─────────────────────────────────────────────
# HELPER
# ─────────────────────────────────────────────
def call_llm(system: str, user: str, max_tokens: int = 800) -> str:
    r = client.messages.create(
        model=MODEL, max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}]
    )
    return r.content[0].text

def log_step(state: ResearchState, agent: str, action: str, detail: str = "") -> list:
    steps = state.get("steps_log", [])
    ts = datetime.utcnow().strftime("%H:%M:%S")
    print(f"  [{ts}] [{agent}] {action}{': ' + detail if detail else ''}")
    steps.append({"agent": agent, "action": action, "detail": detail,
                  "timestamp": datetime.utcnow().isoformat()})
    return steps


# ─────────────────────────────────────────────
# NODES
# ─────────────────────────────────────────────

def planner_node(state: ResearchState) -> ResearchState:
    """Декомпозирует тему на 3 подзадачи."""
    steps = log_step(state, "Planner", "decompose", state["topic"][:50])

    raw = call_llm(
        "You are a research planner. Break the topic into 3 subtasks. "
        "Use format:\nSUBTASK_1: [task]\nFOCUS_1: [focus]\n"
        "SUBTASK_2: [task]\nFOCUS_2: [focus]\n"
        "SUBTASK_3: [task]\nFOCUS_3: [focus]",
        f"Topic: {state['topic']}", max_tokens=400
    )

    subtasks = []
    lines = raw.strip().split('\n')
    tasks = [l.split(':', 1)[1].strip() for l in lines if l.startswith('SUBTASK_')]
    focuses = [l.split(':', 1)[1].strip() for l in lines if l.startswith('FOCUS_')]
    for i, (t, f) in enumerate(zip(tasks, focuses), 1):
        subtasks.append({'id': i, 'task': t, 'focus': f})

    if not subtasks:
        subtasks = [{'id': 1, 'task': state['topic'], 'focus': 'general research'}]

    steps = log_step({'steps_log': steps}, "Planner", "plan_ready",
                     f"{len(subtasks)} subtasks")
    return {**state, "subtasks": subtasks, "steps_log": steps}


def researcher_node(state: ResearchState) -> ResearchState:
    """Собирает данные по каждой подзадаче."""
    steps = log_step(state, "Researcher", "research",
                     f"{len(state['subtasks'])} subtasks")

    context = ""
    if state.get("retry_reason") and "data" in state["retry_reason"].lower():
        context = f"\nPrevious attempt was insufficient: {state['retry_reason']}"

    all_findings = []
    for subtask in state["subtasks"]:
        raw = call_llm(
            "You are a market researcher. Use format:\n"
            "FINDING_1: [finding]\nDETAIL_1: [detail]\n"
            "FINDING_2: [finding]\nDETAIL_2: [detail]\n"
            "FINDING_3: [finding]\nDETAIL_3: [detail]\n"
            "CONFIDENCE: high|medium|low",
            f"Research: {subtask['task']}\nFocus: {subtask['focus']}{context}",
            max_tokens=600
        )

        # Parse text format
        import re
        findings = []
        lines = raw.split('\n')
        current_point = None
        for line in lines:
            line = line.strip()
            if re.match(r'FINDING_\d+:', line):
                current_point = line.split(':', 1)[1].strip()
            elif re.match(r'DETAIL_\d+:', line) and current_point:
                findings.append({'point': current_point,
                                 'detail': line.split(':', 1)[1].strip()})
                current_point = None

        all_findings.append({
            'subtask': subtask['task'],
            'findings': findings or [{'point': raw[:100], 'detail': ''}],
            'confidence': 'medium'
        })

    total = sum(len(f['findings']) for f in all_findings)
    steps = log_step({'steps_log': steps}, "Researcher", "findings_ready",
                     f"{total} findings")
    return {**state, "findings": all_findings, "steps_log": steps,
            "retry_reason": ""}  # сбрасываем retry_reason


def analyst_node(state: ResearchState) -> ResearchState:
    """Структурирует findings в анализ."""
    steps = log_step(state, "Analyst", "analyze",
                     f"{len(state['findings'])} research sets")

    findings_text = ""
    for f in state["findings"]:
        findings_text += f"\n[{f['subtask']}]\n"
        for p in f['findings'][:3]:
            findings_text += f"• {p['point']}: {p.get('detail', '')[:100]}\n"

    raw = call_llm(
        "You are a market analyst. Analyze findings. Use format:\n"
        "SUMMARY: [2-3 sentence overview]\n"
        "SECTION_1: [title] | [insight 1] | [insight 2]\n"
        "SECTION_2: [title] | [insight 1] | [insight 2]\n"
        "TRENDS: [trend1] | [trend2] | [trend3]\n"
        "LANDSCAPE: [competitive overview]\n"
        "OPPORTUNITIES: [opp1] | [opp2]\n"
        "RISKS: [risk1] | [risk2]\n"
        "Keep each field concise — max 100 words total per field.",
        f"Topic: {state['topic']}\n\nFindings:\n{findings_text[:2000]}",
        max_tokens=800
    )

    # Parse
    analysis = {'topic': state['topic'], 'key_sections': [],
                'market_trends': [], 'opportunities': [], 'risks': [],
                'confidence_score': 0.7}
    for line in raw.split('\n'):
        line = line.strip()
        if line.startswith('SUMMARY:'):
            analysis['executive_summary'] = line.split(':', 1)[1].strip()
        elif line.startswith('SECTION_'):
            parts = line.split(':', 1)[1].strip().split(' | ')
            if parts:
                analysis['key_sections'].append({
                    'title': parts[0],
                    'insights': parts[1:],
                    'evidence': ''
                })
        elif line.startswith('TRENDS:'):
            analysis['market_trends'] = [t.strip() for t in
                                          line.split(':', 1)[1].split(' | ')]
        elif line.startswith('LANDSCAPE:'):
            analysis['competitive_landscape'] = line.split(':', 1)[1].strip()
        elif line.startswith('OPPORTUNITIES:'):
            analysis['opportunities'] = [o.strip() for o in
                                          line.split(':', 1)[1].split(' | ')]
        elif line.startswith('RISKS:'):
            analysis['risks'] = [r.strip() for r in
                                  line.split(':', 1)[1].split(' | ')]

    if not analysis.get('executive_summary'):
        analysis['executive_summary'] = raw[:200]
        analysis['key_sections'] = [{'title': 'Analysis', 'insights': [raw[:300]], 'evidence': ''}]

    n = len(analysis['key_sections'])
    steps = log_step({'steps_log': steps}, "Analyst", "analysis_ready",
                     f"{n} sections")
    return {**state, "analysis": analysis, "steps_log": steps}


def critic_node(state: ResearchState) -> ResearchState:
    """Оценивает качество анализа — PASS или FAIL с указанием причины."""
    steps = log_step(state, "Critic", "evaluate", state["topic"][:50])

    a = state["analysis"]
    summary = (f"Summary: {a.get('executive_summary', 'EMPTY')[:150]}\n"
               f"Sections: {len(a.get('key_sections', []))}\n"
               f"Trends: {', '.join(a.get('market_trends', [])[:3])}\n"
               f"Landscape: {a.get('competitive_landscape', 'EMPTY')[:100]}")

    raw = call_llm(
        "You are a quality critic. Evaluate the analysis.\n"
        "Use format:\nVERDICT: PASS or FAIL\n"
        "SCORE: 0.0-1.0\n"
        "ISSUE_TYPE: data|analysis|none  (data=need more research, analysis=need better synthesis)\n"
        "FEEDBACK: [specific feedback]\n"
        "PASS if score >= 0.65",
        f"Topic: {state['topic']}\n\nAnalysis:\n{summary}",
        max_tokens=300
    )

    critique = {'verdict': 'FAIL', 'score': 0.0,
                'issue_type': 'analysis', 'feedback': ''}
    for line in raw.split('\n'):
        line = line.strip()
        if line.startswith('VERDICT:'):
            critique['verdict'] = line.split(':', 1)[1].strip().upper()
        elif line.startswith('SCORE:'):
            try:
                critique['score'] = float(line.split(':', 1)[1].strip())
            except ValueError:
                pass
        elif line.startswith('ISSUE_TYPE:'):
            critique['issue_type'] = line.split(':', 1)[1].strip().lower()
        elif line.startswith('FEEDBACK:'):
            critique['feedback'] = line.split(':', 1)[1].strip()

    v = critique['verdict']
    s = critique['score']
    steps = log_step({'steps_log': steps}, "Critic", "verdict",
                     f"{v} (score={s})")
    return {**state, "critique": critique, "steps_log": steps}


def writer_node(state: ResearchState) -> ResearchState:
    """Генерирует финальный markdown brief."""
    steps = log_step(state, "Writer", "write",
                     f"confidence={state['analysis'].get('confidence_score')}")

    a = state["analysis"]
    quality_note = ""
    if state["critique"].get("verdict") == "FAIL":
        quality_note = "\n> ⚠️ Данные требуют дополнительной верификации.\n"

    prompt = (f"Write a professional market research brief in markdown.\n"
              f"Topic: {state['topic']}\n{quality_note}\n"
              f"Summary: {a.get('executive_summary', '')}\n"
              f"Landscape: {a.get('competitive_landscape', '')}\n"
              f"Trends: {', '.join(a.get('market_trends', []))}\n"
              f"Opportunities: {', '.join(a.get('opportunities', []))}\n"
              f"Risks: {', '.join(a.get('risks', []))}\n"
              f"Target: 400-500 words, professional tone.")

    brief = call_llm("You are a business writer.", prompt, max_tokens=1000)
    words = len(brief.split())
    steps = log_step({'steps_log': steps}, "Writer", "brief_ready",
                     f"{words} words")
    return {**state, "brief": brief, "steps_log": steps}


# ─────────────────────────────────────────────
# CONDITIONAL ROUTING — решение бага Week 7
# ─────────────────────────────────────────────

def route_after_critic(state: ResearchState) -> str:
    """
    Ключевое отличие от Week 7:
    Critic указывает issue_type → маршрутизируем к нужному агенту.

    Week 7: всегда → researcher (неправильно)
    Week 8: анализируем issue_type → researcher ИЛИ analyst ИЛИ writer
    """
    critique = state.get("critique", {})
    verdict = critique.get("verdict", "FAIL")
    issue_type = critique.get("issue_type", "analysis")
    retry_count = state.get("retry_count", 0)

    if verdict == "PASS":
        return "writer"

    if retry_count >= 2:
        print(f"\n  [Orchestrator] Max retries reached → writer (best effort)")
        return "writer"

    if issue_type == "data":
        print(f"\n  [Orchestrator] Issue: insufficient data → researcher")
        return "researcher"
    else:
        print(f"\n  [Orchestrator] Issue: poor synthesis → analyst")
        return "analyst"


def increment_retry(state: ResearchState) -> ResearchState:
    """Промежуточный узел: увеличивает счётчик retry и сохраняет причину."""
    return {
        **state,
        "retry_count": state.get("retry_count", 0) + 1,
        "retry_reason": state["critique"].get("feedback", "")
    }


# ─────────────────────────────────────────────
# BUILD GRAPH
# ─────────────────────────────────────────────

def build_graph():
    graph = StateGraph(ResearchState)

    graph.add_node("planner",       planner_node)
    graph.add_node("researcher",    researcher_node)
    graph.add_node("analyst",       analyst_node)
    graph.add_node("critic",        critic_node)
    graph.add_node("retry_handler", increment_retry)
    graph.add_node("writer",        writer_node)

    # Линейный flow
    graph.set_entry_point("planner")
    graph.add_edge("planner",    "researcher")
    graph.add_edge("researcher", "analyst")
    graph.add_edge("analyst",    "critic")

    # Conditional routing после critic
    graph.add_conditional_edges(
        "critic",
        route_after_critic,
        {
            "researcher": "retry_handler",
            "analyst":    "retry_handler",
            "writer":     "writer"
        }
    )

    # retry_handler → правильный агент
    def route_after_retry(state: ResearchState) -> str:
        issue = state.get("critique", {}).get("issue_type", "analysis")
        return "researcher" if issue == "data" else "analyst"

    graph.add_conditional_edges(
        "retry_handler",
        route_after_retry,
        {"researcher": "researcher", "analyst": "analyst"}
    )

    graph.add_edge("writer", END)

    return graph.compile()


# ─────────────────────────────────────────────
# RUN
# ─────────────────────────────────────────────

def run(topic: str) -> dict:
    print(f"\n{'='*55}")
    print(f"LANGGRAPH RESEARCH PIPELINE")
    print(f"Topic: {topic}")
    print(f"{'='*55}")

    app = build_graph()
    started = time.time()

    initial_state: ResearchState = {
        "topic": topic, "subtasks": [], "findings": [],
        "analysis": {}, "critique": {}, "brief": "",
        "retry_count": 0, "retry_reason": "",
        "started_at": datetime.utcnow().isoformat(),
        "steps_log": []
    }

    final_state = app.invoke(initial_state)
    elapsed = time.time() - started

    print(f"\n{'='*55}")
    print(f"РЕЗУЛЬТАТ")
    print(f"{'='*55}")
    print(f"Quality Gate:  {final_state['critique'].get('verdict')} "
          f"(score={final_state['critique'].get('score')})")
    print(f"Retries:       {final_state['retry_count']}")
    print(f"Steps:         {len(final_state['steps_log'])}")
    print(f"Elapsed:       {elapsed:.1f}s")
    print(f"\nBRIEF PREVIEW:")
    print("─"*55)
    print(final_state["brief"][:500] + "...")

    return {
        "framework": "LangGraph",
        "topic": topic,
        "brief": final_state["brief"],
        "quality_gate": final_state["critique"].get("verdict"),
        "score": final_state["critique"].get("score"),
        "retries": final_state["retry_count"],
        "steps": len(final_state["steps_log"]),
        "elapsed_seconds": elapsed,
        "steps_log": final_state["steps_log"]
    }


if __name__ == "__main__":
    import sys
    topic = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else \
        "Research AI writing tools market: competitors, pricing, growth"
    result = run(topic)

    # Сохраняем
    os.makedirs("outputs", exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    with open(f"outputs/langgraph_brief_{ts}.md", "w") as f:
        f.write(f"# Research Brief (LangGraph)\n**Topic:** {topic}\n\n")
        f.write(result["brief"])
    with open(f"outputs/langgraph_log_{ts}.json", "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Saved to outputs/langgraph_brief_{ts}.md")
