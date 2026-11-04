# HealthTrack

HealthTrack is a web application where patients log symptoms, track how severity changes over time, and share their records with their doctors.

The database schema and authentication are in place: users can register, log in, and log out. Symptom tracking and doctor sharing are not built yet. See [DECISIONS.md](DECISIONS.md) for the architecture and scope.

## Prerequisites

- Python 3.12
- Node.js 20.19+, 22.13+, or 24+ (tested with 24) and npm
- Docker with Docker Compose

## Setup

Commands are shown for Windows PowerShell. On macOS or Linux, use `source venv/bin/activate` and `cp` instead of `Copy-Item`.

### 1. Start PostgreSQL

From the repository root:

```powershell
docker compose up -d --wait
```

The database listens on `127.0.0.1:5432`. Stop it with `docker compose stop`.

### 2. Run the backend

From `backend/`:

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Paste the printed value after `JWT_SECRET=` in `backend/.env`. The app and Alembic both refuse to start without it. Then apply the migrations and start the API:

```powershell
alembic upgrade head
uvicorn app.main:create_app --factory --reload --port 8001
```

Check the API at <http://localhost:8001/api/health> and the database connection at <http://localhost:8001/api/health/db>. Interactive API docs are at <http://localhost:8001/docs>.

The API uses port 8001 because Docker Desktop can occupy port 8000.

### 3. Run the frontend

From `frontend/`, in a second terminal:

```powershell
npm ci
Copy-Item .env.example .env
npm run dev
```

Open <http://localhost:5173>. The status indicator should show "API is running", and you can create an account.

## Migrations

From `backend/`, with the virtual environment active:

```powershell
alembic upgrade head     # Apply all migrations
alembic current          # Show the applied revision
alembic check            # Report model changes that have no migration
alembic revision --autogenerate -m "describe the change"
```

`alembic check` does not compare CHECK constraints, so changes to those need a hand-written migration.

`alembic downgrade base` drops every table and permanently deletes all data. Use it only on a local database you can recreate.

## Configuration

| File | Variable | Purpose |
|---|---|---|
| `backend/.env` | `DATABASE_URL` | PostgreSQL connection URL |
| `backend/.env` | `CORS_ORIGINS` | Comma-separated allowed origins; wildcards are rejected |
| `backend/.env` | `JWT_SECRET` | Token signing secret, at least 32 characters; required |
| `backend/.env` | `JWT_ALGORITHM` | `HS256` (default), `HS384`, or `HS512` |
| `frontend/.env` | `VITE_API_BASE_URL` | Base URL of the API, applied when Vite starts or builds |

The `.env.example` files contain local placeholders only. Do not commit real `.env` files.

## Tests and linting

From `backend/`, with the virtual environment active:

```powershell
pytest                  # Unit and API tests; no database needed
pytest -m integration   # Tests that need the running PostgreSQL
pytest -m ""            # Everything
ruff check .
ruff format --check .
```

Integration tests create a temporary `healthtrack_test` database from the real migrations and drop it afterwards, so they do not touch your development data.

From `frontend/`:

```powershell
npm run lint
npm run build
```

## API endpoints

### Authentication

| Endpoint | Success | Failure |
|---|---|---|
| `POST /api/auth/register` | 201 with the user | 409 email already registered; 422 validation errors |
| `POST /api/auth/login` | 200 `{"access_token": "...", "token_type": "bearer"}` | 401 `{"detail": "Invalid email or password"}`; 422 validation errors |
| `GET /api/auth/me` | 200 with the user; needs `Authorization: Bearer <token>` | 401 missing, invalid, or expired token |

Validation errors use one format:

```json
{
  "detail": "Validation failed",
  "errors": [{ "field": "password", "message": "String should have at least 8 characters" }]
}
```

### Health

| Endpoint | Success | Failure |
|---|---|---|
| `GET /api/health` | 200 `{"status": "ok", "service": "healthtrack-api"}` | API is not running |
| `GET /api/health/db` | 200 `{"status": "ok", "database": "connected"}` | 503 `{"status": "error", "database": "unavailable"}` |
