# RiskIntelligence v2.0 — Multi-Agent Project Risk Analyzer

A structured, multi-agent risk analysis system with RAG-powered company memory.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Backend                          │
│                                                             │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌─────────┐ │
│  │  Market   │──▶│   Risk   │──▶│   Risk   │──▶│  Risk   │ │
│  │ Analysis  │   │Assessment│   │Statement │   │Mitigation│ │
│  │  Agent    │   │  Agent   │   │  Agent   │   │  Agent  │ │
│  └────┬─────┘   └────┬─────┘   └──────────┘   └─────────┘ │
│       │              │                                      │
│       ▼              ▼                                      │
│  ┌─────────────────────────┐   ┌──────────────────────┐    │
│  │   ChromaDB (RAG)        │   │   SQLite (Projects)  │    │
│  │   Company History       │   │   Tasks / Resources  │    │
│  │   Past Incidents        │   │   Dependencies       │    │
│  │   Market Events         │   │   Risk Reports       │    │
│  └─────────────────────────┘   └──────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Agent Pipeline

Each agent receives the output of the previous agent(s), enabling inter-agent communication:

| # | Agent | Role | Input | Output |
|---|-------|------|-------|--------|
| 1 | **Market Analysis** | External risk scanning | Project data + RAG history | Market risks, external score |
| 2 | **Risk Assessment** | Internal risk evaluation | Project data + RAG + Agent 1 output | Internal risks, resource gaps |
| 3 | **Risk Statement** | Formal risk synthesis | Agent 1 + Agent 2 outputs | Scored risk statements (1-25) |
| 4 | **Risk Mitigation** | Actionable planning | Agent 3 output + RAG history | Mitigation actions, recommendations |

## Structured Input Format

Projects are submitted with three structured sections:

**Tasks:** task_name, start_date, end_date, current_status (not_started/in_progress/completed/blocked/delayed)

**Resources:** resource_type, needed, currently_used, unit (count/USD/hours)

**Dependencies:** dependency_name, type (internal/external), status (pending/resolved/blocked), blocking_tasks

## RAG Knowledge Base

The system uses ChromaDB to store and retrieve company history for context-aware analysis. Sample data includes 15 records covering past project successes and failures, market events, resource issues, vendor incidents, security breaches, and financial history.

## Setup

```bash
# 1. Clone and enter directory
cd risk_intelligence

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env and add your GROQ_API_KEY

# 4. Run
python main.py
# Server starts at http://localhost:8000
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Web dashboard |
| POST | `/api/projects` | Save a structured project plan |
| GET | `/api/projects` | List all projects |
| GET | `/api/projects/{id}` | Get project details |
| POST | `/api/analyze/{id}` | Run 4-agent analysis pipeline |
| GET | `/api/report/{id}` | Get latest report for a project |
| POST | `/api/chat` | Chat with the risk consultant |
| POST | `/api/rag/ingest` | Add records to company history |
| GET | `/api/rag/search?query=...` | Search company history |

## Tech Stack

- **Backend:** FastAPI + Python 3.11+
- **LLM:** Llama 3.3 70B via Groq (high-speed inference)
- **RAG Store:** ChromaDB (persistent vector DB)
- **Project DB:** SQLite (structured project data)
- **Frontend:** Vanilla HTML/CSS/JS + Tailwind
- **Agent Framework:** LangChain
