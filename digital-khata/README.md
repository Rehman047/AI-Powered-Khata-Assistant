# Digital Khata Assistant (Week 1 Scaffold)

This folder contains the Week 1 foundation for the Digital Khata Assistant:

- FastAPI app scaffold
- Sync SQLAlchemy PostgreSQL connection
- Customers and transactions models with constraints and indexes
- Pydantic schemas for API data shapes
- Placeholder routers and service stubs

## 1) Create and activate virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2) Configure environment variables

Copy `.env.example` to `.env` and set values:

```bash
cp .env.example .env
```

Required keys in `.env`:

- `DATABASE_URL` (PostgreSQL URL)
- `GROQ_API_KEY` (starts with `gsk_`)
- `APP_HOST` (default: `http://localhost:8000`)
- `SECRET_KEY` (long random secret)
- `DEBUG` (`true`/`false`)

## 3) Run the app

```bash
uvicorn app.main:app --reload
```

Open docs at:

- `http://localhost:8000/docs`

## 4) Verify tables in PostgreSQL

After app startup, check tables:

```sql
SELECT tablename
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN ('customers', 'transactions');
```

Check indexes and constraints as needed from `psql` (`\d+ customers`, `\d+ transactions`).
