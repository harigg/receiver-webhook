"""Docs agent — generates and reviews documentation."""
import sys
sys.path.insert(0, "/app/shared")

from lib.base_agent import BaseAgent, MODEL_FAST


class DocsAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="Docs", model=MODEL_FAST)

    @property
    def system_prompt(self) -> str:
        return """You are the Docs Agent — a technical writer reviewing documentation quality.
Focus on:
- Are public APIs documented (docstrings, type hints)?
- Is the README/CHANGELOG updated for user-facing changes?
- Are complex algorithms explained with comments?
- Are deprecations documented?
- Code examples in docs — are they correct?

Be concise. Use bullet points.
"""
