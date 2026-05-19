# Getting started with nene2-python

In this tutorial you will run a Note CRUD API in under 5 minutes.

## Prerequisites

- Python 3.12 or later
- [uv](https://docs.astral.sh/uv/) installed
- Git

## 1. Clone the repository

```bash
git clone https://github.com/hideyukiMORI/nene2-python.git
cd nene2-python
```

## 2. Install dependencies

```bash
uv sync
```

## 3. Start the development server

```bash
uv run uvicorn src.example.app:app --reload --port 8080
```

Open `http://localhost:8080/docs` in your browser — Swagger UI is ready.

## 4. Try the API

```bash
# Create a note
curl -X POST http://localhost:8080/notes \
  -H "Content-Type: application/json" \
  -d '{"title": "My first note", "body": "Created with nene2-python"}'

# List notes
curl http://localhost:8080/notes
```

## 5. Run the tests

```bash
uv run pytest
```

All 167+ tests should pass.

## Next steps

- [Implement a new domain](first-domain.md) — walk through the full layer stack using the Tag domain
- [Configuration reference](../reference/configuration.md) — configure a real database or enable auth
