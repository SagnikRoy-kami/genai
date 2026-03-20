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

    def __init__(self):
        self.market_agent = MarketAnalysisAgent()
        self.assessment_agent = RiskAssessmentAgent()
        self.statement_agent = RiskStatementAgent()
        self.mitigation_agent = RiskMitigationAgent()

    def run(self, project: dict) -> dict:

        tasks = project.get("tasks", [])
        resources = project.get("resources", [])
        dependencies = project.get("dependencies", [])

        project["signals"] = {
            "blocked_tasks": [t for t in tasks if t.get("current_status") in ["blocked", "delayed"]],
            "resource_gaps": [r for r in resources if r.get("currently_used", 0) < r.get("needed", 0)],
            "dependency_issues": [d for d in dependencies if d.get("status") != "resolved"]
        }

        logger.info("=== STAGE 1/4 — Market Analysis Agent ===")
        market_output = self.market_agent.analyze(project)
        market_risks = market_output.get("market_risks", []) or []
        logger.info(f"Market agent produced {len(market_risks)} risk factors.")

        logger.info("=== STAGE 2/4 — Risk Assessment Agent ===")
        assessment_output = self.assessment_agent.analyze({
            "project": project,
            "market_risks": market_risks,
            "signals": project.get("signals", {})
        })
        internal_risks = assessment_output.get("internal_risks", []) or []
        logger.info(f"Assessment agent produced {len(internal_risks)} internal risks.")

        logger.info("=== STAGE 3/4 — Risk Statement Agent ===")
        statement_output = self.statement_agent.analyze({
            "project": project,
            "market_risks": market_risks,
            "internal_risks": internal_risks
        })
        risk_statements = statement_output.get("risk_statements", []) or []
        logger.info(f"Statement agent produced {len(risk_statements)} formal statements.")

        logger.info("=== STAGE 4/4 — Risk Mitigation Agent ===")
        mitigation_output = self.mitigation_agent.analyze({
            "project": project,
            "risk_statements": risk_statements
        })
        mitigation_plan = mitigation_output.get("mitigation_plan", []) or []
        logger.info(f"Mitigation agent produced {len(mitigation_plan)} action plans.")

        high_confidence = 0
        low_confidence = 0
        for r in risk_statements:
            if r.get("evidence") and len(str(r.get("evidence", ""))) > 30:
                r["confidence"] = "high"
                high_confidence += 1
            else:
                r["confidence"] = "low"
                low_confidence += 1

        for m in mitigation_plan:
            if m.get("rationale") and len(str(m.get("rationale", ""))) > 20:
                m["confidence"] = m.get("confidence", "high")
            else:
                m["confidence"] = "low"

        report = {
            "project_name": project.get("name") or project.get("project_name", "Unknown"),
            "generated_at": datetime.now().isoformat(),
            "overall_risk_score": statement_output.get("overall_risk_score", 0),
            "overall_severity": statement_output.get("overall_severity", "unknown"),
            "executive_summary": statement_output.get("executive_summary", ""),
            "market_risks": market_risks,
            "internal_risks": internal_risks,
            "risk_statements": risk_statements,
            "mitigation_plan": mitigation_plan,
            "recommendations": mitigation_output.get("recommendations", []),
            "confidence_metrics": {
                "high_confidence_risks": high_confidence,
                "low_confidence_risks": low_confidence,
                "total_risks": len(risk_statements),
                "confidence_ratio": f"{high_confidence}/{len(risk_statements)}" if risk_statements else "0/0",
                "analysis_quality": "strong" if high_confidence > low_confidence else "moderate" if high_confidence > 0 else "weak"
            },
            "_meta": {
                "signals": project.get("signals", {}),
                "counts": {
                    "market": len(market_risks),
                    "internal": len(internal_risks),
                    "statements": len(risk_statements),
                    "mitigation": len(mitigation_plan),
                }
            }
        }

        logger.info(f"Final report generated — Overall Risk Score: {report['overall_risk_score']}/25")
        logger.info(f"Report type: {type(report)}, keys: {list(report.keys())}")
        return report

    def run_quick(self, project: dict) -> dict:

        tasks = project.get("tasks", [])
        resources = project.get("resources", [])
        dependencies = project.get("dependencies", [])

        project["signals"] = {
            "blocked_tasks": [t for t in tasks if t.get("current_status") in ["blocked", "delayed"]],
            "resource_gaps": [r for r in resources if r.get("currently_used", 0) < r.get("needed", 0)],
            "dependency_issues": [d for d in dependencies if d.get("status") != "resolved"]
        }

        logger.info("=== QUICK MODE: Running Agent 2 + 3 only ===")

        assessment_output = self.assessment_agent.analyze({
            "project": project,
            "market_risks": [],
            "signals": project.get("signals", {})
        })
        internal_risks = assessment_output.get("internal_risks", []) or []

        statement_output = self.statement_agent.analyze({
            "project": project,
            "market_risks": [],
            "internal_risks": internal_risks
        })

        # Load old mitigation + recommendations from last full analysis
        old_mitigation = []
        old_recommendations = []
        old_market = []
        try:
            from database.project_db import get_latest_report
            project_id = project.get("id")
            if project_id:
                old_report = get_latest_report(project_id)
                if old_report and isinstance(old_report, dict):
                    old_mitigation = old_report.get("mitigation_plan", [])
                    old_recommendations = old_report.get("recommendations", [])
                    old_market = old_report.get("market_risks", [])
        except Exception as e:
            logger.warning(f"Could not load previous report: {e}")

        return {
            "project_name": project.get("name") or project.get("project_name", "Unknown"),
            "generated_at": datetime.now().isoformat(),
            "overall_risk_score": statement_output.get("overall_risk_score", 0),
            "overall_severity": statement_output.get("overall_severity", "unknown"),
            "executive_summary": statement_output.get("executive_summary", ""),
            "market_risks": old_market,
            "internal_risks": internal_risks,
            "risk_statements": statement_output.get("risk_statements", []),
            "mitigation_plan": old_mitigation,
            "recommendations": old_recommendations,
            "mode": "quick_simulation"
        }