"""
Parses uploaded project files (JSON, PDF, Excel, CSV) into structured data.

- JSON: Expected to match ProjectPlanInput schema directly.
- Excel/CSV: Expected columns — task_name, start_date, end_date, current_status, etc.
             Supports multiple sheets: 'tasks', 'resources', 'dependencies'.
- PDF: Extracts text, then uses the LLM to parse it into structured format.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import json
import csv
import io
import logging

logger = logging.getLogger(__name__)


# ── JSON Parser ─────────────────────────────────────────────────────

def parse_json(file_bytes: bytes) -> dict:
    """Parse a JSON file directly into project plan dict."""
    raw = json.loads(file_bytes.decode("utf-8"))
    return raw


# ── CSV Parser ──────────────────────────────────────────────────────

def parse_csv(file_bytes: bytes) -> dict:
    """
    Parse a CSV file. Expects at minimum these columns:
    task_name, start_date, end_date, current_status

    Optional columns:
    description, resource_type, needed, currently_used, unit,
    dependency_name, dependency_type, dep_status
    """
    text = file_bytes.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))
    rows = [row for row in reader]

    if not rows:
        raise ValueError("CSV file is empty.")

    # Normalize column names (lowercase, strip spaces)
    rows = [{k.strip().lower().replace(" ", "_"): v.strip() for k, v in row.items()} for row in rows]

    tasks = []
    resources = []
    dependencies = []

    for row in rows:
        # Tasks
        if row.get("task_name"):
            tasks.append({
                "task_name": row["task_name"],
                "start_date": row.get("start_date", "2025-01-01"),
                "end_date": row.get("end_date", "2025-12-31"),
                "current_status": row.get("current_status", "not_started"),
                "description": row.get("description", ""),
            })

        # Resources (if resource columns exist)
        if row.get("resource_type"):
            resources.append({
                "resource_type": row["resource_type"],
                "needed": float(row.get("needed", 0)),
                "currently_used": float(row.get("currently_used", 0)),
                "unit": row.get("unit", "count"),
            })

        # Dependencies (if dependency columns exist)
        if row.get("dependency_name"):
            dependencies.append({
                "dependency_name": row["dependency_name"],
                "dependency_type": row.get("dependency_type", "internal"),
                "status": row.get("dep_status", row.get("dependency_status", "pending")),
                "blocking_tasks": [t.strip() for t in row.get("blocking_tasks", "").split(",") if t.strip()],
            })

    project_name = rows[0].get("project_name", "Uploaded Project")

    return {
        "project_name": project_name,
        "project_description": rows[0].get("project_description", ""),
        "tasks": tasks,
        "resources": resources,
        "dependencies": dependencies,
    }


# ── Excel Parser ────────────────────────────────────────────────────

def parse_excel(file_bytes: bytes) -> dict:
    """
    Parse an Excel file. Supports two modes:
    1. Multi-sheet: Separate sheets named 'tasks', 'resources', 'dependencies'
    2. Single-sheet: All data in one sheet (same columns as CSV)
    """
    try:
        import openpyxl
    except ImportError:
        raise ImportError("Install openpyxl: pip install openpyxl")

    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True)
    sheet_names_lower = {s.lower(): s for s in wb.sheetnames}

    project_name = "Uploaded Project"
    project_description = ""
    tasks = []
    resources = []
    dependencies = []

    def sheet_to_dicts(sheet):
        """Convert a sheet into a list of dicts using first row as headers."""
        data = []
        headers = None
        for i, row in enumerate(sheet.iter_rows(values_only=True)):
            if i == 0:
                headers = [str(h).strip().lower().replace(" ", "_") if h else f"col_{j}" for j, h in enumerate(row)]
                continue
            if all(v is None for v in row):
                continue
            data.append({headers[j]: (str(v).strip() if v is not None else "") for j, v in enumerate(row) if j < len(headers)})
        return data

    # Multi-sheet mode
    if "tasks" in sheet_names_lower:
        task_rows = sheet_to_dicts(wb[sheet_names_lower["tasks"]])
        for row in task_rows:
            if row.get("task_name"):
                tasks.append({
                    "task_name": row["task_name"],
                    "start_date": row.get("start_date", "2025-01-01"),
                    "end_date": row.get("end_date", "2025-12-31"),
                    "current_status": row.get("current_status", "not_started"),
                    "description": row.get("description", ""),
                })
                if not project_name or project_name == "Uploaded Project":
                    project_name = row.get("project_name", project_name)

        if "resources" in sheet_names_lower:
            res_rows = sheet_to_dicts(wb[sheet_names_lower["resources"]])
            for row in res_rows:
                if row.get("resource_type"):
                    resources.append({
                        "resource_type": row["resource_type"],
                        "needed": float(row.get("needed", 0)),
                        "currently_used": float(row.get("currently_used", 0)),
                        "unit": row.get("unit", "count"),
                    })

        if "dependencies" in sheet_names_lower:
            dep_rows = sheet_to_dicts(wb[sheet_names_lower["dependencies"]])
            for row in dep_rows:
                if row.get("dependency_name"):
                    dependencies.append({
                        "dependency_name": row["dependency_name"],
                        "dependency_type": row.get("dependency_type", "internal"),
                        "status": row.get("dep_status", row.get("dependency_status", row.get("status", "pending"))),
                        "blocking_tasks": [t.strip() for t in row.get("blocking_tasks", "").split(",") if t.strip()],
                    })

    else:
        # Single-sheet mode — treat first sheet like CSV
        first_sheet = wb[wb.sheetnames[0]]
        all_rows = sheet_to_dicts(first_sheet)

        for row in all_rows:
            if row.get("task_name"):
                tasks.append({
                    "task_name": row["task_name"],
                    "start_date": row.get("start_date", "2025-01-01"),
                    "end_date": row.get("end_date", "2025-12-31"),
                    "current_status": row.get("current_status", "not_started"),
                    "description": row.get("description", ""),
                })
            if row.get("resource_type"):
                resources.append({
                    "resource_type": row["resource_type"],
                    "needed": float(row.get("needed", 0)),
                    "currently_used": float(row.get("currently_used", 0)),
                    "unit": row.get("unit", "count"),
                })
            if row.get("dependency_name"):
                dependencies.append({
                    "dependency_name": row["dependency_name"],
                    "dependency_type": row.get("dependency_type", "internal"),
                    "status": row.get("dep_status", row.get("status", "pending")),
                    "blocking_tasks": [t.strip() for t in row.get("blocking_tasks", "").split(",") if t.strip()],
                })

        if all_rows:
            project_name = all_rows[0].get("project_name", project_name)
            project_description = all_rows[0].get("project_description", "")

    wb.close()

    return {
        "project_name": project_name,
        "project_description": project_description,
        "tasks": tasks,
        "resources": resources,
        "dependencies": dependencies,
    }


# ── PDF Parser (uses LLM to extract structured data) ────────────────

def parse_pdf(file_bytes: bytes, llm=None) -> dict:
    """
    Extract text from PDF, then use the LLM to parse it into structured project data.
    If no LLM is provided, returns raw text in a minimal structure.
    """
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ImportError("Install pypdf: pip install pypdf")

    reader = PdfReader(io.BytesIO(file_bytes))
    full_text = ""
    for page in reader.pages:
        full_text += page.extract_text() + "\n"

    full_text = full_text.strip()
    if not full_text:
        raise ValueError("Could not extract text from PDF.")

    if llm is None:
        # Return a minimal project with the PDF text as description
        return {
            "project_name": "Uploaded PDF Project",
            "project_description": full_text[:2000],
            "tasks": [{"task_name": "Review uploaded document", "start_date": "2025-01-01", "end_date": "2025-12-31", "current_status": "not_started"}],
            "resources": [],
            "dependencies": [],
        }

    # Use LLM to extract structured data
    prompt = f"""Extract structured project data from this document. 
