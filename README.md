# HealthTrack

HealthTrack is a web application where patients log symptoms, track how severity changes over time, and share their records with their doctors.

Users can register, log in, and log out. Patients can log batches of symptom entries, review, filter, edit, and delete them, and follow a symptom's severity on a chart. Doctor sharing is not built yet. See [DECISIONS.md](DECISIONS.md) for the architecture and scope.

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

### Symptoms

All symptom routes need `Authorization: Bearer <token>` from a patient. They return 401 without a valid token and 403 for a doctor. Each route only ever reads or changes the authenticated patient's own entries, and another patient's entry returns the same 404 as one that does not exist.

| Endpoint | Success | Failure |
|---|---|---|
| `GET /api/symptoms` | 200 `{"entries": [...]}`, newest occurrence first | 422 invalid filters |
| `GET /api/symptoms/names` | 200 `{"symptoms": [{"key": "...", "name": "..."}]}`, most recently logged first | |
| `GET /api/symptoms/trends` | 200 with daily maximums | 422 invalid filters or no `symptom` |
| `POST /api/symptoms/batch` | 201 `{"entries": [...]}` | 422, and nothing is saved |
| `PATCH /api/symptoms/{entry_id}` | 200 with the updated entry | 404 not found; 422, and nothing changes |
| `DELETE /api/symptoms/{entry_id}` | 204 with no body | 404 not found |

`GET /api/symptoms` and `GET /api/symptoms/trends` accept these query parameters:

| Parameter | Meaning |
|---|---|
| `symptom` | Matches case and spacing variants. Optional for history, required for trends |
| `start_date`, `end_date` | Optional and inclusive, in `YYYY-MM-DD` format |

#### Trends

`GET /api/symptoms/trends?symptom=headache&start_date=2026-01-01` returns one point per day that has entries, oldest first:

```json
{
  "symptom_key": "headache",
  "points": [
    { "date": "2026-01-15", "max_severity": 8, "entry_count": 3 },
    { "date": "2026-01-18", "max_severity": 4, "entry_count": 1 }
  ]
}
```

Days without entries have no point. The chart shows them as breaks in the line, so nothing is plotted for a day that was not logged.

#### Editing

`PATCH` accepts any of `symptom_name`, `occurred_on`, `severity`, and `notes`, using the same validation as new entries. Fields left out keep their values, and `"notes": null` clears the notes. Errors use the `field` and `message` format, without an `entry` key.

#### Creating a batch

`POST /api/symptoms/batch` saves 1–20 entries. The batch is all-or-nothing: if any entry is invalid, none are saved.

```json
{
  "entries": [
    { "symptom_name": "Headache", "occurred_on": "2026-03-09", "severity": 6, "notes": "After lunch" },
    { "symptom_name": "Sore throat", "occurred_on": "2026-03-09", "severity": 3 }
  ]
}
```

Entry errors use zero-based indices, and every invalid entry is reported in one response:

```json
{
  "detail": "Validation failed",
  "errors": [
    { "entry": 1, "field": "severity", "message": "Severity must be between 1 and 10" },
    { "entry": 3, "field": "occurred_on", "message": "Date cannot be in the future" }
  ]
}
```

Errors about the batch as a whole, such as its size, have no `entry` key. The patient always comes from the token, and a request that supplies `patient_id` is rejected.

### Health

| Endpoint | Success | Failure |
|---|---|---|
| `GET /api/health` | 200 `{"status": "ok", "service": "healthtrack-api"}` | API is not running |
| `GET /api/health/db` | 200 `{"status": "ok", "database": "connected"}` | 503 `{"status": "error", "database": "unavailable"}` |
