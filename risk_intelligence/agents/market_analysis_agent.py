import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from agents.base_agent import BaseAgent


class MarketAnalysisAgent(BaseAgent):
    """
    Agent 1 — Scans external environment: market trends, economic indicators,
    competitor moves, regulatory changes. Uses RAG for company history context.
    """

    def __init__(self):
        super().__init__("MarketAnalysisAgent")

    def analyze(self, project: dict) -> dict:
        project_text = self.format_project_context(project)

        rag_context = self.get_rag_context(
            f"market trends economic risks regulatory changes for {project['name']}"
        )

        prompt = f"""You are a Market Analysis Agent specializing in external risk factors.

COMPANY HISTORY (from internal knowledge base):
{rag_context}

CURRENT PROJECT DATA:
{project_text}

Analyze the external risk landscape for this project. Consider:
1. Market trends that could affect project success or timeline
2. Economic indicators (interest rates, funding climate, sector health)
3. Regulatory and compliance risks
4. Competitor activity that could impact project value
5. Vendor/supplier risks based on dependencies listed

Respond ONLY with valid JSON in this exact format:
{{
  "market_risks": [
    {{
      "factor": "Name of the risk factor",
      "impact": "Description of how it impacts this project",
      "likelihood": "high | medium | low",
      "evidence": "Specific evidence from company history or project data"
    }}
  ],
  "market_summary": "2-3 sentence executive summary of external risk posture",
  "external_risk_score": <integer 1-25>
}}
"""
        return self.call_llm_json(prompt)
