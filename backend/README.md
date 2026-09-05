# Backend — AI Cybersecurity Mentor

FastAPI backend for the Personal AI Mentor project. See the root `README.md`
for full project context and architecture.

## Run

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Structure

```text
app/
├── api/          # Routers (versioned under /api/v1)
├── core/         # Config, security, dependencies, error handlers
├── db/           # MongoDB connection + collection registry
├── models/       # Domain models (placeholders until each feature lands)
├── schemas/      # Request/response schemas (placeholders until each feature lands)
├── services/     # Business logic, grouped by domain
├── utils/        # Logger, response helpers, misc utilities
└── main.py       # App entry point
```

## Tests

```bash
pytest tests/ -v
```
