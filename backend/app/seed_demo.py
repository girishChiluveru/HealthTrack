"""Load synthetic demo records into a local database.

Run from `backend/` with `python -m app.seed_demo`. It runs only when asked, never at startup,
and refuses any database that is not on this machine.

It can be run repeatedly. Each run resets the demo accounts below to the same state, relative
to today, and leaves every other account alone. Everything here is fictional.
"""

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_session_factory
from app.models import DoctorAccess, SymptomEntry, User, UserRole
from app.security import hash_password
from app.services.sharing import get_active_grant
from app.services.symptoms import today_in_timezone, validate_batch
from app.symptom_names import symptom_key

# Public on purpose, like the accounts. The local-only check is what keeps them off a server.
DEMO_PASSWORD = "demo-password-1"
DEMO_TIMEZONE = "Asia/Kolkata"
LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})

# One character per day, oldest first and ending today. A digit is that day's severity, and a
# dash is a day with no entry, which charts show as a gap. Each covers the same 30 days.
MAIN_PATIENT_SEVERITIES = {
    "Headache": "334---567888--654--33---567854",
    "Fatigue": "8877-76666-5554-44433-333-3233",
    "Joint pain": "2233-456888765-5443-3322--2222",
    "Nausea": "--456---------345----------324",
    "Sore throat": "------------357642------------",
    "Dizziness": "---23----454-----456-----32---",
    "Brain fog": "556655-5444-443--33-33--222-22",
}

# Extra entries on days above, as (symptom, days ago, severity, notes). Charts plot only the
# highest severity of a day, so these show the daily maximum at work.
MAIN_PATIENT_EXTRAS = [
    ("Headache", 2, 3, "Mild in the morning, worse by evening."),
    ("Headache", 18, 4, "Eased after resting."),
    ("Fatigue", 9, 2, "Felt better after a long sleep."),
    ("Joint pain", 20, 4, "Better after a short walk."),
]

MAIN_PATIENT_NOTES = {
    ("Headache", 2): "Second entry today: much worse after screen time.",
    ("Headache", 18): "Started mid-afternoon.",
    ("Joint pain", 20): "Stiff when waking up.",
    ("Sore throat", 15): "Worst day so far.",
    ("Nausea", 2): "After a heavy meal.",
}

OTHER_PATIENT_SEVERITIES = {"Back pain": "--------------------45-65-43-3"}


@dataclass(frozen=True)
class DemoAccount:
    name: str
    email: str
    role: UserRole


MAIN_PATIENT = DemoAccount("Mira Demo", "mira.demo@example.com", UserRole.PATIENT)
# Shares with nobody, so the doctor's list shows that access is by grant only.
OTHER_PATIENT = DemoAccount("Noah Demo", "noah.demo@example.com", UserRole.PATIENT)
DOCTOR = DemoAccount("Dr Lena Demo", "dr.lena.demo@example.com", UserRole.DOCTOR)


def require_local_database(database_url: str) -> None:
    host = make_url(database_url).host
    if host not in LOCAL_HOSTS:
        raise SystemExit(
            f"Refusing to seed: demo data is for local databases only, not host {host!r}."
        )


def build_entries(
    severities: dict[str, str],
    extras: list[tuple[str, int, int, str]],
    notes: dict[tuple[str, int], str],
    today: date,
) -> list[dict]:
    entries = []
    for name, values in severities.items():
        for index, severity in enumerate(values):
            if severity != "-":
                days_ago = len(values) - 1 - index
                entries.append(
                    {
                        "symptom_name": name,
                        "occurred_on": (today - timedelta(days=days_ago)).isoformat(),
                        "severity": int(severity),
                        "notes": notes.get((name, days_ago)),
                    }
                )
    for name, days_ago, severity, note in extras:
        entries.append(
            {
                "symptom_name": name,
                "occurred_on": (today - timedelta(days=days_ago)).isoformat(),
                "severity": severity,
                "notes": note,
            }
        )
    return entries


def upsert_account(db: Session, account: DemoAccount) -> User:
    user = db.scalar(select(User).where(User.email == account.email))
    if user is None:
        user = User(email=account.email, role=account.role)
        db.add(user)
    elif user.role != account.role:
        raise SystemExit(f"Refusing to seed: {account.email} already exists with another role.")
    user.name = account.name
    user.password_hash = hash_password(DEMO_PASSWORD)
    user.timezone = DEMO_TIMEZONE
    db.flush()
    return user


def replace_entries(db: Session, patient: User, raw_entries: list[dict], today: date) -> None:
    """Swap in the planned entries, checked by the same rules as the API."""
    db.execute(delete(SymptomEntry).where(SymptomEntry.patient_id == patient.id))
    db.add_all(
        SymptomEntry(
            patient_id=patient.id,
            symptom_name=entry.symptom_name,
            symptom_key=symptom_key(entry.symptom_name),
            severity=entry.severity,
            occurred_on=entry.occurred_on,
            notes=entry.notes,
        )
        for entry in validate_batch(raw_entries, today)
    )


def close_other_grants(db: Session, patient: User, doctor: User) -> None:
    """End anything shared during an earlier demo, apart from the planned grant."""
    grants = db.scalars(
        select(DoctorAccess).where(
            DoctorAccess.patient_id == patient.id,
            DoctorAccess.doctor_id != doctor.id,
            DoctorAccess.revoked_at.is_(None),
        )
    )
    for grant in grants:
        grant.revoked_at = func.now()


def seed(db: Session, today: date) -> dict[str, int]:
    """Reset the demo accounts in one transaction, and return what they now hold."""
    main_patient = upsert_account(db, MAIN_PATIENT)
    other_patient = upsert_account(db, OTHER_PATIENT)
    doctor = upsert_account(db, DOCTOR)

    main_entries = build_entries(
        MAIN_PATIENT_SEVERITIES, MAIN_PATIENT_EXTRAS, MAIN_PATIENT_NOTES, today
    )
    other_entries = build_entries(OTHER_PATIENT_SEVERITIES, [], {}, today)
    replace_entries(db, main_patient, main_entries, today)
    replace_entries(db, other_patient, other_entries, today)

    close_other_grants(db, main_patient, doctor)
    if get_active_grant(db, main_patient.id, doctor.id) is None:
        db.add(DoctorAccess(patient_id=main_patient.id, doctor_id=doctor.id))
    db.commit()
    return {"main_entries": len(main_entries), "other_entries": len(other_entries)}


def main() -> None:
    require_local_database(get_settings().database_url.get_secret_value())
    with get_session_factory()() as db:
        counts = seed(db, today_in_timezone(DEMO_TIMEZONE))
    print(f"Patient: {MAIN_PATIENT.email} ({counts['main_entries']} entries)")
    print(f"Patient: {OTHER_PATIENT.email} ({counts['other_entries']} entries, shares with nobody)")
    print(f"Doctor:  {DOCTOR.email} (can read {MAIN_PATIENT.name}'s records)")
    print("The password is in the Demo data section of README.md.")


if __name__ == "__main__":
    main()
