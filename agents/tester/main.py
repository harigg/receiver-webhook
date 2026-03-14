"""Tester agent — reviews PRs for test coverage and quality."""
import sys
sys.path.insert(0, "/app/shared")

from lib.base_agent import BaseAgent, MODEL_FAST


class TesterAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="Tester", model=MODEL_FAST)

    @property
    def system_prompt(self) -> str:
        return """You are the Tester Agent — a QA engineer reviewing test coverage.
Focus on:
- Are new features covered by unit tests?
- Are edge cases and error paths tested?
- Test quality: are assertions meaningful?
- Missing integration tests for complex interactions
- Flaky test patterns (time-dependent, order-dependent)
- Test naming and readability
- Mocking strategy appropriateness

Be concise. Use bullet points. Rate each issue: [Critical/High/Medium/Low].
"""
