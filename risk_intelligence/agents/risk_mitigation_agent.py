import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from agents.base_agent import BaseAgent


class RiskMitigationAgent(BaseAgent):

    def __init__(self):
        super().__init__("RiskMitigationAgent")

    def analyze(self, input_data: dict) -> dict:
        project = input_data.get("project", {})
        risk_statements = input_data.get("risk_statements", [])

        project_text = self.format_project_context(project)

        # Targeted RAG: query for EACH risk separately for better matches
        rag_sections = []
        for rs in risk_statements[:6]:  # Limit to top 6 to save tokens
            title = rs.get("title", "")
            category = rs.get("impact_area", "")
            query = f"mitigation strategy for {title} {category} project recovery"

            # Pull from success stories and past mitigations
            context = self.get_rag_context(
                query,
                n_results=2,
                categories=["project_success", "project_failure", "vendor_risk", "resource_issue"]
            )
            if context and "No relevant" not in context:
                rag_sections.append(f"For {rs.get('risk_id', '?')} ({title}):\n{context}")

        rag_context = "\n\n===\n\n".join(rag_sections) if rag_sections else "No relevant company history found."

        prompt = f"""You are a Risk Mitigation Specialist for IT/software projects.

PROJECT:
{project_text}

RISK STATEMENTS TO MITIGATE:
{json.dumps(risk_statements, indent=2, default=str)}

COMPANY HISTORY — RELEVANT PAST STRATEGIES:
{rag_context}

FOR EACH risk_id, create a mitigation plan following these rules:

RULES:
1. Every action step must be SPECIFIC — include WHO does WHAT by WHEN
   BAD:  "Improve resource allocation"
   GOOD: "Post a Senior Backend Engineer job listing on LinkedIn within 3 business days"
   
2. Every mitigation MUST reference either:
   - A specific number from the project data (gap %, dates, resource counts), OR
   - A specific historical precedent from company history
   If you cannot cite either → mark confidence as "low"
   
3. Priority must match the risk severity:
   - critical/high risk → priority must be "critical" or "high"
   - medium risk → priority "medium"
   - low risk → priority "low"
   
4. Timeline must be realistic:
   - "Immediate" = can be done today/this week
   - "1-2 weeks" = needs some coordination
   - "1 month" = needs hiring, procurement, or approval
   - "long-term" = organizational change

5. Include a "rationale" field explaining WHY this strategy will work,
   referencing what happened in similar past situations

6. DO NOT suggest:
   - "Monitor the situation" (not actionable)
   - "Establish a risk team" (too vague)
   - "Improve communication" (meaningless)

Respond ONLY with valid JSON:
{{
  "mitigation_plan": [
    {{
      "risk_id": "RSK-001",
      "strategy": "Clear strategy name",
      "action_steps": [
        "Step 1: [WHO] does [WHAT] by [WHEN]",
        "Step 2: [WHO] does [WHAT] by [WHEN]",
        "Step 3: [WHO] does [WHAT] by [WHEN]"
      ],
      "owner": "Specific role (Project Manager, CTO, DevOps Lead, HR, etc.)",
      "priority": "critical | high | medium | low",
      "timeline": "Immediate | 1-2 weeks | 1 month | long-term",
      "rationale": "Why this will work, citing project data or company history",
      "confidence": "high | low"
    }}
  ],
  "recommendations": [
    "Strategic recommendation with specific measurable action"
  ]
}}
"""

        data = self.call_llm_json(prompt)

        cleaned_plan = []
        for m in data.get("mitigation_plan", []):
            # Validate: must have action steps
            steps = m.get("action_steps", [])
            if not steps:
                steps = ["Define and execute mitigation strategy"]

            cleaned_plan.append({
                "risk_id": m.get("risk_id", ""),
                "strategy": m.get("strategy", ""),
                "action_steps": steps,
                "owner": m.get("owner", "Project Manager"),
                "priority": (m.get("priority", "medium") or "medium").lower(),
                "timeline": m.get("timeline", "1-2 weeks"),
                "rationale": m.get("rationale", ""),
                "confidence": m.get("confidence", "low"),
            })

        # Fallback
        if not cleaned_plan and risk_statements:
            for rs in risk_statements:
                cleaned_plan.append({
                    "risk_id": rs.get("risk_id", "RSK-001"),
                    "strategy": f"Address {rs.get('title', 'identified risk')}",
                    "action_steps": [
                        "Assign a dedicated owner for this risk within 48 hours",
                        "Document current status and blockers in the project tracker",
                        "Schedule a review meeting within 1 week to assess progress"
                    ],
                    "owner": "Project Manager",
                    "priority": rs.get("severity", "medium"),
                    "timeline": "1-2 weeks",
                    "rationale": "Fallback mitigation — LLM did not generate specific strategy",
                    "confidence": "low",
                })

        return {
            "mitigation_plan": cleaned_plan,
            "recommendations": data.get("recommendations", [])
        }