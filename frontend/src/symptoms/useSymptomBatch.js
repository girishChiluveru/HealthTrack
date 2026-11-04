import { useRef, useState } from 'react';
import { createSymptomBatch } from '../api/symptoms.js';
import { MAX_ENTRIES, toEntryPayload, todayInTimezone, validateRow } from './validation.js';

const INVALID_BATCH = 'Nothing was saved. Please correct the highlighted fields and try again.';

let nextRowId = 1;

function createRow(today) {
  const id = nextRowId;
  nextRowId += 1;
  return { id, symptom_name: '', occurred_on: today, severity: '', notes: '' };
}

// Maps API errors, which identify entries by index, onto the rows that were submitted.
function mapServerErrors(errors, submittedRows) {
  const rowErrors = {};
  const otherMessages = [];
  for (const { entry, field, message } of errors) {
    const row = submittedRows[entry];
    if (row) {
      rowErrors[row.id] = { ...rowErrors[row.id], [field]: message };
    } else {
      otherMessages.push(message);
    }
  }
  return { rowErrors, otherMessages };
}

export function useSymptomBatch(timezone, onSaved) {
  const [rows, setRows] = useState(() => [createRow(todayInTimezone(timezone))]);
  const [rowErrors, setRowErrors] = useState({});
  const [formError, setFormError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  // Increments whenever new field errors appear, so the form can move focus to them.
  const [errorFocusRequest, setErrorFocusRequest] = useState(0);
  // State updates only apply on the next render, so a fast double click needs a ref.
  const submissionInFlight = useRef(false);

  function updateRow(id, field, value) {
    setRows((current) =>
      current.map((row) => (row.id === id ? { ...row, [field]: value } : row)),
    );
    setRowErrors((current) => {
      if (!current[id]?.[field]) {
        return current;
      }
      const remaining = { ...current[id] };
      delete remaining[field];
      return { ...current, [id]: remaining };
    });
    setSuccessMessage('');
  }

  function addRow() {
    setRows((current) =>
      current.length < MAX_ENTRIES ? [...current, createRow(todayInTimezone(timezone))] : current,
    );
    setSuccessMessage('');
  }

  function removeRow(id) {
    setRows((current) => (current.length > 1 ? current.filter((row) => row.id !== id) : current));
    setRowErrors((current) => {
      const remaining = { ...current };
      delete remaining[id];
      return remaining;
    });
    setSuccessMessage('');
  }

  async function submit() {
    if (submissionInFlight.current) {
      return;
    }

    setFormError('');
    setSuccessMessage('');

    const today = todayInTimezone(timezone);
    const localErrors = Object.fromEntries(
      rows
        .map((row) => [row.id, validateRow(row, today)])
        .filter(([, errors]) => Object.keys(errors).length > 0),
    );
    setRowErrors(localErrors);
    if (Object.keys(localErrors).length > 0) {
      setFormError(INVALID_BATCH);
      setErrorFocusRequest((current) => current + 1);
      return;
    }

    submissionInFlight.current = true;
    setIsSubmitting(true);
    const submittedRows = rows;
    try {
      const { entries } = await createSymptomBatch(submittedRows.map(toEntryPayload));
      setRows([createRow(today)]);
      setSuccessMessage(
        entries.length === 1 ? 'Saved 1 entry.' : `Saved ${entries.length} entries.`,
      );
      onSaved();
    } catch (error) {
      const { rowErrors: serverErrors, otherMessages } = mapServerErrors(
        error.errors ?? [],
        submittedRows,
      );
      const hasRowErrors = Object.keys(serverErrors).length > 0;
      setRowErrors(serverErrors);
      setFormError(hasRowErrors ? INVALID_BATCH : (otherMessages[0] ?? error.message));
      if (hasRowErrors) {
        setErrorFocusRequest((current) => current + 1);
      }
    } finally {
      submissionInFlight.current = false;
      setIsSubmitting(false);
    }
  }

  return {
    rows,
    rowErrors,
    formError,
    successMessage,
    isSubmitting,
    errorFocusRequest,
    updateRow,
    addRow,
    removeRow,
    submit,
  };
}
