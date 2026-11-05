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

// A removed row stays on screen while it closes, but it is out of the form from that moment.
export function activeOnly(rows) {
  return rows.filter((row) => !row.isRemoving);
}

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
  const [isSubmitting, setIsSubmitting] = useState(false);
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
  }

  function addRow() {
    setRows((current) =>
      activeOnly(current).length < MAX_ENTRIES
        ? [...current, createRow(todayInTimezone(timezone))]
        : current,
    );
  }

  function removeRow(id) {
    setRows((current) =>
      activeOnly(current).length > 1
        ? current.map((row) => (row.id === id ? { ...row, isRemoving: true } : row))
        : current,
    );
    setRowErrors((current) => {
      const remaining = { ...current };
      delete remaining[id];
      return remaining;
    });
  }

  function discardRow(id) {
    setRows((current) => current.filter((row) => row.id !== id));
  }

  async function submit() {
    if (submissionInFlight.current) {
      return;
    }

    setFormError('');

    const today = todayInTimezone(timezone);
    const submittedRows = activeOnly(rows);
    const localErrors = Object.fromEntries(
      submittedRows
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
    try {
      const { entries } = await createSymptomBatch(submittedRows.map(toEntryPayload));
      setRows([createRow(today)]);
      onSaved(entries.length);
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
    isSubmitting,
    errorFocusRequest,
    updateRow,
    addRow,
    removeRow,
    discardRow,
    submit,
  };
}
