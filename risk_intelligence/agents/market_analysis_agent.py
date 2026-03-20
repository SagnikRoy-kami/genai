import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from agents.base_agent import BaseAgent


class MarketAnalysisAgent(BaseAgent):

    def __init__(self):
        super().__init__("MarketAnalysisAgent")

    def analyze(self, project: dict) -> dict:
        project_text = self.format_project_context(project)
        project_name = project.get('name') or project.get('project_name', 'Unknown')

        # Targeted RAG queries with category filtering
        rag_market = self.get_rag_context(
            f"market trends economic risks competitor activity for {project_name}",
            n_results=3,
            categories=["market_event", "client_risk", "financial_history"]
        )

        rag_vendor = self.get_rag_context(
            f"vendor risk supplier outage dependency failure",
            n_results=2,
            categories=["vendor_risk", "dependency_issue"]
        )

        rag_regulatory = self.get_rag_context(
            f"regulatory compliance legal risk audit",
            n_results=2,
            categories=["security_incident", "market_event"]
        )

        combined_rag = f"MARKET & ECONOMIC HISTORY:\n{rag_market}\n\nVENDOR HISTORY:\n{rag_vendor}\n\nREGULATORY HISTORY:\n{rag_regulatory}"

        prompt = f"""You are a Market Analysis Agent for IT/software projects.

COMPANY HISTORY:
{combined_rag}

PROJECT DATA:
{project_text}

TASK:
Analyze EXTERNAL risk factors for this project. External means things OUTSIDE the team's control.

ANALYSIS FRAMEWORK — evaluate each category:
1. VENDOR RISKS: Are there external dependencies on third-party vendors, APIs, or services? 
   → Check if project dependencies include external items
   → Check if company history shows vendor-related incidents
   
2. REGULATORY/COMPLIANCE: Does this project involve regulated areas (payments, health data, PII)?
   → Check project description and task names for compliance keywords
   → Check company history for regulatory incidents
   
3. ECONOMIC: Could economic conditions affect this project's budget, hiring, or timeline?
   → Check company history for economic impacts on similar projects
   
4. COMPETITIVE: Could competitor actions reduce this project's value?
   → Check company history for competitive pressure

STRICT RULES:
- ONLY flag risks you can support with evidence from the project data OR company history
- For each risk, you MUST cite which piece of evidence supports it
- If a category has no evidence → do NOT include it. Empty is better than invented.
- Assign likelihood based on evidence strength:
  - "high" = evidence in BOTH project data AND company history
  - "medium" = evidence in project data OR company history (not both)  
  - "low" = weak inference, no direct evidence
- Mark confidence: "high" if evidence-backed, "low" if inferred

Respond ONLY with valid JSON:
{{
  "market_risks": [
    {{
      "factor": "Specific risk name",
      "impact": "How exactly this impacts THIS project (not generic)",
      "likelihood": "high | medium | low",
      "evidence": "EXACT quote or reference from project data or company history that supports this",
      "confidence": "high | low"
    }}
  ],
  "market_summary": "2-3 sentences. State how many risks found and overall external posture.",
  "external_risk_score": <integer 1-10>
}}

NOTE: external_risk_score maximum is 10, not 25. This is just the external component.
"""
        result = self.call_llm_json(prompt)

        # Post-process: remove low-confidence risks with no evidence
        risks = result.get("market_risks", [])
        filtered = []
        for r in risks:
            evidence = r.get("evidence", "")
            if evidence and len(evidence) > 20:  # Must have substantive evidence
                filtered.append(r)
            elif r.get("confidence") == "high":
                filtered.append(r)
            # Drop risks with no evidence and low confidence

        result["market_risks"] = filtered
        
        # Cap external score
        ext_score = result.get("external_risk_score", 0)
        try:
            ext_score = min(int(ext_score), 10)
        except:
            ext_score = len(filtered) * 2
        result["external_risk_score"] = min(ext_score, 10)

        return result