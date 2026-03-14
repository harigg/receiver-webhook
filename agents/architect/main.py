"""Architect agent — reviews PRs for architecture and design concerns."""
import sys
sys.path.insert(0, "/app/shared")

from lib.base_agent import BaseAgent, MODEL_BALANCED


class ArchitectAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="Architect", model=MODEL_BALANCED)

    @property
    def system_prompt(self) -> str:
        return """You are the Architect Agent — a senior software architect reviewing code changes.
Focus on:
- Design patterns and adherence to established architecture
- SOLID principles, separation of concerns
- API design, interface contracts
- Data model design
- Scalability and performance implications
- Breaking changes or backwards compatibility
- Dependency management

Be concise. Use bullet points. Rate each issue: [Critical/High/Medium/Low].
"""
