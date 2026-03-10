import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import json as json_lib
from agents.base_agent import BaseAgent


class RiskStatementAgent(BaseAgent):
    """
    Agent 3 — Takes outputs from Market Analysis and Risk Assessment agents,
    synthesizes them into formal, numbered risk statements with scores.
    """

    def __init__(self):
        super().__init__("RiskStatementAgent")

    def analyze(self, project: dict, market_analysis: dict, risk_assessment: dict) -> dict:
        project_text = self.format_project_context(project)

        market_json = json_lib.dumps(market_analysis, indent=2, default=str)
        internal_json = json_lib.dumps(risk_assessment, indent=2, default=str)

        prompt = f"""You are a Risk Statement Agent. Your job is to synthesize the findings from the 
Market Analysis Agent and the Risk Assessment Agent into formal, structured risk statements.

PROJECT OVERVIEW:
{project_text}

MARKET ANALYSIS AGENT OUTPUT:
{market_json}

RISK ASSESSMENT AGENT OUTPUT:
{internal_json}

Create formal risk statements by:
1. Combining related external and internal risks where they intersect
2. Assigning each a unique risk ID (RSK-001, RSK-002, etc.)
3. Scoring each risk on a 1-25 scale (probability x impact, each 1-5)
4. Calculating an overall project risk score (weighted average)

Respond ONLY with valid JSON in this exact format:
{{
  "risk_statements": [
    {{
      "risk_id": "RSK-001",
      "title": "Short risk title",
      "description": "Detailed formal risk statement",
      "severity": "low | medium | high | critical",
      "score": <integer 1-25>,
      "probability": "1-5 with rationale",
      "impact_area": "schedule | budget | quality | scope | compliance"
    }}
  ],
  "overall_risk_score": <integer 1-25>,
  "overall_severity": "low | medium | high | critical",
  "executive_summary": "3-4 sentence executive summary of the risk landscape for leadership"
}}
"""
        return self.call_llm_json(prompt)
