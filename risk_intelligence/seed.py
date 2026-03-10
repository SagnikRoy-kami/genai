"""
Quick-start seed script.
Run once to initialize the database, ingest company history,
and load the sample project for testing.

Usage:
    python seed.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
from database.project_db import init_db, save_project
from database.chroma_store import ingest_company_history
from models.schemas import ProjectPlanInput


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))

    print("-- Initializing SQLite database ...")
    init_db()

    print("-- Ingesting company history into ChromaDB ...")
    history_path = os.path.join(base_dir, "data", "company_history.json")
    ingest_company_history(history_path)

    print("-- Loading sample project plan ...")
    sample_path = os.path.join(base_dir, "data", "sample_project.json")
    with open(sample_path) as f:
        raw = json.load(f)

    plan = ProjectPlanInput(**raw)
    project_id = save_project(plan)
    print(f"   Sample project saved with ID: {project_id}")

    print(f"\n   Setup complete! Start the server with:")
    print(f"   python main.py")
    print(f"\n   Then visit http://localhost:8000")
    print(f"   Or run analysis via API:")
    print(f"   curl -X POST http://localhost:8000/api/analyze/{project_id}")


if __name__ == "__main__":
    main()
