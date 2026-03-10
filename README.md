# RiskIntelligence

**A multi-agent AI system that analyzes project plans for risks using 4 specialized LLM agents, RAG-powered company memory, and structured data storage.**

Built with FastAPI, LangChain, Groq (Llama 3.3 70B), ChromaDB, and SQLite.

---

## What It Does

You feed it a project plan (as JSON, CSV, Excel, or PDF), and 4 AI agents work in sequence — each one passing its findings to the next — to produce a scored risk report with actionable mitigations.

**Agent Pipeline:**

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Agent 1    │────▶│   Agent 2    │────▶│   Agent 3    │────▶│   Agent 4    │
│   Market     │     │    Risk      │     │    Risk      │     │    Risk      │
│  Analysis    │     │  Assessment  │     │  Statements  │     │  Mitigation  │
└──────┬───────┘     └──────┬───────┘     └──────────────┘     └──────────────┘
       │                    │
       ▼                    ▼
┌─────────────────────────────────┐     ┌────────────────────┐
│   ChromaDB (RAG)                │     │   SQLite            │
│   Company history, past         │     │   Projects, tasks,  │
│   incidents, market events      │     │   resources, reports │
└─────────────────────────────────┘     └────────────────────┘
```

| Agent | Role | Receives | Produces |
|-------|------|----------|----------|
| **Market Analysis** | Scans external risks — market trends, regulatory changes, competitor moves | Project data + RAG history | Market risks with likelihood scores |
| **Risk Assessment** | Evaluates internal risks — schedule delays, resource gaps, dependency chains | Project data + RAG + Agent 1 output | Internal risks with severity ratings |
| **Risk Statement** | Synthesizes both into formal, numbered risk statements | Agent 1 + Agent 2 outputs | Scored risk statements (1–25 scale) |
| **Risk Mitigation** | Creates actionable mitigation plans referencing what worked historically | Agent 3 output + RAG history | Action plans with owners and timelines |

Each agent queries ChromaDB for relevant company history (past project failures, vendor incidents, financial data), so the analysis is grounded in what actually happened before — not just generic advice.

---

## Features

- **Structured Input** — Projects are stored with typed fields: tasks (name, dates, status), resources (needed vs. used), and dependencies (type, status, blocking tasks)
- **Multi-Format Upload** — Supports JSON, CSV, Excel (.xlsx), and PDF files. PDFs are parsed by the LLM into structured data
- **RAG Knowledge Base** — 15 sample company history records covering past project successes/failures, market events, vendor incidents, security breaches, and financial data. Add your own via the API
- **Formatted Reports** — Structured JSON output with executive summary, risk scores (1–25), severity badges, and a PDF export
- **Chat Consultant** — A conversational agent that can answer follow-up questions about the report using both the risk analysis and company history as context
- **Persistent Storage** — Projects and reports saved in SQLite, company history in ChromaDB. Everything survives restarts

---

## Project Structure

```
risk_intelligence/
├── main.py                  # FastAPI app — all API endpoints
├── seed.py                  # Initialize DB + load sample data
├── config.py                # Environment config
├── .env.example             # Template for API keys
├── requirements.txt
│
├── agents/                  # The 4 AI agents
│   ├── base_agent.py        # Shared LLM + RAG utilities
│   ├── market_analysis_agent.py
│   ├── risk_assessment_agent.py
│   ├── risk_statement_agent.py
│   ├── risk_mitigation_agent.py
│   └── orchestrator.py      # Chains all 4 agents together
│
├── database/                # Data layer
│   ├── project_db.py        # SQLite — projects, tasks, reports
│   └── chroma_store.py      # ChromaDB — RAG vector store
│
├── models/
│   └── schemas.py           # Pydantic schemas for input/output
│
├── utils/
│   └── file_parser.py       # JSON/CSV/Excel/PDF parsing
│
├── data/
│   ├── company_history.json # Sample RAG data (15 records)
│   └── sample_project.json  # Sample project for testing
│
└── templates/
    └── index.html           # Frontend dashboard
```

---

## Quick Start

**Prerequisites:** Python 3.11+, a [Groq API key](https://console.groq.com/) (free tier works)

```bash
# Clone
git clone https://github.com/YOUR_USERNAME/risk-intelligence.git
cd risk-intelligence

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Open .env and paste your GROQ_API_KEY

# Seed the database with sample data
python seed.py

# Run
python main.py
```

Open `http://localhost:8000` in your browser.

---

## Usage

### Option 1: Upload a File

Upload a project plan as JSON, CSV, Excel, or PDF. The system parses it into structured data and runs the 4-agent pipeline.

- **Upload & Parse** — Extracts data and fills the form so you can review/edit before analyzing
- **Upload & Analyze** — Goes straight to the 4-agent pipeline

### Option 2: Manual Entry

Fill in the structured form with tasks, resources, and dependencies directly in the browser.

### Option 3: API

