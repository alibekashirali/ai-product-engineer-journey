"""
base_agent.py — Base class for all agents in the pipeline.
"""
import os
import sys
from datetime import datetime
import anthropic

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

MODEL = "claude-sonnet-4-6"
_client = anthropic.Anthropic()


class AgentStep:
    def __init__(self, agent: str, action: str, input_summary: str, output_summary: str):
        self.agent = agent
        self.action = action
        self.input_summary = input_summary[:200]
        self.output_summary = output_summary[:300]
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self):
        return {
            "agent": self.agent,
            "action": self.action,
            "input": self.input_summary,
            "output": self.output_summary,
            "timestamp": self.timestamp
        }


class BaseAgent:
    def __init__(self, name: str, role: str, system_prompt: str):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.steps: list = []

    def call_llm(self, prompt: str, max_tokens: int = 1000) -> str:
        response = _client.messages.create(
            model=MODEL,
            max_tokens=max_tokens,
            system=self.system_prompt,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text

    def log(self, action: str, subject: str, detail: str = ""):
        ts = datetime.utcnow().strftime("%H:%M:%S")
        detail_str = f" — {detail}" if detail else ""
        print(f"[{ts}] [{self.name}] {action}: {subject}{detail_str}")
        self.steps.append(AgentStep(
            agent=self.name,
            action=action,
            input_summary=subject,
            output_summary=detail
        ))