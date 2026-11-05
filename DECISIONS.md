# HealthTrack — Engineering Decisions

## 1. Project goal

HealthTrack is a web application where patients log their symptoms, track how severity changes over time, and share their records with their doctors.

## 2. Scope

### Core

- Patients and doctors register and log in.
- Patients log 1–20 symptoms at a time, each with a name, date of occurrence, severity (1–10), and optional notes.
- Invalid submissions (missing fields, future dates, out-of-range severity) are rejected with a specific error message.
- Patients view their symptom history, with filters by symptom and date range.
- Patients correct or delete their own entries. Deleting asks for confirmation and is permanent.
- Patients see severity trends over time as a chart.
- Patients grant doctors access to their records, and can revoke it.
- Doctors view shared patients' records and trends (read-only).

## 3. Tech stack

| Layer | Technology | Why |
|---|---|---|
| Frontend | React + JavaScript + Vite, Plus Jakarta Sans (self-hosted), Lucide icons, jsPDF | Component-based interactive UI, fast dev server and build. The font ships with the app, so no third party sees visits and the demo works offline |
| Backend | FastAPI + Python 3.12 + pydantic-settings | REST API, Pydantic validation, automatic API docs, validated configuration |
| Database | PostgreSQL 16 + psycopg 3 | Relational data, foreign keys, constraints, trend queries |
| ORM / migrations | SQLAlchemy 2.0 (synchronous) + Alembic | Typed models, versioned schema changes |
| Authentication | JWT (PyJWT) + Argon2 (argon2-cffi) + email-validator | Simple bearer auth for patients and doctors; passwords never stored in plaintext |
| Charts | Chart.js + react-chartjs-2 | Severity trends over time |
| Testing | pytest + HTTPX | Service unit tests and API tests |
| Linting | Ruff (Python), ESLint (JavaScript) | Consistent style and early error detection |
| Local demo | Docker Compose (PostgreSQL, Adminer as a database viewer) + synthetic seed data; API on port 8001 | Primary demo path; reproducible and independent of hosted services. Docker Desktop can occupy port 8000 |
| Hosting | Vercel (frontend), Render (API), Supabase (database) | Free tiers suit a demo. Supabase is reached through its session pooler, its Data API is off, and every table has RLS on with no policies, so only the API's own connection can read data |

`tzdata` is included so that Python's `zoneinfo` can validate timezones on Windows, which has no system timezone database.

## 4. Data model

All columns are required unless marked optional. Timestamps are `timestamptz`.

