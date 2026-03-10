import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import logging
from datetime import datetime

from agents.market_analysis_agent import MarketAnalysisAgent
from agents.risk_assessment_agent import RiskAssessmentAgent
from agents.risk_statement_agent import RiskStatementAgent
from agents.risk_mitigation_agent import RiskMitigationAgent

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Chains the 4 agents in sequence, passing each agent's output to the next.

    Pipeline:
      1. MarketAnalysisAgent   -> external risks
      2. RiskAssessmentAgent   -> internal risks (receives market output)
      3. RiskStatementAgent    -> formal risk statements (receives both)
      4. RiskMitigationAgent   -> mitigation plan (receives statements)
    """

    def __init__(self):
        self.market_agent = MarketAnalysisAgent()
        self.assessment_agent = RiskAssessmentAgent()
        self.statement_agent = RiskStatementAgent()
        self.mitigation_agent = RiskMitigationAgent()

    def run(self, project: dict) -> dict:
        """Execute the full agent pipeline and return the consolidated report."""

        logger.info("=== STAGE 1/4 — Market Analysis Agent ===")
        market_output = self.market_agent.analyze(project)
        logger.info(f"Market agent produced {len(market_output.get('market_risks', []))} risk factors.")

        logger.info("=== STAGE 2/4 — Risk Assessment Agent ===")
        assessment_output = self.assessment_agent.analyze(project, market_output)
        logger.info(f"Assessment agent produced {len(assessment_output.get('internal_risks', []))} internal risks.")

        logger.info("=== STAGE 3/4 — Risk Statement Agent ===")
        statement_output = self.statement_agent.analyze(project, market_output, assessment_output)
        logger.info(f"Statement agent produced {len(statement_output.get('risk_statements', []))} formal statements.")

        logger.info("=== STAGE 4/4 — Risk Mitigation Agent ===")
        mitigation_output = self.mitigation_agent.analyze(project, statement_output)
        logger.info(f"Mitigation agent produced {len(mitigation_output.get('mitigation_plan', []))} action plans.")

        # Consolidate into final report
        report = {
            "project_name": project.get("name", "Unknown"),
            "generated_at": datetime.now().isoformat(),
            "overall_risk_score": statement_output.get("overall_risk_score", 0),
            "overall_severity": statement_output.get("overall_severity", "unknown"),
            "executive_summary": statement_output.get("executive_summary", ""),
            "market_risks": market_output.get("market_risks", []),
            "internal_risks": assessment_output.get("internal_risks", []),
            "risk_statements": statement_output.get("risk_statements", []),
            "mitigation_plan": mitigation_output.get("mitigation_plan", []),
            "recommendations": mitigation_output.get("recommendations", []),
            "_agent_outputs": {
                "market": market_output,
                "assessment": assessment_output,
                "statements": statement_output,
                "mitigation": mitigation_output,
            },
        }

        logger.info(f"Final report generated — Overall Risk Score: {report['overall_risk_score']}/25")
        return report
