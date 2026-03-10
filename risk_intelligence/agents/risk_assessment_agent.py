import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from agents.base_agent import BaseAgent


class RiskAssessmentAgent(BaseAgent):
    """
    Agent 2 — Evaluates internal project risks: schedule slippage, resource gaps,
    dependency chains, budget overruns. Cross-references company history via RAG.
    """

    def __init__(self):
        super().__init__("RiskAssessmentAgent")

    def analyze(self, project: dict, market_analysis: dict) -> dict:
        project_text = self.format_project_context(project)

        rag_context = self.get_rag_context(
            "project delays resource shortage dependency failure budget overrun"
        )

        market_summary = market_analysis.get("market_summary", "No market analysis available.")

        prompt = f"""You are a Risk Assessment Agent specializing in internal project risk evaluation.

COMPANY HISTORY (from internal knowledge base):
{rag_context}

MARKET ANALYSIS (from the Market Analysis Agent):
{market_summary}

CURRENT PROJECT DATA:
{project_text}

Perform a thorough internal risk assessment. Evaluate:
1. Schedule risk: Are any tasks delayed? Are timelines realistic given company history?
2. Resource risk: Compare needed vs. used resources. Flag critical gaps.
3. Dependency risk: Identify blocked or pending dependencies and their downstream impact.
4. Budget risk: Is the budget utilization on track? Compare with historical overruns.
5. Execution risk: Based on similar past projects, what patterns of failure apply?

Respond ONLY with valid JSON in this exact format:
{{
  "internal_risks": [
    {{
      "category": "schedule | resource | dependency | budget | execution",
      "description": "Clear description of the risk",
      "severity": "low | medium | high | critical",
      "affected_tasks": ["list", "of", "task", "names"],
      "evidence": "Specific data points from project data or company history"
    }}
  ],
  "internal_summary": "2-3 sentence summary of internal risk posture",
  "internal_risk_score": <integer 1-25>
}}
"""
        return self.call_llm_json(prompt)