### users

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `name` | text | |
| `email` | text | Stored lowercase, unique |
| `password_hash` | text | Argon2 hash |
| `role` | text | `patient` or `doctor`, enforced by a CHECK constraint |
| `timezone` | text | IANA name; see [Dates](#dates) |
| `created_at` | timestamptz | |

### symptom_entries

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `patient_id` | UUID | Foreign key → `users` |
| `symptom_name` | text | Trimmed, repeated whitespace collapsed, 2–60 characters (CHECK) |
| `symptom_key` | text | Lowercased `symptom_name`, used for filtering and grouping |
| `severity` | integer | 1–10 (CHECK) |
| `occurred_on` | date | Calendar date; cannot be in the future |
| `notes` | text | Optional, max 500 characters (CHECK) |
| `created_at` | timestamptz | |

Index on `(patient_id, occurred_on)` for history and trend queries.

### doctor_access

Each row is one grant. Revoking closes the row, and re-granting inserts a new row, so earlier grants are never overwritten.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `patient_id` | UUID | Foreign key → `users` |
| `doctor_id` | UUID | Foreign key → `users` |
| `granted_at` | timestamptz | |
| `revoked_at` | timestamptz | Optional; null while access is active |

Constraints:

- Partial unique index on `(patient_id, doctor_id) WHERE revoked_at IS NULL`: at most one active grant per pair.
- CHECK `patient_id <> doctor_id`.
- CHECK `revoked_at IS NULL OR revoked_at >= granted_at`.

The grant service checks that `patient_id` belongs to a patient and `doctor_id` to a doctor, because a CHECK constraint cannot read another table.

### Relationships

- One patient has many symptom entries; each entry belongs to one patient.
- Patients and doctors are many-to-many through `doctor_access`.
- Foreign keys use the default `NO ACTION`, since accounts cannot be deleted in the initial version.

## 5. Authentication

- **Token:** One signed JWT containing the user ID and expiry, sent in the `Authorization: Bearer` header. There are no refresh tokens.
- **Expiration:** 60 minutes. After that the API returns 401 and the user logs in again.
- **Storage:** `sessionStorage`, so the token survives a page refresh and is cleared when the tab closes.
- **Logout:** The client deletes the token, and every token expires within 60 minutes.
- **Current user:** Loaded from the database on each request, so the role comes from the database and not from a token claim.

Why these choices:

- `sessionStorage` is cleared when the tab closes. React escapes rendered values by default, notes are never rendered as raw HTML, and the 60-minute expiry keeps tokens short-lived.
- Bearer headers avoid CSRF and the cross-site cookie setup that separate frontend and API hosts would need.

## 6. Authorization

- Patient routes take the patient's identity only from the authenticated user, never from a client-supplied ID.
- Patients can access only their own records.
- Every doctor request checks for an active grant at request time, through one shared dependency.
- Doctors have no write routes for patient records.

| Situation | Response |
|---|---|
| Missing, invalid, or expired token | 401 |
| Wrong role for the route (for example, a doctor creating symptom entries) | 403 |
| Record or patient the requester is not authorized to access | 404 |

The 404 applies whether or not the record exists, so responses do not reveal which records exist. API tests cover cross-patient access, a doctor with no grant, and a doctor immediately after revocation.

## 7. Doctor sharing

1. The patient enters the exact email of an existing doctor account.
2. If the email matches a doctor, the API returns that doctor's name and email. Otherwise it returns a generic not-found message. There is no doctor directory or search.
3. The patient confirms, and an active grant is created. Granting when access is already active returns the existing grant.
4. The doctor can see all of the patient's entries, past and future, while the grant is active.
5. The patient can revoke access at any time. It takes effect on the doctor's next request.
6. The patient can grant access again later, which creates a new row.
7. Doctors see the patient's name and email, and their records read-only. Records already on a doctor's screen stay there until their next request to the server, which then removes them.

## 8. Symptom logging rules

### Batch submissions

- A submission contains 1–20 entries.
- It is all-or-nothing: entries are saved in one transaction, and one invalid entry means none are saved.
- Unknown fields, including `patient_id`, are rejected. The patient always comes from the token.
- All invalid entries are reported together, each identified by zero-based entry index and field:

```json
{
  "detail": "Validation failed",
  "errors": [
    { "entry": 1, "field": "severity", "message": "Severity must be between 1 and 10" }
  ]
}
```

### Normalization

One shared function trims the symptom name and collapses repeated whitespace to produce `symptom_name`, then lowercases that value to produce `symptom_key`. Length limits apply after normalization. Spelling variants and plurals such as "headache" and "headaches" remain separate symptoms.

### Charts

- Multiple entries for the same symptom on the same day are allowed, and history shows all of them.
- The chart plots one point per symptom per day, using the daily maximum severity. PostgreSQL computes this, and the frontend does not aggregate.
- Days with no entries are left as gaps, not plotted as zero. The API returns only days that have entries, so a long date range cannot produce a huge response, and the frontend breaks the line across skipped days.
- The chart shows one symptom at a time: the filtered symptom, otherwise the patient's choice, otherwise the most recently logged one.

### Dashboard and interface

- The dashboard shows each symptom's latest daily maximum and a 14-day pulse, built from the existing names and trends endpoints. Days without entries appear as empty outlines.
- Severity colors use display bands: 1–3 mild, 4–6 moderate, 7–10 severe. These are not clinical categories.
- Light is the default and dark is optional. Without a saved choice the interface follows the system setting.
- Each view is in the URL hash, so reloading and the Back button work. Filters stay out of the URL so symptom names do not reach browser history.
- Components stay on the existing token-based CSS. shadcn/ui would need a Tailwind migration, and Motion adds nothing over CSS for short transitions, so dialogs use native `<dialog>` and selection controls use native radio buttons.
- The all-symptoms chart draws up to six symptoms at a time, reusing the per-symptom trend endpoint. Six is the size of the color palette, which is validated across all pairs because any two lines can cross. Marker shapes differ too, so identity does not rest on color alone.

### History, reports, and AI insights

- History is paged on the server, 25 entries by default. Trends stay unpaged, so charts cover the full filtered range.
- PDFs are built in the browser from the same authorized API calls as the page, so reports need no endpoint of their own and a revoked doctor cannot export. The code loads only on export. A report holds at most 2,000 entries and says so when it is cut short.
- AI insights are for patients only, run only when asked, and never affect logging, viewing, or export. The server computes the figures and sends only those to the provider, with no dates, notes, or identity. Doctors do not get the feature, because sending a patient's data to a provider should be the patient's choice.
- Groq and OpenRouter are supported through one client, because both offer an OpenAI-compatible API. Groq is the default, because its model and output format are fixed. On OpenRouter only hosts that do not collect data are allowed.
- The provider sits behind a small interface and is optional. Without one, or if it fails, the figures are shown and labelled as not written by AI, so no AI output is ever imitated.

### Editing and deleting

- Only the owner can edit or delete an entry, and doctors stay read-only.
- Edits use the same validation as new entries. Fields left out of a request keep their values, and an explicit null clears `notes` only.
- Deleting removes the row. Edits keep no history, and there is no `updated_at` column because nothing uses it yet.
- After any change, the frontend refetches history, symptom names, and the trend rather than patching local state, so the displayed values always come from the server.

### Dates

- `occurred_on` is a calendar date with no time component, and it is stored and displayed without timezone conversion.
- "Today" means the current date in the patient's stored timezone. The server computes it; the client's date is not trusted.
- The browser sends its IANA timezone at registration. An invalid value is rejected, and `Asia/Kolkata` is used if none is sent.
- Every entry submission uses the same future-date check. It runs in the service layer because the result depends on the current date and the patient's timezone, so a database CHECK cannot enforce it.
- There is no lower limit on historical dates.

## 9. Security and privacy

- **Passwords:** Hashed with Argon2, with a minimum length of 8 characters. Failed logins return one generic error.
- **Authentication and ownership:** See [Authentication](#5-authentication) and [Authorization](#6-authorization).
- **CORS:** Explicit origin allowlist from configuration; no wildcard.
- **Environment variables:** `DATABASE_URL`, `JWT_SECRET`, `JWT_ALGORITHM`, and `CORS_ORIGINS` come from the environment. Real `.env` files are not committed; `.env.example` documents the names.
- **Demo data:** Seed and demo data are synthetic only. Real health information must not be entered. `python -m app.seed_demo` runs only on request. A hosted database needs its exact host confirmed and a private password, because the local demo password is public.
- **Logs:** Logs exclude request bodies, query strings, symptom names, notes, passwords, and tokens.
