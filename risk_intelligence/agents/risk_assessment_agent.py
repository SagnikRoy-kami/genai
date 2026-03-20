import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import logging
from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class RiskAssessmentAgent(BaseAgent):

    def __init__(self):
        super().__init__("RiskAssessmentAgent")

    def _safe_float(self, val, default=0):
        """Force any value to float. Handles strings, None, etc."""
        try:
            return float(val)
        except (TypeError, ValueError):
            return default

    def analyze(self, input_data: dict) -> dict:
        project = input_data.get("project", {})
        market_risks = input_data.get("market_risks", [])

        tasks = project.get("tasks", [])
        resources = project.get("resources", [])
        dependencies = project.get("dependencies", [])

        logger.info(f"[RiskAssessment] Input: {len(tasks)} tasks, {len(resources)} resources, {len(dependencies)} dependencies")

        detected_risks = []

        # ══════════════════════════════════════════════
        # 1. RESOURCE GAP ANALYSIS
        # ══════════════════════════════════════════════
        for r in resources:
            needed = self._safe_float(r.get("needed", 0))
            used = self._safe_float(r.get("currently_used", 0))
            unit = r.get("unit", "count")

            if needed <= 0:
                continue

            gap = needed - used
            gap_pct = (gap / needed) * 100

            logger.info(f"[RiskAssessment] Resource: {r.get('resource_type')} — needed={needed}, used={used}, gap={gap_pct:.1f}%")

            if gap_pct <= 0:
                continue

            if gap_pct >= 75:
                severity = "critical"
            elif gap_pct >= 50:
                severity = "high"
            elif gap_pct >= 25:
                severity = "medium"
            else:
                severity = "low"

            # Skip budget items here — handled separately below
            if unit.upper() == "USD":
                continue

            detected_risks.append({
                "category": "resource",
                "description": f"{r.get('resource_type', 'Unknown')}: {gap_pct:.0f}% resource gap — needed {needed:.0f}, have {used:.0f}, missing {gap:.0f} {unit}",
                "severity": severity,
                "affected_tasks": [],
                "evidence": f"Needed={needed:.0f} {unit}, Currently Used={used:.0f} {unit}, Gap={gap:.0f} ({gap_pct:.1f}%)",
            })

        # ══════════════════════════════════════════════
        # 2. SCHEDULE RISK DETECTION
        # ══════════════════════════════════════════════
        for t in tasks:
            status = str(t.get("current_status", "")).lower().strip()
            task_name = t.get("task_name", "Unknown")

            if status in ("delayed", "blocked"):
                logger.info(f"[RiskAssessment] Schedule risk: '{task_name}' is {status}")
                detected_risks.append({
                    "category": "schedule",
                    "description": f"Task '{task_name}' has status '{status}' — {'already behind schedule' if status == 'delayed' else 'cannot proceed due to blocker'}",
                    "severity": "high",
                    "affected_tasks": [task_name],
                    "evidence": f"Task status = {status}, planned: {t.get('start_date', '?')} to {t.get('end_date', '?')}",
                })

        # ══════════════════════════════════════════════
        # 3. DEPENDENCY RISK DETECTION
        # ══════════════════════════════════════════════
        for d in dependencies:
            dep_status = str(d.get("status", "")).lower().strip()
            dep_name = d.get("dependency_name", "Unknown")
            dep_type = str(d.get("dependency_type", "internal")).lower()
            blocking = d.get("blocking_tasks", [])
            if isinstance(blocking, str):
                try:
                    blocking = json.loads(blocking)
                except:
                    blocking = [blocking] if blocking else []

            if dep_status == "resolved":
                continue

            logger.info(f"[RiskAssessment] Dependency risk: '{dep_name}' is {dep_status} ({dep_type}), blocks {len(blocking)} tasks")

            if dep_status == "blocked":
                severity = "critical" if dep_type == "external" else "high"
            elif dep_status == "pending":
                severity = "high" if dep_type == "external" else "medium"
            else:
                severity = "medium"

            if len(blocking) >= 3:
                severity = "critical"
            elif len(blocking) >= 2 and severity not in ("critical",):
                severity = "high"

            detected_risks.append({
                "category": "dependency",
                "description": f"Dependency '{dep_name}' is {dep_status} ({dep_type}) — blocking {len(blocking)} task(s): {', '.join(blocking) if blocking else 'none specified'}",
                "severity": severity,
                "affected_tasks": blocking,
                "evidence": f"Status={dep_status}, Type={dep_type}, Blocks: {', '.join(blocking) if blocking else 'none'}",
            })

        # ══════════════════════════════════════════════
        # 4. BUDGET TRAJECTORY
        # ══════════════════════════════════════════════
        for r in resources:
            if str(r.get("unit", "")).upper() != "USD":
                continue

            needed = self._safe_float(r.get("needed", 0))
            used = self._safe_float(r.get("currently_used", 0))

            if needed <= 0:
                continue

            consumed_pct = (used / needed) * 100
            total_tasks = len(tasks)
            completed = len([t for t in tasks if str(t.get("current_status", "")).lower() == "completed"])
            progress_pct = (completed / total_tasks * 100) if total_tasks > 0 else 0
            overspend = consumed_pct - progress_pct

            logger.info(f"[RiskAssessment] Budget: {consumed_pct:.1f}% spent at {progress_pct:.1f}% completion, overspend={overspend:.1f}%")

            if overspend <= 0:
                continue

            if overspend > 20:
                severity = "high"
            elif overspend > 10:
                severity = "medium"
            else:
                severity = "low"

            detected_risks.append({
                "category": "budget",
                "description": f"Budget overspend: {consumed_pct:.1f}% of budget consumed at {progress_pct:.1f}% project completion — spending {overspend:.1f}% ahead of progress",
                "severity": severity,
                "affected_tasks": [],
                "evidence": f"Spent ${used:,.0f} of ${needed:,.0f} ({consumed_pct:.1f}%), project {progress_pct:.1f}% complete, overspend rate {overspend:.1f}%",
            })

        # ══════════════════════════════════════════════
        # RESULTS
        # ══════════════════════════════════════════════
        logger.info(f"[RiskAssessment] Total detected risks: {len(detected_risks)}")
        # ── 1e. MINIMUM RISK SCAN ───────────────────
        # Even if no gaps/blocks, check for warning signs
        if not detected_risks:
            # Check: any tasks not started that should have started by now?
            from datetime import datetime, date
            today = datetime.now().date()
            for t in tasks:
                status = str(t.get("current_status", "")).lower()
                if status == "not_started":
                    try:
                        start = t.get("start_date", "")
                        if isinstance(start, str) and start:
                            start_date = datetime.strptime(start, "%Y-%m-%d").date()
                            if start_date < today:
                                detected_risks.append({
                                    "category": "schedule",
                                    "description": f"Task '{t.get('task_name', 'Unknown')}' was planned to start {start} but status is still 'not_started'",
                                    "severity": "medium",
                                    "affected_tasks": [t.get("task_name", "Unknown")],
                                    "evidence": f"Start date {start} is in the past, status remains not_started",
                                })
                    except (ValueError, TypeError):
                        pass

            # Check: any dependencies that are not resolved?
            for d in dependencies:
                dep_status = str(d.get("status", "")).lower()
                if dep_status not in ("resolved", ""):
                    dep_name = d.get("dependency_name", "Unknown")
                    detected_risks.append({
                        "category": "dependency",
                        "description": f"Dependency '{dep_name}' is not yet resolved (status: {dep_status})",
                        "severity": "low",
                        "affected_tasks": d.get("blocking_tasks", []),
                        "evidence": f"Status = {dep_status}",
                    })
                    
        if not detected_risks:
            return {
                "internal_risks": [],
                "internal_summary": "No significant internal risks detected.",
                "internal_risk_score": 0
            }

        # ══════════════════════════════════════════════
        # ENHANCE WITH RAG + LLM
        # ══════════════════════════════════════════════

        # Try to enhance with RAG context and LLM
        try:
            rag_context = self.get_rag_context(
                "project delays resource shortage dependency failure budget overrun"
            )

            market_summary = "No market analysis available."
            if market_risks:
                points = [f"- {mr.get('factor', '')} ({mr.get('likelihood', '')})" for mr in market_risks[:5] if mr.get('factor')]
                if points:
                    market_summary = "Market Analysis Agent found:\n" + "\n".join(points)

            prompt = f"""You are an internal risk analyst.

I have ALREADY detected these risks from project data. Your job is to improve the descriptions
using company history context. DO NOT remove any risks. DO NOT add new ones.

COMPANY HISTORY:
{rag_context}

MARKET CONTEXT:
{market_summary}

DETECTED RISKS:
{json.dumps(detected_risks, indent=2, default=str)}

For each risk, improve the description and evidence by referencing company history where relevant.
Keep my severity ratings unless history strongly justifies changing them.

Respond ONLY with valid JSON:
{{
  "internal_risks": [
    {{
      "category": "resource | schedule | dependency | budget",
      "description": "Enhanced description with company history context",
      "severity": "low | medium | high | critical",
      "affected_tasks": ["task names"],
      "evidence": "Original data points + relevant company history"
    }}
  ]
}}
"""

            data = self.call_llm_json(prompt)
            llm_risks = data.get("internal_risks", [])

            if llm_risks and len(llm_risks) >= len(detected_risks):
                # LLM produced good output — use it
                cleaned = []
                for r in llm_risks:
                    severity = str(r.get("severity", "medium")).lower()
                    if severity not in ("low", "medium", "high", "critical"):
                        severity = "medium"
                    cleaned.append({
                        "category": str(r.get("category", "general")).lower(),
                        "description": r.get("description", ""),
                        "severity": severity,
                        "affected_tasks": r.get("affected_tasks", []),
                        "evidence": r.get("evidence", ""),
                    })
                logger.info(f"[RiskAssessment] Using LLM-enhanced output: {len(cleaned)} risks")
                detected_risks = cleaned
            else:
                logger.warning(f"[RiskAssessment] LLM returned {len(llm_risks)} risks (expected {len(detected_risks)}), using rule-based output")

        except Exception as e:
            logger.error(f"[RiskAssessment] LLM enhancement failed: {e}, using rule-based output")

        # ══════════════════════════════════════════════
        # SCORE CALCULATION
        # ══════════════════════════════════════════════
        severity_weights = {"low": 2, "medium": 5, "high": 8, "critical": 12}
        total_score = sum(severity_weights.get(r.get("severity", "medium"), 5) for r in detected_risks)
        overall_score = min(total_score, 25)

        crit = sum(1 for r in detected_risks if r.get("severity") == "critical")
        high = sum(1 for r in detected_risks if r.get("severity") == "high")
        med = sum(1 for r in detected_risks if r.get("severity") == "medium")
        low = sum(1 for r in detected_risks if r.get("severity") == "low")

        logger.info(f"[RiskAssessment] Final: {len(detected_risks)} risks, score={overall_score}/25 ({crit}C {high}H {med}M {low}L)")

        return {
            "internal_risks": detected_risks,
            "internal_summary": f"{len(detected_risks)} internal risks: {crit} critical, {high} high, {med} medium, {low} low.",
            "internal_risk_score": overall_score
        }
