"""Requirements agent — validates implementation matches requirements."""
import sys
sys.path.insert(0, "/app/shared")

from lib.base_agent import BaseAgent, MODEL_FAST


class RequirementsAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="Requirements", model=MODEL_FAST)

    @property
    def system_prompt(self) -> str:
        return """You are the Requirements Agent — you validate that code changes match their stated requirements.
Given a PR description and code diff, assess:
- Does the implementation fulfill the stated requirements?
- Are there unrelated changes bundled into this PR?
- Are acceptance criteria met (if stated)?
- Are there obvious missing pieces?

Be concise. Use bullet points.
"""
