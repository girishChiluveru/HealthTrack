# HealthTrack

HealthTrack is a web app where patients log symptoms, track how severity changes over time, and share their records with their doctors. It is a prototype, so please use synthetic data only.

**Patients** can log symptoms in batches, review, filter, edit, and delete entries, chart one symptom or several together, export a PDF report, share with doctors, and generate optional AI insights.

**Doctors** get a read-only view of the patients who share with them, and can export those records.

See [DECISIONS.md](DECISIONS.md) for the architecture and the reasons behind it.

| Part | Technology | Local address |
|---|---|---|
| Frontend | React, Vite, Chart.js | <http://localhost:5173> |
| API | FastAPI, SQLAlchemy, Alembic | <http://localhost:8001> (docs at `/docs`) |
| Database | PostgreSQL 16 in Docker | `127.0.0.1:5432` |
| Database viewer | Adminer in Docker | <http://localhost:8080> |

## First-time setup

You need Python 3.12, Node.js 20.19+, 22.13+, or 24+, and Docker Desktop. Commands are for Windows PowerShell. On macOS or Linux, use `source venv/bin/activate` and `cp` instead of `Copy-Item`.

**1. Start the database and viewer.** Make sure Docker Desktop is running, then from the repository root:

```powershell
docker compose up -d --wait
```

**2. Set up the backend.** From `backend/`:

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Paste the printed value after `JWT_SECRET=` in `backend/.env`. The app refuses to start without it. Then create the tables:

```powershell
alembic upgrade head
```

**3. Set up the frontend.** From `frontend/`:

```powershell
npm ci
Copy-Item .env.example .env
```

**4. Load the demo data (optional).** From `backend/`, with the virtual environment active:

```powershell
python -m app.seed_demo
```

## Daily use

Start Docker Desktop, then use three terminals.

```powershell
# Terminal 1, repository root
docker compose up -d --wait

# Terminal 2, backend/
venv\Scripts\Activate.ps1
uvicorn app.main:create_app --factory --reload --port 8001

# Terminal 3, frontend/
npm run dev
```

Open <http://localhost:5173>. Stop the servers with Ctrl+C, and the containers with `docker compose stop`. Your data stays in a Docker volume.

The API uses port 8001 because Docker Desktop can occupy port 8000.

## Demo accounts

`python -m app.seed_demo` loads about 30 days of fictional records, relative to today. Every account uses the password `demo-password-1`.

| Account | Role | Shows |
|---|---|---|
| `mira.demo@example.com` | Patient | Seven symptoms with trends, days with no entry, several entries on one day, and an active share with the doctor below |
| `dr.lena.demo@example.com` | Doctor | Read-only access to Mira's records |
| `noah.demo@example.com` | Patient | A few entries shared with nobody, so the doctor cannot see them |

Run it again whenever you like. Each run resets these three accounts, including any entries you changed, and creates no duplicates. Other accounts are left alone.

