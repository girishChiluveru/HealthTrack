import { useRef, useState } from 'react';
import { updateSymptomEntry } from '../api/symptoms.js';
import { useFocusFirstError } from '../symptoms/useFocusFirstError.js';
import { toEntryPayload, todayInTimezone, validateRow } from '../symptoms/validation.js';
import SymptomFields from './SymptomFields.jsx';

function toFormValues(entry) {
  return {
    symptom_name: entry.symptom_name,
    occurred_on: entry.occurred_on,
    severity: String(entry.severity),
    notes: entry.notes ?? '',
  };
}

export default function EntryEditForm({ entry, timezone, onSaved, onMissing, onCancel }) {
  const [values, setValues] = useState(() => toFormValues(entry));
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [errorFocusRequest, setErrorFocusRequest] = useState(0);
  const saveInFlight = useRef(false);
  const formRef = useRef(null);
  const today = todayInTimezone(timezone);
  useFocusFirstError(formRef, errorFocusRequest);

  function handleChange(field, value) {
    setValues((current) => ({ ...current, [field]: value }));
    setErrors((current) => {
      const remaining = { ...current };
      delete remaining[field];
      return remaining;
    });
  }

  function showFieldErrors(fieldErrors) {
    setErrors(fieldErrors);
    setErrorFocusRequest((current) => current + 1);
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (saveInFlight.current) {
      return;
    }
    setFormError('');

    const localErrors = validateRow(values, todayInTimezone(timezone));
    if (Object.keys(localErrors).length > 0) {
      showFieldErrors(localErrors);
      return;
    }

    saveInFlight.current = true;
    setIsSaving(true);
    try {
      onSaved(await updateSymptomEntry(entry.id, toEntryPayload(values)));
    } catch (error) {
      if (error.status === 404) {
        onMissing();
      } else if (Object.keys(error.fieldErrors ?? {}).length > 0) {
        showFieldErrors(error.fieldErrors);
      } else {
        setFormError(error.message);
      }
    } finally {
      saveInFlight.current = false;
      setIsSaving(false);
    }
  }

  return (
    <form ref={formRef} className="entry-form" onSubmit={handleSubmit} noValidate>
      <fieldset className="entry-form__rows" disabled={isSaving}>
        <legend className="visually-hidden">Edit entry</legend>
        <SymptomFields values={values} errors={errors} today={today} onChange={handleChange} />
      </fieldset>
      {formError && (
        <p className="alert alert--error" role="alert">
          {formError}
        </p>
      )}
      <div className="action-row">
        <button type="submit" className="button" disabled={isSaving}>
          {isSaving ? 'Saving…' : 'Save changes'}
        </button>
        <button
          type="button"
          className="button button--secondary"
          disabled={isSaving}
          onClick={onCancel}
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
