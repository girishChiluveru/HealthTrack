# HealthTrack — Engineering Decisions

## 1. Project goal

HealthTrack is a web application where patients log their symptoms, track how severity changes over time, and share their records with their doctors.

## 2. Scope

### Core

- Patients and doctors register and log in.
- Patients log 1–20 symptoms at a time, each with a name, date of occurrence, severity (1–10), and optional notes.
- Invalid submissions (missing fields, future dates, out-of-range severity) are rejected with a specific error message.
- Patients view their symptom history, with filters by symptom and date range.
- Patients see severity trends over time as a chart.
- Patients grant doctors access to their records, and can revoke it.
- Doctors view shared patients' records and trends (read-only).

### Out of scope for the initial version

- Editing and deleting symptom entries (see [Open questions](#10-open-questions))
- Account deletion and changing a stored timezone
- Password reset and email verification
- Comprehensive audit logging and login rate limiting
- Professional verification of doctors

### Future enhancements

These are not current implementation requirements.

- Expiring, revocable public share links
- PDF export of symptom reports
- AI-generated general wellness suggestions with safety guardrails

## 3. Tech stack

| Layer | Technology | Why |
|---|---|---|
| Frontend | React + JavaScript + Vite | Component-based interactive UI, fast dev server and build |
| Backend | FastAPI + Python 3.12 + pydantic-settings | REST API, Pydantic validation, automatic API docs, validated configuration |
| Database | PostgreSQL 16 + psycopg 3 | Relational data, foreign keys, constraints, trend queries |
| ORM / migrations | SQLAlchemy 2.0 (synchronous) + Alembic | Typed models, versioned schema changes |
| Authentication | JWT (PyJWT) + Argon2 (argon2-cffi) + email-validator | Simple bearer auth for patients and doctors; passwords never stored in plaintext |
| Charts | Chart.js + react-chartjs-2 | Severity trends over time |
| Testing | pytest + HTTPX | Service unit tests and API tests |
| Linting | Ruff (Python), ESLint (JavaScript) | Consistent style and early error detection |
| Local demo | Docker Compose (PostgreSQL) + synthetic seed data; API on port 8001 | Primary demo path; reproducible and independent of hosted services. Docker Desktop can occupy port 8000 |
| Hosting (optional) | Vercel (frontend), Render (API), Supabase (database) | Only after the core and local demo are reliable |

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
- **Logout:** The client deletes the token. There is no server-side denylist, so a copied token stays valid until it expires.
- **Current user:** Loaded from the database on each request, so the role comes from the database and not from a token claim.

Trade-offs:

- JavaScript can read `sessionStorage`, so an XSS bug could expose the token. React escapes rendered values by default, notes are never rendered as raw HTML, and the 60-minute expiry limits the exposure.
- Bearer headers avoid CSRF and the cross-site cookie setup that separate frontend and API hosts would need.
- `HttpOnly` cookies would protect the token from XSS, but they add CSRF handling and cross-domain configuration that this prototype does not justify.

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

**Prototype limitation:** Doctor identities are not professionally verified. Anyone can register with the doctor role, and the name shown at confirmation is self-declared. A production system would need credential verification before patients rely on this role.

## 8. Symptom logging rules

### Batch submissions

- A submission contains 1–20 entries.
- It is all-or-nothing: entries are saved in one transaction, and one invalid entry means none are saved.
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
- The chart plots one point per symptom per day, using the daily maximum severity.
- Days with no entries are left as gaps, not plotted as zero.

### Dates

- `occurred_on` is a calendar date with no time component, and it is stored and displayed without timezone conversion.
- "Today" means the current date in the patient's stored timezone. The server computes it; the client's date is not trusted.
- The browser sends its IANA timezone at registration. An invalid value is rejected, and `Asia/Kolkata` is used if none is sent.
- Every entry submission uses the same future-date check. It runs in the service layer because the result depends on the current date and the patient's timezone, so a database CHECK cannot enforce it.
- There is no lower limit on historical dates.
- **Limitation:** The timezone is set only at registration, so a patient who travels keeps their original timezone.

## 9. Security and privacy

- **Passwords:** Hashed with Argon2, with a minimum length of 8 characters. Failed logins return one generic error.
- **Authentication and ownership:** See [Authentication](#5-authentication) and [Authorization](#6-authorization).
- **CORS:** Explicit origin allowlist from configuration; no wildcard.
- **Environment variables:** `DATABASE_URL`, `JWT_SECRET`, `JWT_ALGORITHM`, and `CORS_ORIGINS` come from the environment. Real `.env` files are not committed; `.env.example` documents the names.
- **Demo data:** Seed and demo data are synthetic only. Real health information must not be entered.
- **Logs:** Logs exclude request bodies, symptom names, notes, passwords, and tokens.
- **Accepted trade-off:** Registration reports when an email is already in use, which reveals that the account exists.

This is a prototype and is not presented as compliant with any health-data regulation.

## 10. Open questions

The take-home brief is not in this repository, so these need checking against it:

- **Editing and deleting entries:** Out of scope unless the brief requires them. If required, add owner-only update and delete routes and an `updated_at` column. Doctors stay read-only.
- **Doctor access:** Included in the core here. Confirm that the brief requires it; if not, it could be reduced or moved to future enhancements.
- **Hosted deployment:** Treated as optional. If the brief requires a live URL, deployment becomes part of the core.
- **Security scope:** Password reset, email verification, and audit logging stay out of scope unless the brief requires them.
