// These checks give quick feedback only. The API remains the authority on validity.

export const MAX_ENTRIES = 20;
const MAX_NOTES_LENGTH = 500;
const MAX_NAME_LENGTH = 60;
const MIN_NAME_LENGTH = 2;

export function todayInTimezone(timezone) {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: timezone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(new Date());
  const value = (type) => parts.find((part) => part.type === type).value;
  return `${value('year')}-${value('month')}-${value('day')}`;
}

function validateName(name) {
  const normalized = name.trim().split(/\s+/).join(' ');
  if (!normalized) {
    return 'Symptom name is required';
  }
  if (normalized.length < MIN_NAME_LENGTH || normalized.length > MAX_NAME_LENGTH) {
    return `Symptom name must be between ${MIN_NAME_LENGTH} and ${MAX_NAME_LENGTH} characters`;
  }
  return null;
}

function validateDate(occurredOn, today) {
  if (!occurredOn) {
    return 'Date is required';
  }
  return occurredOn > today ? 'Date cannot be in the future' : null;
}

export function validateRow(row, today) {
  const errors = {
    symptom_name: validateName(row.symptom_name),
    occurred_on: validateDate(row.occurred_on, today),
    severity: row.severity ? null : 'Severity is required',
    notes:
      [...row.notes.trim()].length > MAX_NOTES_LENGTH
        ? `Notes must be at most ${MAX_NOTES_LENGTH} characters`
        : null,
  };
  return Object.fromEntries(Object.entries(errors).filter(([, message]) => message));
}

export function toEntryPayload(row) {
  return {
    symptom_name: row.symptom_name,
    occurred_on: row.occurred_on,
    severity: Number(row.severity),
    notes: row.notes.trim() || null,
  };
}