```bash
# Save a project
curl -X POST http://localhost:8000/api/projects \
  -H "Content-Type: application/json" \
  -d @data/sample_project.json

# Run analysis on project ID 1
curl -X POST http://localhost:8000/api/analyze/1

# Get the report
curl http://localhost:8000/api/report/1

# Chat with the consultant
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the biggest risk?", "project_id": 1}'

# Search company history
curl "http://localhost:8000/api/rag/search?query=vendor+outage&n=3"
```

---

## Input Format

### Structured JSON

```json
{
  "project_name": "Project Phoenix",
  "project_description": "Payment gateway modernization",
  "tasks": [
    {
      "task_name": "Core Engine Development",
      "start_date": "2025-04-28",
      "end_date": "2025-07-18",
      "current_status": "in_progress",
      "description": "Build transaction processing layer"
    }
  ],
  "resources": [
    {
      "resource_type": "Backend Engineers",
      "needed": 6,
      "currently_used": 4,
      "unit": "count"
    }
  ],
  "dependencies": [
    {
      "dependency_name": "Stripe Connect v3 API",
      "dependency_type": "external",
      "status": "blocked",
      "blocking_tasks": ["Payment Provider Integration"]
    }
  ]
}
```

### CSV

Columns: `project_name`, `task_name`, `start_date`, `end_date`, `current_status`, `description`, `resource_type`, `needed`, `currently_used`, `unit`, `dependency_name`, `dependency_type`, `dep_status`, `blocking_tasks`

### Excel

Either a single sheet with the same columns as CSV, or multiple sheets named `tasks`, `resources`, `dependencies`.

### PDF

Any project document — the LLM extracts structured data from the text.

---

## RAG Knowledge Base

The system ships with 15 sample company history records in `data/company_history.json`. These cover:

- Past project failures (Atlas, Zenith) and successes (Meridian, Lighthouse)
- Market events (competitor mergers, regulatory changes, economic downturns)
- Resource issues (hiring freezes, skills gaps, contractor costs)
- Vendor incidents (outages, SLA penalties)
- Security breaches and financial summaries

The agents query these during analysis so they can say things like *"Based on Project Atlas in 2021, which had a similar dependency structure and overran by 58%, this project faces elevated schedule risk."*

**Add your own records:**

```bash
curl -X POST http://localhost:8000/api/rag/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "records": [
      {
        "id": "custom-001",
        "category": "project_failure",
        "year": 2024,
        "source": "postmortem",
        "text": "Project X failed because..."
      }
    ]
  }'
```

---

## Report Output

The final report includes:

| Section | Description |
|---------|-------------|
| **Executive Summary** | 3–4 sentence overview for leadership |
| **Overall Risk Score** | 1–25 (probability × impact) with severity badge |
| **Market Risks** | External factors with likelihood and evidence |
| **Internal Risks** | Schedule, resource, dependency, budget risks with affected tasks |
| **Risk Statements** | Formal numbered statements (RSK-001, RSK-002…) with individual scores |
| **Mitigation Plan** | Action steps, owners, priority, and timeline for each risk |
| **Recommendations** | Strategic recommendations for leadership |

Reports can be downloaded as PDF or copied as raw JSON.

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI + Python 3.11+ |
| LLM | Llama 3.3 70B via Groq |
| RAG Vector Store | ChromaDB |
| Project Database | SQLite |
| Agent Framework | LangChain |
| Frontend | HTML + Tailwind CSS + Vanilla JS |
| File Parsing | pypdf, openpyxl, csv |

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Web dashboard |
| `POST` | `/api/projects` | Save a structured project plan |
| `POST` | `/api/upload` | Upload and parse a file (JSON/CSV/Excel/PDF) |
| `GET` | `/api/projects` | List all saved projects |
| `GET` | `/api/projects/{id}` | Get full project details |
| `POST` | `/api/analyze/{id}` | Run the 4-agent analysis pipeline |
| `GET` | `/api/report/{id}` | Get the latest report for a project |
| `POST` | `/api/chat` | Chat with the risk consultant |
| `POST` | `/api/rag/ingest` | Add records to the RAG knowledge base |
| `GET` | `/api/rag/search?query=...` | Search company history |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | — | **Required.** Your Groq API key |
| `LLM_MODEL` | `llama-3.3-70b-versatile` | LLM model to use |
| `LLM_TEMPERATURE` | `0.2` | LLM temperature |
| `SQLITE_DB_PATH` | `data/projects.db` | SQLite database location |
| `CHROMA_PERSIST_DIR` | `data/chroma_db` | ChromaDB storage location |

---

## Roadmap

- [ ] AWS deployment (App Runner / Lambda)
- [ ] Multi-user authentication
- [ ] Scheduled re-analysis with email alerts
- [ ] Dashboard with historical risk score trends
- [ ] Additional LLM provider support (OpenAI, Anthropic)
- [ ] Jira / Asana integration for live project data

---

## License

MIT
