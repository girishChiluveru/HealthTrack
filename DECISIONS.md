# HealthTrack — Engineering Decisions

## 1. Project goal

HealthTrack is a web application where patients log their symptoms, track how severity changes over time, and share their records with their doctors.

## 2. Features

### Core

- Patients register and log in.
- Patients log one or more symptoms at a time, each with a name, date of occurrence, severity (1–10), and optional notes.
- Invalid submissions (missing fields, future dates, out-of-range severity) are rejected with a specific error message.
- Patients view their symptom history, with filters by symptom and date range.
- Patients see severity trends over time as a chart.
- Patients grant doctors access to their records, and can revoke it.
- Doctors view shared patients' records and trends (read-only).

### Planned extensions

- Expiring, revocable share links
- PDF export of symptom reports
- AI-generated general wellness suggestions with safety guardrails

## 3. Tech stack

| Layer | Technology | Why |
|---|---|---|
| Frontend | React + JavaScript + Vite | Component-based interactive UI, fast dev server and build |
| Backend | FastAPI + Python 3.12 | REST API, Pydantic validation, automatic API docs |
| Database | PostgreSQL 16 | Relational data, foreign keys, constraints, trend queries |
| ORM / migrations | SQLAlchemy 2.0 + Alembic | Typed models, versioned schema changes |
| Authentication | JWT + Argon2 password hashing | Stateless auth for patients and doctors; passwords never stored in plaintext |
| Charts | Chart.js + react-chartjs-2 | Severity trends over time |
| Testing | pytest + HTTPX | Service unit tests and API tests |
| Local setup | Docker Compose (PostgreSQL) | Reproducible local database |
| Hosting | Vercel (frontend), Render (API), Supabase (database) | Separate hosting for each layer |

## 4. Data model

### users

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `name` | text | |
| `email` | text | Stored lowercase, unique |
| `password_hash` | text | Argon2 hash |
| `role` | text | `patient` or `doctor` |
| `timezone` | text | Default `Asia/Kolkata`; used to decide what "today" means |
| `created_at` | timestamp | |

### symptom_entries

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `patient_id` | UUID | Foreign key → `users` |
| `symptom_name` | text | As entered, trimmed, 2–60 characters |
| `symptom_key` | text | Lowercased name, used to group the same symptom in charts |
| `severity` | integer | 1–10, enforced by a CHECK constraint |
| `occurred_on` | date | The day the symptom occurred; cannot be in the future |
| `notes` | text | Optional, max 500 characters |
| `created_at` | timestamp | |

Index on `(patient_id, occurred_on)` for history and trend queries.

### doctor_access

| Column | Type | Notes |
|---|---|---|
| `patient_id` | UUID | Foreign key → `users` |
| `doctor_id` | UUID | Foreign key → `users` |
| `granted_at` | timestamp | |
| `revoked_at` | timestamp | Null while access is active |

Unique on `(patient_id, doctor_id)`.

### Relationships

- One patient has many symptom entries; each entry belongs to one patient.
- Patients and doctors are many-to-many through `doctor_access`.
