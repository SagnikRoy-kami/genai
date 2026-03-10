import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import json
import logging
from langchain_groq import ChatGroq
from database.chroma_store import query_company_history
from config import GROQ_API_KEY, LLM_MODEL, LLM_TEMPERATURE

logger = logging.getLogger(__name__)


class BaseAgent:
    """Shared foundation for all risk analysis agents."""

    def __init__(self, name: str):
        self.name = name
        self.llm = ChatGroq(
            model_name=LLM_MODEL,
            groq_api_key=GROQ_API_KEY,
            temperature=LLM_TEMPERATURE,
        )

    def get_rag_context(self, query: str, n_results: int = 5) -> str:
        """Retrieve relevant company history from ChromaDB."""
        docs = query_company_history(query, n_results=n_results)
        if not docs:
            return "No company history available."
        chunks = []
        for d in docs:
            chunks.append(f"[{d['metadata'].get('category', '')} | {d['metadata'].get('year', '')}] {d['text']}")
        return "\n\n".join(chunks)

    def call_llm(self, prompt: str) -> str:
        """Invoke the LLM and return raw text."""
        logger.info(f"[{self.name}] Invoking LLM ...")
        response = self.llm.invoke(prompt)
        return response.content

    def call_llm_json(self, prompt: str) -> dict:
        """Invoke LLM expecting a JSON response. Falls back to raw text on parse failure."""
        raw = self.call_llm(prompt)
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning(f"[{self.name}] JSON parse failed, returning raw text.")
            return {"raw_response": raw}

    @staticmethod
    def format_project_context(project: dict) -> str:
        """Turn a project dict into a readable text block for prompts."""
        lines = [f"PROJECT: {project['name']}"]
        if project.get("description"):
            lines.append(f"Description: {project['description']}")

        lines.append("\n-- TASKS --")
        for t in project.get("tasks", []):
            lines.append(
                f"  {t['task_name']}  |  {t['start_date']} -> {t['end_date']}  |  Status: {t['current_status']}"
                + (f"  |  Note: {t['description']}" if t.get("description") else "")
            )

        lines.append("\n-- RESOURCES --")
        for r in project.get("resources", []):
            gap = r["needed"] - r["currently_used"]
            lines.append(
                f"  {r['resource_type']}: Needed={r['needed']} {r['unit']}, "
                f"Used={r['currently_used']} {r['unit']}, Gap={gap} {r['unit']}"
            )

        lines.append("\n-- DEPENDENCIES --")
        for d in project.get("dependencies", []):
            lines.append(
                f"  {d['dependency_name']} ({d['dependency_type']}) — Status: {d['status']}"
                + (f"  |  Blocks: {', '.join(d['blocking_tasks'])}" if d.get("blocking_tasks") else "")
            )

        return "\n".join(lines)
