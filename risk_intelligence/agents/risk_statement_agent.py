import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import json as json_lib
import logging
from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class RiskStatementAgent(BaseAgent):

    def __init__(self):
        super().__init__("RiskStatementAgent")

    def _calculate_data_driven_score(self, market_risks, internal_risks):
        """Calculate overall risk score. Internal risks (data-backed) weigh more than market risks (speculative)."""
        score = 0

        # Internal risks are DATA-DRIVEN — weigh heavily
        severity_scores = {"critical": 6, "high": 4, "medium": 2, "low": 1}
        for ir in internal_risks:
            score += severity_scores.get(str(ir.get("severity", "low")).lower(), 1)

        # Market risks are SPECULATIVE — cap their total contribution at 5
        market_score = 0
        likelihood_scores = {"high": 2, "medium": 1, "low": 0}
        for mr in market_risks:
            market_score += likelihood_scores.get(str(mr.get("likelihood", "low")).lower(), 0)
        score += min(market_score, 5)  # Market can add at most 5 points

        return max(1, min(score, 25))

    def _validate_risk_score(self, score):
        """Ensure a single risk score is within 1-25."""
        try:
            s = int(score)
            return max(1, min(s, 25))
        except (TypeError, ValueError):
            return 10

    def _get_severity(self, score):
        if score <= 5: return "low"
        elif score <= 10: return "medium"
        elif score <= 18: return "high"
        else: return "critical"

    def analyze(self, input_data: dict) -> dict:
        project = input_data.get("project", {})
        market_risks = input_data.get("market_risks", [])
        internal_risks = input_data.get("internal_risks", [])

        project_text = self.format_project_context(project)

        # Calculate data-driven score BEFORE calling LLM
        data_score = self._calculate_data_driven_score(market_risks, internal_risks)
        data_severity = self._get_severity(data_score)

        logger.info(f"[RiskStatement] Data-driven score: {data_score}/25 ({data_severity})")
        logger.info(f"[RiskStatement] Input: {len(market_risks)} market risks, {len(internal_risks)} internal risks")

        # If no risks at all, return minimal report
        if not market_risks and not internal_risks:
            return {
                "risk_statements": [{
                    "risk_id": "RSK-001",
                    "title": "Low Risk Profile",
                    "description": "No significant market or internal risks were identified. All resources are allocated, no tasks are blocked, and dependencies are resolved.",
                    "severity": "low",
                    "score": 2,
                    "probability": "1 (no active issues detected)",
                    "impact_area": "scope"
                }],
                "overall_risk_score": 2,
                "overall_severity": "low",
                "executive_summary": "The project shows a low risk profile. No resource gaps, blocked tasks, or unresolved dependencies were detected. Market conditions appear stable based on available data."
            }

        prompt = f"""You are a Risk Statement Generator.

PROJECT:
{project_text}

MARKET RISKS (from Agent 1):
{json_lib.dumps(market_risks, default=str)}

INTERNAL RISKS (from Agent 2):
{json_lib.dumps(internal_risks, default=str)}

RULES:
1. Create ONE risk statement for EACH market risk and EACH internal risk — keep them separate
2. Assign risk_id as RSK-001, RSK-002, etc.
3. Score = Probability (1-5) x Impact (1-5). Maximum possible score is 25.
4. DO NOT inflate scores. Base scores strictly on evidence:
   - A risk with no evidence of impact = score 1-5 (low)
   - A risk with moderate evidence = score 6-10 (medium)
   - A risk with strong evidence from data = score 11-18 (high)
   - Only score 19-25 if the risk is ALREADY HAPPENING (blocked, delayed, zero resources)
5. Do NOT invent risks beyond what is provided above
6. If market/internal risks are few, generate fewer statements — do NOT pad

Respond ONLY with valid JSON:

{{
  "risk_statements": [
    {{
      "risk_id": "RSK-001",
      "title": "Short title",
      "description": "What causes this risk and what it impacts",
      "severity": "low | medium | high | critical",
      "score": 1-25,
      "probability": "1-5 with brief reason",
      "impact_area": "schedule | budget | quality | scope | compliance"
    }}
  ],
  "executive_summary": "3-4 sentences summarizing the risk landscape"
}}
"""

        data = self.call_llm_json(prompt)
        risks = data.get("risk_statements") or []

        # ── VALIDATE AND CAP EVERY INDIVIDUAL SCORE ──
        for r in risks:
            r["score"] = self._validate_risk_score(r.get("score", 10))
            r["severity"] = self._get_severity(r["score"])

        # ── REMOVE DUPLICATES / HALLUCINATED RISKS ──
        # If LLM generated more statements than input risks, trim extras
        max_expected = len(market_risks) + len(internal_risks)
        if max_expected > 0 and len(risks) > max_expected + 2:
            logger.warning(f"[RiskStatement] LLM generated {len(risks)} statements for {max_expected} input risks — trimming")
            risks = risks[:max_expected + 2]

        # ── FALLBACK if LLM returned nothing ──
        if not risks:
            risks = []
            for i, mr in enumerate(market_risks):
                risks.append({
                    "risk_id": f"RSK-{i+1:03d}",
                    "title": mr.get("factor", "Market Risk"),
                    "description": mr.get("impact", "External market risk identified"),
                    "severity": "medium" if mr.get("likelihood") == "medium" else "low" if mr.get("likelihood") == "low" else "high",
                    "score": {"high": 12, "medium": 8, "low": 4}.get(str(mr.get("likelihood", "low")).lower(), 6),
                    "probability": "Based on market analysis",
                    "impact_area": "scope"
                })
            offset = len(market_risks)
            for i, ir in enumerate(internal_risks):
                sev = str(ir.get("severity", "medium")).lower()
                risks.append({
                    "risk_id": f"RSK-{offset+i+1:03d}",
                    "title": f"{ir.get('category', 'Internal')} Risk",
                    "description": ir.get("description", "Internal risk identified"),
                    "severity": sev,
                    "score": {"critical": 20, "high": 14, "medium": 8, "low": 3}.get(sev, 8),
                    "probability": ir.get("evidence", "Based on internal assessment"),
                    "impact_area": "schedule"
                })

        # ── CALCULATE OVERALL SCORE FROM DATA, NOT LLM ──
        if risks:
            avg_score = sum(r.get("score", 5) for r in risks) / len(risks)
            # Blend: 80% data-driven score, 20% LLM average (keeps LLM honest)
            overall_score = int(data_score * 0.8 + avg_score * 0.2)
        else:
            overall_score = data_score

        overall_score = max(1, min(overall_score, 25))
        overall_severity = self._get_severity(overall_score)

        # ── SUMMARY ──
        summary = data.get("executive_summary", "")
        if not summary:
            summary = f"Project shows {overall_severity} risk exposure (score {overall_score}/25) with {len(market_risks)} external and {len(internal_risks)} internal risks identified."

        logger.info(f"[RiskStatement] Final: {len(risks)} statements, score={overall_score}/25 ({overall_severity})")

        return {
            "risk_statements": risks,
            "overall_risk_score": overall_score,
            "overall_severity": overall_severity,
            "executive_summary": summary
        }