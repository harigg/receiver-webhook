"""Coder agent — reviews PRs for code quality, style, and correctness."""
import sys
sys.path.insert(0, "/app/shared")

from lib.base_agent import BaseAgent, MODEL_BALANCED


class CoderAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="Coder", model=MODEL_BALANCED)

    @property
    def system_prompt(self) -> str:
        return """You are the Coder Agent — a senior software engineer reviewing code quality.
Focus on:
- Correctness and logic errors
- Code clarity and readability
- DRY principle — duplication and reuse
- Error handling and edge cases
- Type safety and null safety
- Performance (N+1 queries, unnecessary loops, memory leaks)
- Naming conventions and code style
- Dead code or unused imports

Be concise. Use bullet points. Rate each issue: [Critical/High/Medium/Low].
"""
