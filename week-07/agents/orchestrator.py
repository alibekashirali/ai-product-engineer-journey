"""
orchestrator.py — Координирует весь multi-agent pipeline.
Sequential flow с conditional routing:
  Planner → Researcher(×N) → Analyst → Critic → [PASS→Writer | FAIL→Researcher(refine)→Analyst→Critic] → Writer
"""
import json, sys, os, time
from datetime import datetime
sys.path.insert(0, os.path.dirname(__file__))
from planner import PlannerAgent
from researcher import ResearcherAgent
from analyst import AnalystAgent
from critic import CriticAgent
from writer import WriterAgent

MAX_RETRIES = 2


class Orchestrator:
    def __init__(self):
        self.planner    = PlannerAgent()
        self.researcher = ResearcherAgent()
        self.analyst    = AnalystAgent()
        self.critic     = CriticAgent()
        self.writer     = WriterAgent()
        self.run_log    = []
        self.started_at = None

    def _log(self, event: str, detail: str = ""):
        entry = {"event": event, "detail": detail, "timestamp": datetime.utcnow().isoformat()}
        self.run_log.append(entry)
        print(f"\n{'─'*50}")
        print(f"▶ {event}: {detail}")

    def run(self, topic: str) -> dict:
        self.started_at = datetime.utcnow()
        print(f"\n{'='*55}")
        print(f"MULTI-AGENT RESEARCH PIPELINE")
        print(f"Topic: {topic}")
        print(f"{'='*55}")

        # ── Step 1: PLAN ──────────────────────────────
        self._log("STEP 1: PLAN", f"decomposing '{topic}'")
        plan = self.planner.run(topic)
        subtasks = plan.get("subtasks", [])
        self._log("plan_ready", f"{len(subtasks)} subtasks")

        # ── Step 2: RESEARCH ──────────────────────────
        self._log("STEP 2: RESEARCH", f"gathering data for {len(subtasks)} subtasks")
        all_findings = []
        for subtask in subtasks:
            print(f"\n  researching: {subtask['task'][:60]}...")
            findings = self.researcher.run(subtask)
            all_findings.append(findings)
        self._log("research_done", f"{sum(len(f.get('findings',[])) for f in all_findings)} total findings")

        # ── Steps 3-4: ANALYZE + CRITIQUE (с retry) ──
        retries = 0
        analysis = None
        critique = None

        while retries <= MAX_RETRIES:
            # Step 3: ANALYZE
            self._log(f"STEP 3: ANALYZE (attempt {retries+1})", "synthesizing findings")
            analysis = self.analyst.run(all_findings, topic)

            # Step 4: CRITIQUE
            self._log(f"STEP 4: CRITIQUE (attempt {retries+1})", "evaluating quality")
            critique = self.critic.run(analysis, topic)
            verdict = critique.get('verdict', 'FAIL')
            score = critique.get('score', 0)

            print(f"\n  Critique verdict: {verdict} (score={score})")

            if verdict == "PASS":
                self._log("quality_gate_passed", f"score={score}")
                break

            if retries < MAX_RETRIES:
                feedback = critique.get('feedback', 'insufficient data')
                self._log(f"quality_gate_failed", f"retry {retries+1}/{MAX_RETRIES}: {feedback[:80]}")

                # Рефинируем researcher для слабых подзадач
                print(f"\n  Refining research based on: {feedback[:80]}...")
                refined_findings = []
                for subtask in subtasks:
                    refined = self.researcher.refine(subtask, feedback)
                    refined_findings.append(refined)
                all_findings = refined_findings

            retries += 1

        # ── Step 5: WRITE ─────────────────────────────
        self._log("STEP 5: WRITE", "generating final brief")
        brief = self.writer.run(analysis, critique, topic)

        # ── Collect all steps ─────────────────────────
        all_steps = (
            self.planner.steps +
            self.researcher.steps +
            self.analyst.steps +
            self.critic.steps +
            self.writer.steps
        )

        elapsed = (datetime.utcnow() - self.started_at).total_seconds()
        self._log("PIPELINE_COMPLETE", f"{len(all_steps)} total steps, {elapsed:.1f}s")

        return {
            "topic": topic,
            "plan": plan,
            "analysis": analysis,
            "critique": critique,
            "brief": brief,
            "steps": [s.to_dict() for s in all_steps],
            "run_log": self.run_log,
            "metadata": {
                "total_steps": len(all_steps),
                "retries": retries,
                "quality_gate": critique.get('verdict'),
                "final_score": critique.get('score'),
                "elapsed_seconds": elapsed,
                "agents_used": ["Planner", "Researcher", "Analyst", "Critic", "Writer"]
            }
        }
