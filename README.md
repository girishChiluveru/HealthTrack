# HealthTrack

HealthTrack is a web app where patients log their symptoms, see how severity changes over time, and share their records with their doctors. All demo data is synthetic, so please do not enter real health information.

- **Live app:** <https://health-track-ten-drab.vercel.app>
- **Live API docs:** <https://healthtrack-4yev.onrender.com/docs>

The API runs on Render's free plan, so the first request after a quiet period can take about a minute.

## Features

**Patients** can:

- Log 1–20 symptoms at once, each with a name, date, severity from 1 to 10, and optional notes
- Review, filter, edit, and delete their entries
- Chart severity over time, for one symptom or several together
- Share records with a doctor, and revoke that access at any time
- Export a PDF report
- Generate optional AI insights from their recent entries

**Doctors** get a read-only view of the patients who share with them, including history and trends, and can export those records.

## Requirement coverage

| Priority | Requirement | How it is met |
|---|---|---|
| Must | Data model for patients and symptoms | `users`, `symptom_entries`, and `doctor_access` tables. One patient has many entries, each with a date and severity |
| Must | REST endpoint with validation | `POST /api/symptoms/batch` saves valid entries and returns a clear error for each invalid field |
| Must | Edge-case error handling | Missing fields and future dates each return their own message, such as `Date cannot be in the future` |
| Must | Front-end to log symptoms and view history | A React interface for logging symptoms and viewing history, served by a Python (FastAPI) API |
| Should | Severity chart | Interactive Chart.js charts of daily maximum severity |
| Could | Documentation | This README, [DECISIONS.md](DECISIONS.md), and automatic API docs at `/docs` |

## Tech stack

| Layer | Choice | Why I chose it |
|---|---|---|
| Frontend | React, Vite, Chart.js | Suits an interactive form and charts, and I already knew React |
| Backend | FastAPI (Python) | Request validation through Pydantic, automatic API docs, and less setup than Django for an API |
| Database | PostgreSQL, SQLAlchemy, Alembic | The data is relational. Foreign keys and constraints protect it, and SQL can calculate trends directly. Alembic keeps schema changes versioned |
| AI | Groq API | Fast, has a free tier, and offers structured JSON output |
| Hosting | Vercel, Render, Supabase | Free plans for the frontend, the API, and PostgreSQL |

## Key decisions

- **React on a Python API.** FastAPI handles all validation, business logic, and data access. The interface is built in React because the charts and multi-row form are highly interactive.
- **Three tables.** I started from patients, doctors, and symptoms. Patients and doctors share a `users` table with a `role`, because they log in the same way. `symptom_entries` holds one row per symptom, and `doctor_access` links patients to doctors.
- **Validation at three levels.** React gives quick feedback, Pydantic in the API has the final say, and database constraints are the last safety net.
- **"Future" uses the patient's timezone.** The server works out today's date from the patient's stored timezone, so the client's clock is not trusted.
- **All-or-nothing batches.** Entries are saved in one transaction, and one invalid entry means none are saved. The response lists every error together.
- **Patient identity comes only from the token.** A request that supplies `patient_id` is rejected, so one patient cannot write to another's record.
- **Sharing is checked on every request.** Revoking a doctor's access takes effect on their next request. Records the requester cannot access return 404, so responses do not reveal what exists.
- **Routes stay thin.** Routes handle HTTP, and business logic lives in `services/`, so it can be tested and reused by both patient and doctor routes.
- **Health data stays out of logs.** Logs exclude request bodies, query strings, and symptom details.

The full reasoning is in [DECISIONS.md](DECISIONS.md).

## Project structure

```text
backend/
  app/
    main.py      App setup and error handling
    models.py    Database tables
    schemas.py   Request and response validation
    api/         Routes: auth, symptoms, sharing, doctor, health
    services/    Business logic and queries
  migrations/    Database schema history
  tests/         Unit and integration tests
frontend/src/
  api/           Calls to the backend
  components/    Screens and UI pieces
  symptoms/      Chart, date, and form logic
  reports/       PDF export
```

## Run it locally

You need Python 3.12, Node.js 20.19+, 22.13+, or 24+, and Docker Desktop. Commands are for Windows PowerShell.

**1. Start PostgreSQL** from the repository root:

```powershell
docker compose up -d --wait
```

**2. Set up and start the API** from `backend/`:

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Paste the printed value after `JWT_SECRET=` in `backend/.env`, then run:

```powershell
alembic upgrade head
python -m app.seed_demo
uvicorn app.main:create_app --factory --reload --port 8001
```

**3. Set up and start the frontend** from `frontend/`, in a second terminal:

```powershell
npm ci
Copy-Item .env.example .env
npm run dev
```

Open <http://localhost:5173>. API docs are at <http://localhost:8001/docs>.

**Demo accounts** from the seed step use the password `demo-password-1`:

| Account | Role |
|---|---|
| `mira.demo@example.com` | Patient with about 30 days of records, shared with the doctor below |
| `dr.lena.demo@example.com` | Doctor with read-only access to Mira's records |
| `noah.demo@example.com` | Patient who shares with nobody |

