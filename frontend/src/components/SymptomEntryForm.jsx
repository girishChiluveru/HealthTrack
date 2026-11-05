import { Plus } from 'lucide-react';
import { useRef } from 'react';
import { flushSync } from 'react-dom';
import { useFocusFirstError } from '../symptoms/useFocusFirstError.js';
import { activeOnly, useSymptomBatch } from '../symptoms/useSymptomBatch.js';
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
    discardRow,
    submit,
  } = useSymptomBatch(timezone, onSaved);
  const formRef = useRef(null);
  const today = todayInTimezone(timezone);
  const active = activeOnly(rows);
  const isFull = active.length >= MAX_ENTRIES;
  const addButton = useRef(null);

  useFocusFirstError(formRef, errorFocusRequest);

  function handleRemove(id) {
    flushSync(() => removeRow(id));
    addButton.current?.focus();
  }

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
          {rows.map((row) => (
            <div
              key={row.id}
              className={row.isRemoving ? 'entry-slot entry-slot--removing' : 'entry-slot'}
              inert={row.isRemoving}
              onAnimationEnd={(event) => {
                if (row.isRemoving && event.target === event.currentTarget) {
                  discardRow(row.id);
                }
              }}
            >
              <div className="entry-slot__clip">
                <SymptomEntryRow
                  row={row}
                  number={active.indexOf(row) + 1 || active.length + 1}
                  today={today}
                  errors={rowErrors[row.id] ?? {}}
                  canRemove={active.length > 1 && !row.isRemoving}
                  onChange={updateRow}
                  onRemove={handleRemove}
                />
              </div>
            </div>
          ))}
          <button
            ref={addButton}
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
          {isSubmitting
            ? 'Saving…'
            : active.length === 1
              ? 'Save entry'
              : `Save ${active.length} entries`}
        </button>
      </form>
    </section>
  );
}