Return ONLY valid JSON matching this exact format:
{{
  "project_name": "Name of the project",
  "project_description": "Brief description",
  "tasks": [
    {{"task_name": "...", "start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD", "current_status": "not_started|in_progress|completed|blocked|delayed", "description": "..."}}
  ],
  "resources": [
    {{"resource_type": "...", "needed": 0, "currently_used": 0, "unit": "count|USD|hours"}}
  ],
  "dependencies": [
    {{"dependency_name": "...", "dependency_type": "internal|external", "status": "pending|resolved|blocked", "blocking_tasks": []}}
  ]
}}

If some data is not in the document, make reasonable inferences. 
Always include at least one task.

DOCUMENT TEXT:
{full_text[:4000]}
"""
    response = llm.invoke(prompt)
    raw = response.content.strip()

    # Clean markdown fences
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1]
    if raw.endswith("```"):
        raw = raw.rsplit("```", 1)[0]

    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        logger.warning("LLM could not parse PDF into structured data, using raw text.")
        return {
            "project_name": "Uploaded PDF Project",
            "project_description": full_text[:2000],
            "tasks": [{"task_name": "Review uploaded document", "start_date": "2025-01-01", "end_date": "2025-12-31", "current_status": "not_started"}],
            "resources": [],
            "dependencies": [],
        }


# ── Main Router ─────────────────────────────────────────────────────

def parse_upload(filename: str, file_bytes: bytes, llm=None) -> dict:
    """Route to the correct parser based on file extension."""
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

    if ext == "json":
        return parse_json(file_bytes)
    elif ext == "csv":
        return parse_csv(file_bytes)
    elif ext in ("xlsx", "xls"):
        return parse_excel(file_bytes)
    elif ext == "pdf":
        return parse_pdf(file_bytes, llm=llm)
    else:
        raise ValueError(f"Unsupported file format: .{ext}. Use JSON, CSV, Excel, or PDF.")