AI insights are optional. To turn them on, set `AI_API_KEY` in `backend/.env` to a Groq key and restart the API. Without a key, the app still shows the calculated figures.

## Using the API

Interactive docs at `/docs` list every endpoint. Except for register and login, requests need `Authorization: Bearer <token>`.

| Endpoint | Purpose |
|---|---|
| `POST /api/auth/register` | Create a patient or doctor account |
| `POST /api/auth/login` | Get an access token |
| `GET /api/auth/me` | Get the current user |
| `POST /api/symptoms/batch` | Log 1–20 symptoms |
| `GET /api/symptoms` | List history, with filters and paging |
| `GET /api/symptoms/names` | List the patient's symptoms |
| `GET /api/symptoms/trends?symptom=headache` | Get daily maximum severity for one symptom |
| `PATCH /api/symptoms/{entry_id}` | Edit an entry |
| `DELETE /api/symptoms/{entry_id}` | Delete an entry |
| `POST /api/symptoms/insights` | Generate insights |
| `POST /api/sharing/lookup` | Find a doctor by exact email |
| `GET`, `POST /api/sharing/grants` | List or create sharing grants |
| `DELETE /api/sharing/grants/{grant_id}` | Revoke a doctor's access |
| `GET /api/doctor/patients` | List patients sharing with this doctor |
| `GET /api/doctor/patients/{patient_id}/symptoms` | Read a shared patient's history. `/names` and `/trends` are also available |
| `GET /api/health`, `GET /api/health/db` | Check the API and the database |

**Example request** to `POST /api/symptoms/batch`:

```json
{
  "entries": [
    { "symptom_name": "Headache", "occurred_on": "2026-03-09", "severity": 6, "notes": "After lunch" },
    { "symptom_name": "Sore throat", "occurred_on": "2026-03-09", "severity": 3 }
  ]
}
```

**Example 422 response.** `entry` is the zero-based position in the batch, and nothing is saved:

```json
{
  "detail": "Validation failed",
  "errors": [
    { "entry": 0, "field": "severity", "message": "Severity must be between 1 and 10" },
    { "entry": 1, "field": "occurred_on", "message": "Date cannot be in the future" }
  ]
}
```

Other responses: 401 for a missing or invalid token, 403 for the wrong role, and 404 for a record the requester cannot access.

## Testing

The backend has 392 tests: 197 unit tests and 195 integration tests. Integration tests run against real PostgreSQL, in a temporary database built from the migrations. From `backend/`:

```powershell
pytest                  # Unit tests; no database needed
pytest -m integration   # Integration tests; needs PostgreSQL running
pytest -m ""            # Everything
```

The frontend is checked with `npm run lint` and `npm run build`, and by manual inspection of the interface.

## Deployment

| Part | Host |
|---|---|
| Frontend | Vercel |
| API | Render |
| PostgreSQL | Supabase |

## AI usage

**Tools**

- **Claude Code** built the project from my prompts.
- **Claude skills:** I installed `frontend-design` and `web-design-guidelines` to guide the interface.
- **Groq API** powers the AI insights feature inside the app.

**What I did before using AI**

1. Explored the problem statement and worked out which features the application needed.
2. Designed a simple data model around patients, doctors, and symptoms.
3. Chose the tech stack by comparing its advantages with the alternatives.
4. Decided to add an AI feature that summarizes a patient's recent symptoms.
5. Wrote a stage-wise implementation plan as prompts for Claude Code.

**Where AI was used**

I prompted Claude Code one stage at a time, so it touched the backend, frontend, migrations, tests, and documentation, including this README. Each stage is in the git history:

| Stage | Commit | What was built |
|---|---|---|
| 1 | `2c8baf9` | Project decisions |
| 2 | `c0cb480` | Frontend and backend foundation |
| 3 | `d955ba8` | Database models, migrations, and authentication |
| 4 | `17d18a9` | Symptom logging and validation |
| 5 | `a44fa2e` | Editing, deleting, and the first chart |
| 6 | `4e42013` | Design fixes, doctor sharing, and the doctor dashboard |
| 7 | `ffe2dec` | Interactive charts, a modernized interface, and demo data |
| 8 | `695af28` | Final tests, AI insights, PDF export, and paging |

**What I verified or changed**

At every stage I reviewed the code, inspected the interface manually, and ran the tests. When something needed fixing, I prompted Claude Code to correct it before moving on. I then deployed the application to Vercel, Render, and Supabase.

**The AI feature in the app**

When a patient asks for insights, the server calculates per-symptom figures, by default for the last 30 days, and needs at least 3 logged days. Only those figures and the symptom labels go to Groq, never notes, dates, or the patient's name or email.

A system prompt sets the rules, and a JSON schema fixes the output format. A word filter then drops any statement that mentions a diagnosis or medicine. The result is observations about the figures plus general wellness tips, not medical advice. If Groq is unavailable, the app shows the calculated figures, labelled as not written by AI.
