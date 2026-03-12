import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hashlib
import json
import shutil
import logging
from fastapi import FastAPI, Request, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse

from config import UPLOAD_DIR
from models.schemas import ProjectPlanInput
from utils.file_parser import parse_upload
from database.project_db import init_db, save_project, get_project, list_projects, save_report, get_latest_report
from database.chroma_store import ingest_company_history, query_company_history
from agents.orchestrator import AgentOrchestrator
from agents.base_agent import BaseAgent

# ── Setup ───────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(name)-28s  %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="RiskIntelligence", version="2.0.0")
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates"))
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs("data", exist_ok=True)

orchestrator = AgentOrchestrator()
chat_agent = BaseAgent("ChatConsultant")


# ── Startup ─────────────────────────────────────────────────────────

@app.on_event("startup")
def startup():
    init_db()
    history_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "company_history.json")
    if os.path.exists(history_path):
        ingest_company_history(history_path)
        logger.info("Company history loaded into ChromaDB.")


# ── Pages ───────────────────────────────────────────────────────────

@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# ── API: Project Management ─────────────────────────────────────────

@app.post("/api/projects")
async def create_project(plan: ProjectPlanInput):
    """Save a structured project plan into SQLite and return the project ID."""
    # Hash the actual data to catch duplicate manual saves
    plan_json = json.dumps(plan.model_dump(mode='json'), sort_keys=True)
    data_hash = hashlib.sha256(plan_json.encode('utf-8')).hexdigest()
    
    from database.project_db import get_cached_project, save_file_cache
    cached_project_id = get_cached_project(data_hash)
    
    if cached_project_id:
        return {"project_id": cached_project_id, "message": f"Project '{plan.project_name}' loaded from cache."}
        
    project_id = save_project(plan)
    save_file_cache(data_hash, plan.project_name, "manual_entry", project_id)
    
    return {"project_id": project_id, "message": f"Project '{plan.project_name}' saved."}

@app.post("/api/upload")
async def upload_project_file(file: UploadFile = File(...)):
    allowed_extensions = (".json", ".csv", ".xlsx", ".xls", ".pdf")
    filename = file.filename.lower()
    
    if not any(filename.endswith(ext) for ext in allowed_extensions):
        return JSONResponse(status_code=400, content={
            "error": f"Unsupported file type. Please upload: {', '.join(allowed_extensions)}"
        })
        
    try:
        file_bytes = await file.read()
        
        # 1. Hash the file contents (The Fingerprint)
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        
        # 2. Check if this exact file was uploaded before
        from database.project_db import get_cached_project, save_file_cache, get_latest_report
        cached_project_id = get_cached_project(file_hash)
        
        if cached_project_id:
            # File already analyzed — return cached report
            existing_report = get_latest_report(cached_project_id)
            return {
                "project_id": cached_project_id,
                "project_name": f"Cached — {file.filename}",
                "cached": True,
                "report": existing_report,
                "message": f"File '{file.filename}' was already analyzed (Project ID {cached_project_id}). Returning cached report."
            }
            
        # 3. Save the original file to disk
        save_path = os.path.join(UPLOAD_DIR, f"{file_hash}_{file.filename}")
        with open(save_path, "wb") as f:
            f.write(file_bytes)
            
        # 4. Parse the file
        llm = None
        if filename.endswith(".pdf"):
            llm = chat_agent.llm
            
        from utils.file_parser import parse_upload
        parsed = parse_upload(file.filename, file_bytes, llm=llm)
        
        # 5. Validate and save project
        from models.schemas import ProjectPlanInput
        from database.project_db import save_project
        plan = ProjectPlanInput(**parsed)
        project_id = save_project(plan)
        
        # 6. Save file hash → project mapping
        save_file_cache(file_hash, file.filename, save_path, project_id)
        
        return {
            "project_id": project_id,
            "project_name": plan.project_name,
            "parsed_data": parsed,
            "cached": False,
            "message": f"File '{file.filename}' parsed and saved as project ID {project_id}."
        }
        
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
    except Exception as e:
        logger.error(f"Upload error: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": f"Failed to parse file: {str(e)}"})


@app.get("/api/projects")
async def get_projects():
    """List all saved projects."""
    return {"projects": list_projects()}


@app.get("/api/projects/{project_id}")
async def get_project_detail(project_id: int):
    """Get full project details."""
    try:
        project = get_project(project_id)
        return {"project": project}
    except Exception as e:
        return JSONResponse(status_code=404, content={"error": str(e)})


# ── API: Risk Analysis ──────────────────────────────────────────────

@app.post("/api/analyze/{project_id}")
async def analyze_project(project_id: int, force: bool = False):
    """Run the 4-agent pipeline on a saved project and return the risk report."""
    try:
        project = get_project(project_id)
    except Exception:
        return JSONResponse(status_code=404, content={"error": "Project not found."})

    # --- NEW: Check if report already exists! ---
    if not force:
        existing_report = get_latest_report(project_id)
        if existing_report:
            return {"report": existing_report, "cached": True}
    # --------------------------------------------

    try:
        report = orchestrator.run(project)
        save_report(project_id, json.dumps(report, default=str))
        return {"report": report}

    except Exception as e:
        logger.error(f"Agent pipeline error: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": f"Analysis failed: {str(e)}"})


@app.get("/api/report/{project_id}")
async def get_report(project_id: int):
    """Retrieve the latest risk report for a project."""
    report = get_latest_report(project_id)
    if not report:
        return JSONResponse(status_code=404, content={"error": "No report found. Run analysis first."})
    return {"report": report}


# ── API: Chat ───────────────────────────────────────────────────────

@app.post("/api/chat")
async def chat(request: Request):
    """Conversational agent that answers questions using the report as context."""
    data = await request.json()
    user_message = data.get("message", "")
    project_id = data.get("project_id")

    report_context = ""
    if project_id:
        report = get_latest_report(project_id)
        if report:
            clean_report = {k: v for k, v in report.items() if not k.startswith("_")}
            report_context = json.dumps(clean_report, indent=2, default=str)[:3000]

    rag_context = chat_agent.get_rag_context(user_message, n_results=3)

    prompt = f"""You are an AI Risk Consultant for a leadership team. You have access to:

1. CURRENT RISK REPORT:
{report_context if report_context else "No report generated yet."}

2. COMPANY HISTORY (relevant excerpts):
{rag_context}

Answer the user's question professionally and specifically. Reference data from the 
report and company history where relevant. If asked about something not in the data,
say so clearly.

User's question: {user_message}
"""
    reply = chat_agent.call_llm(prompt)
    return {"reply": reply}


# ── API: RAG Management ─────────────────────────────────────────────

@app.post("/api/rag/ingest")
async def ingest_rag_data(request: Request):
    """Ingest additional company history records into ChromaDB."""
    data = await request.json()
    records = data.get("records", [])
    if not records:
        return JSONResponse(status_code=400, content={"error": "No records provided."})

    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(records, f)
        temp_path = f.name

    try:
        ingest_company_history(temp_path)
        return {"message": f"Ingested {len(records)} records into RAG knowledge base."}
    finally:
        os.unlink(temp_path)


@app.get("/api/rag/search")
async def search_rag(query: str, n: int = 5):
    """Search company history for relevant context."""
    results = query_company_history(query, n_results=n)
    return {"results": results}


# ── Run ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
