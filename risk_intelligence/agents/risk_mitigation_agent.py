import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import json as json_lib
from agents.base_agent import BaseAgent


class RiskMitigationAgent(BaseAgent):
    """
    Agent 4 — Takes the formal risk statements and generates specific,
    actionable mitigation strategies with owners, priorities, and timelines.
    Uses RAG to reference what worked (or failed) historically.
    """

    def __init__(self):
        super().__init__("RiskMitigationAgent")

    def analyze(self, project: dict, risk_statements: dict) -> dict:
        project_text = self.format_project_context(project)

        rag_context = self.get_rag_context(
            "mitigation strategy risk resolution successful project recovery contingency"
        )

        statements_json = json_lib.dumps(risk_statements, indent=2, default=str)

        prompt = f"""You are a Risk Mitigation Agent. Your job is to create actionable mitigation plans
for each risk identified by the Risk Statement Agent.

COMPANY HISTORY — PAST MITIGATIONS & STRATEGIES:
{rag_context}

PROJECT OVERVIEW:
{project_text}

RISK STATEMENTS FROM PREVIOUS AGENT:
{statements_json}

For each risk statement, create a concrete mitigation plan. Consider:
1. What worked in similar past situations (from company history)
2. What failed and should be avoided
3. Specific action steps (not vague recommendations)
4. Who should own each mitigation (role, not person)
5. Priority ranking and realistic timelines

Also provide 3-5 overall strategic recommendations for leadership.

Respond ONLY with valid JSON in this exact format:
{{
  "mitigation_plan": [
    {{
      "risk_id": "RSK-001",
      "strategy": "Name of the mitigation strategy",
      "action_steps": [
        "Specific action step 1",
        "Specific action step 2"
      ],
      "owner": "Role responsible (e.g. Project Manager, CTO, DevOps Lead)",
      "priority": "critical | high | medium | low",
      "timeline": "e.g. Immediate, Within 2 weeks, Before Q3"
    }}
  ],
  "recommendations": [
    "Strategic recommendation 1 for leadership",
    "Strategic recommendation 2 for leadership"
  ]
}}
"""
        return self.call_llm_json(prompt)
