import { Plus } from 'lucide-react';
import { useRef } from 'react';
import { useFocusFirstError } from '../symptoms/useFocusFirstError.js';
import { useSymptomBatch } from '../symptoms/useSymptomBatch.js';
import { MAX_ENTRIES, todayInTimezone } from '../symptoms/validation.js';
import SymptomEntryRow from './SymptomEntryRow.jsx';

export default function SymptomEntryForm({ timezone, onSaved }) {
  const {
    rows,
    rowErrors,
    formError,
    isSubmitting,
    errorFocusRequest,
    updateRow,
    addRow,
    removeRow,
    submit,
  } = useSymptomBatch(timezone, onSaved);
  const formRef = useRef(null);
  const today = todayInTimezone(timezone);
  const isFull = rows.length >= MAX_ENTRIES;

  // In a long batch the first invalid field can be off screen.
  useFocusFirstError(formRef, errorFocusRequest);

  function handleSubmit(event) {
    event.preventDefault();
    submit();
  }

  return (
    <section className="card log-panel" aria-labelledby="log-symptoms-heading">
      <h2 id="log-symptoms-heading">Log symptoms</h2>
      <form ref={formRef} className="entry-form" onSubmit={handleSubmit} noValidate>
        <fieldset className="entry-form__rows" disabled={isSubmitting}>
          <legend className="visually-hidden">Symptom entries</legend>
          {rows.map((row, index) => (
            <SymptomEntryRow
              key={row.id}
              row={row}
              number={index + 1}
              today={today}
              errors={rowErrors[row.id] ?? {}}
              canRemove={rows.length > 1}
              onChange={updateRow}
              onRemove={removeRow}
            />
          ))}
          <button
            type="button"
            className="button button--secondary"
            disabled={isFull}
            onClick={addRow}
          >
            <Plus size={16} aria-hidden="true" />
            Add another entry
          </button>
          {isFull && <p className="field__hint">You can log up to {MAX_ENTRIES} entries at a time.</p>}
        </fieldset>

        {formError && (
          <p className="alert alert--error" role="alert">
            {formError}
          </p>
        )}
        <button type="submit" className="button" disabled={isSubmitting}>
          {isSubmitting ? 'Saving…' : rows.length === 1 ? 'Save entry' : `Save ${rows.length} entries`}
        </button>
      </form>
    </section>
  );
}