It only runs when you ask. For a database that is not on `localhost` or `127.0.0.1`, see [Deployment](#deployment), because the password above is public and must never be used on a hosted database.

## Viewing the database

Open <http://localhost:8080> and log in with these values from `docker-compose.yml`:

| Field | Value |
|---|---|
| System | PostgreSQL |
| Server | `postgres` |
| Username | `healthtrack` |
| Password | `change-me-local-only` |
| Database | `healthtrack` |

Pick a table and choose **Select data** to browse it, or use **SQL command** to run a query. The Server is `postgres`, not `localhost`, because Adminer reaches the database over Docker's network.

| Table | Holds |
|---|---|
| `users` | Patients and doctors. `password_hash` holds an Argon2 hash, never the password |
| `symptom_entries` | One row per logged symptom |
| `doctor_access` | Sharing grants. A row with empty `revoked_at` is active |
| `alembic_version` | The applied migration |

For example, this shows each patient's entries:

```sql
SELECT u.name, e.occurred_on, e.symptom_name, e.severity, e.notes
FROM symptom_entries e
JOIN users u ON u.id = e.patient_id
ORDER BY e.occurred_on DESC, u.name;
```

Editing rows here skips the app's validation, so treat it as a place to look. Adminer listens on this computer only. From a terminal, `docker exec -it healthtrack-postgres psql -U healthtrack -d healthtrack` opens the same database.

## AI insights (optional)

The app works fully without this. It supports [Groq](https://console.groq.com/keys) and [OpenRouter](https://openrouter.ai/settings/keys). Create a free API key, add it to `backend/.env`, and restart the API:

```text
AI_PROVIDER=groq
AI_API_KEY=your-key
```

Then open **History and trends** and choose **Generate insights**. The key stays on the server.

| | Groq | OpenRouter |
|---|---|---|
| `AI_PROVIDER` | `groq` (default) | `openrouter` |
| Default model | `openai/gpt-oss-120b` | `openrouter/free` |
| Free limits | Shown in your [Groq account](https://console.groq.com/settings/limits) | 20 requests a minute, 50 a day |
| Keeping requests | Not retained by default, apart from up to 30 days of possible abuse and troubleshooting logs | Depends on the model's host. HealthTrack only allows hosts that do not collect data |

Groq is the default because its model is fixed and always returns the expected format. `openrouter/free` picks a free model at random, and the free list changes often. If you see "unavailable" on OpenRouter, set `AI_MODEL` to a specific free model that supports structured outputs, or switch to Groq. `AI_TIMEOUT_SECONDS` sets the wait, from the default 30 down.

- **What is sent:** per-symptom figures (name, counts, highest, lowest, averages, direction) and the length of the period. Notes, dates, names, and emails are not sent. Symptom names are free text, so whatever a patient typed there does leave the server.
- **What comes back:** observations about those figures, shown apart from general wellness tips. A filter drops statements that mention diagnoses, conditions, or medicines. It is a safety net with a fixed word list, so it cannot catch everything, and the output has not been clinically reviewed.
- **Without a key, or if the provider fails:** the panel says so and shows the figures calculated from the entries, labelled as not written by AI.
- **Limits:** at most 4 AI requests run at once, and any others get the fallback. There is no per-user limit, so add one before exposing this publicly.

To add another provider with an OpenAI-compatible API, add an entry to `PROVIDERS` in `backend/app/services/insights.py`.

## Project layout

```text
backend/app/
  main.py          App setup and error handling
  config.py        Settings from backend/.env
  models.py        Database tables
  schemas.py       Request and response validation
  api/             Routes: auth, symptoms, sharing, doctor, health
  services/        Business logic and queries
  authorization.py Doctor access checks
  seed_demo.py     Demo data
backend/migrations/ Database schema history
backend/tests/      Unit and integration tests
frontend/src/
  App.jsx          Chooses the logged-out, patient, or doctor view
  api/             Calls to the backend
  auth/            Login state
  components/      Screens and UI pieces
  symptoms/        Chart, date, and form logic
  reports/         PDF export
  theme.js         Light and dark theme
```

## Configuration

| File | Variable | Purpose |
|---|---|---|
| `backend/.env` | `DATABASE_URL` | PostgreSQL connection URL |
| `backend/.env` | `CORS_ORIGINS` | Comma-separated allowed origins; wildcards are rejected |
| `backend/.env` | `JWT_SECRET` | Token signing secret, at least 32 characters; required |
| `backend/.env` | `JWT_ALGORITHM` | `HS256` (default), `HS384`, or `HS512` |
| `backend/.env` | `AI_PROVIDER` | Optional; `groq` (default) or `openrouter` |
| `backend/.env` | `AI_API_KEY` | Optional; enables AI insights |
| `backend/.env` | `AI_MODEL` | Optional; overrides the provider's default model |
| `backend/.env` | `AI_TIMEOUT_SECONDS` | Optional; up to 30, which is the default |
| Your terminal | `DEMO_PASSWORD` | Private password for seeding a hosted database |
| `frontend/.env` | `VITE_API_BASE_URL` | Base URL of the API, applied when Vite starts or builds |

The `.env.example` files contain local placeholders only. Do not commit real `.env` files.

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

## Deployment

The app runs on three services. Create them in this order, because each one needs an address from the one before.

**1. Database on Supabase.** Create a project, then in the **Connect** dialog copy the **Session pooler** string, with port 5432 and a username like `postgres.yourproject`. The direct connection is IPv6 by default, and the transaction pooler does not support prepared statements. Add `?sslmode=require` to the end. In the project's Data API settings, turn off **Enable Data API**, because the app does not use it.

**2. API on Render.** Create a Web Service from this repository:

| Setting | Value |
|---|---|
| Root Directory | `backend` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn app.main:create_app --factory --host 0.0.0.0 --port $PORT` |
| Health Check Path | `/api/health` |

| Environment variable | Value |
|---|---|
| `PYTHON_VERSION` | `3.12.8` |
| `DATABASE_URL` | The Supabase string from step 1 |
| `JWT_SECRET` | A new secret, not your local one |
| `CORS_ORIGINS` | Your frontend URL, with no trailing slash. Set this after step 3 |
| `AI_PROVIDER`, `AI_API_KEY` | Optional |

**3. Migrate.** From `backend/`, with `DATABASE_URL` set to the Supabase string for that terminal only:

```powershell
$env:DATABASE_URL = "your-supabase-string"
alembic upgrade head
Remove-Item Env:DATABASE_URL
```

**4. Frontend on Vercel.** Import this repository, set **Root Directory** to `frontend`, and keep the detected Vite settings. Add `VITE_API_BASE_URL` with your Render URL. Views use the URL hash, so no rewrites are needed. Then set `CORS_ORIGINS` on Render to the Vercel production URL. Vercel preview URLs are different and will be blocked. `VITE_API_BASE_URL` is read at build time, so redeploy after changing it.

**5. Demo data (optional).** The seed refuses a hosted database unless you name its exact host and set your own password:

```powershell
$env:DATABASE_URL = "your-supabase-string"
$env:DEMO_PASSWORD = "a-private-password"
python -m app.seed_demo --remote-host your-pooler-host.pooler.supabase.com
Remove-Item Env:DATABASE_URL, Env:DEMO_PASSWORD
```

Check `https://your-api.onrender.com/api/health/db`, which should report that the database is connected.

Render's free plan sleeps after 15 minutes without traffic and takes about a minute to wake, so the first request after a pause is slow. The app starts waking it when the page loads. Supabase's free plan can pause an inactive project.

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
| `GET /api/symptoms` | 200 `{"entries": [...], "total": 120, "page": 1, "page_size": 25}`, newest occurrence first | 422 invalid filters or paging |
| `GET /api/symptoms/names` | 200 `{"symptoms": [{"key": "...", "name": "..."}]}`, most recently logged first | |
| `GET /api/symptoms/trends` | 200 with daily maximums | 422 invalid filters or no `symptom` |
| `POST /api/symptoms/batch` | 201 `{"entries": [...]}` | 422, and nothing is saved |
| `POST /api/symptoms/insights` with optional `symptom`, `start_date`, `end_date` | 200 with `status` (`ok`, `insufficient_data`, `not_configured`, or `unavailable`), figures, and `summary` | 422 invalid filters |
| `PATCH /api/symptoms/{entry_id}` | 200 with the updated entry | 404 not found; 422, and nothing changes |
| `DELETE /api/symptoms/{entry_id}` | 204 with no body | 404 not found |

`GET /api/symptoms` and `GET /api/symptoms/trends` accept these query parameters:

| Parameter | Meaning |
|---|---|
| `symptom` | Matches case and spacing variants. Optional for history, required for trends |
| `start_date`, `end_date` | Optional and inclusive, in `YYYY-MM-DD` format |
| `page`, `page_size` | History only. Default to 1 and 25; `page_size` is at most 100 |

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

Trends are never paged, so charts always cover the full filtered range. Days without entries have no point. The chart shows them as breaks in the line, so nothing is plotted for a day that was not logged. The all-symptoms chart makes one of these requests per symptom it draws, up to six at a time.

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

### Sharing (patients)

These routes need a patient token. Doctors get 403.

| Endpoint | Success | Failure |
|---|---|---|
| `POST /api/sharing/lookup` with `{"email": "..."}` | 200 `{"name": "...", "email": "..."}` | 404 no doctor account; 422 invalid email |
| `GET /api/sharing/grants` | 200 `{"grants": [...]}`, active grants only | |
| `POST /api/sharing/grants` with `{"email": "..."}` | 201 new grant, or 200 with the existing active grant | 404 no doctor account; 422 invalid email |
| `DELETE /api/sharing/grants/{grant_id}` | 204 with no body | 404 not found or already revoked |

An unknown email and a patient's email get the same 404. Sharing again after revoking creates a new grant and keeps the old row.

### Doctor views

These routes need a doctor token and are all read-only. Patients get 403.

| Endpoint | Success |
|---|---|
| `GET /api/doctor/patients` | 200 `{"patients": [...]}`, patients currently sharing with this doctor |
| `GET /api/doctor/patients/{patient_id}/symptoms` | Same as `GET /api/symptoms` |
| `GET /api/doctor/patients/{patient_id}/symptoms/names` | Same as `GET /api/symptoms/names` |
| `GET /api/doctor/patients/{patient_id}/symptoms/trends` | Same as `GET /api/symptoms/trends` |

The active grant is checked on every request, so a revocation applies immediately, even to tokens already issued. Without an active grant, these routes return the same 404 as a patient who does not exist.

### Health

| Endpoint | Success | Failure |
|---|---|---|
| `GET /api/health` | 200 `{"status": "ok", "service": "healthtrack-api"}` | API is not running |
| `GET /api/health/db` | 200 `{"status": "ok", "database": "connected"}` | 503 `{"status": "error", "database": "unavailable"}` |
