# Support Ticket AI

An AI-powered customer support ticket system that classifies incoming tickets, retrieves evidence from a company Help Centre, judges whether the issue can be answered safely, and either replies to the customer or escalates the ticket to a developer.

## Architecture
Customer Ticket → Classifier → Knowledge Retrieval → Judge → Decision → Reply / Escalate

## Structure
- `frontend/` — SupportAI dashboard
- `backend/` — FastAPI integration API
- `src/` — core AI pipeline
- `tickets/` — sample support tickets
- `help_centre/` — company knowledge base
- `tests/` — pipeline tests
- `agent.md` — agent rules
- `main.py` — run the pipeline

## Run
```bash
python main.py
python -m pytest
```

## Dashboard
```bash
cd frontend
python -m http.server 5500
```
Open http://localhost:5500.

## Backend
```bash
cd backend
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

The current AI implementation uses a deterministic MockLLM so it runs without an API key. The dashboard uses demo ticket data and the FastAPI service is the integration point for the live pipeline.

## Roadmap
- Production LLM integration
- Structured outputs and confidence thresholds
- RAG/vector retrieval
- PostgreSQL ticket storage
- Live dashboard/API integration
- Developer escalation notifications
