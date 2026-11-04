import { useEffect, useRef, useState } from 'react';
import { deleteSymptomEntry } from '../api/symptoms.js';
import { formatDate } from '../symptoms/dates.js';
import EntryEditForm from './EntryEditForm.jsx';

export default function HistoryEntry({ entry, timezone, onEdited, onDeleted, onMissing }) {
  const [mode, setMode] = useState('view');
  const [deleteError, setDeleteError] = useState('');
  const [isDeleting, setIsDeleting] = useState(false);
  const deleteInFlight = useRef(false);
  const editButton = useRef(null);
  const deleteButton = useRef(null);
  const focusTarget = useRef(null);

  // Editing and confirming replace the buttons, so focus has to be put back afterwards.
  useEffect(() => {
    if (mode === 'view' && focusTarget.current) {
      focusTarget.current.current?.focus();
      focusTarget.current = null;
    }
  }, [mode]);

  function returnToView(button) {
    focusTarget.current = button;
    setDeleteError('');
    setMode('view');
  }

  async function confirmDelete() {
    if (deleteInFlight.current) {
      return;
    }
    deleteInFlight.current = true;
    setIsDeleting(true);
    setDeleteError('');
    try {
      await deleteSymptomEntry(entry.id);
      onDeleted();
    } catch (error) {
      if (error.status === 404) {
        onMissing();
      } else {
        setDeleteError(error.message);
      }
    } finally {
      deleteInFlight.current = false;
      setIsDeleting(false);
    }
  }

  if (mode === 'edit') {
    return (
      <li className="history-entry">
        <EntryEditForm
          entry={entry}
          timezone={timezone}
          onSaved={() => {
            returnToView(editButton);
            onEdited();
          }}
          onMissing={onMissing}
          onCancel={() => returnToView(editButton)}
        />
      </li>
    );
  }

  return (
    <li className="history-entry">
      <div className="history-entry__summary">
        <h3 className="history-entry__name">{entry.symptom_name}</h3>
        <span className="history-entry__severity">Severity {entry.severity}/10</span>
      </div>
      <p className="history-entry__date">{formatDate(entry.occurred_on)}</p>
      {entry.notes && <p className="history-entry__notes">{entry.notes}</p>}

      {mode === 'confirm-delete' ? (
        <div className="history-entry__confirm" role="group" aria-label="Confirm deletion">
          <p>Delete this entry? This cannot be undone.</p>
          {deleteError && (
            <p className="alert alert--error" role="alert">
              {deleteError}
            </p>
          )}
          <div className="action-row">
            <button
              type="button"
              className="button button--danger"
              disabled={isDeleting}
              onClick={confirmDelete}
            >
              {isDeleting ? 'Deleting…' : 'Delete entry'}
            </button>
            <button
              type="button"
              className="button button--secondary"
              disabled={isDeleting}
              // Focus starts here, so pressing Enter by accident does not delete.
              autoFocus
              onClick={() => returnToView(deleteButton)}
            >
              Keep entry
            </button>
          </div>
        </div>
      ) : (
        <div className="action-row">
          <button
            ref={editButton}
            type="button"
            className="link-button"
            aria-label={`Edit ${entry.symptom_name}, ${formatDate(entry.occurred_on)}`}
            onClick={() => setMode('edit')}
          >
            Edit
          </button>
          <button
            ref={deleteButton}
            type="button"
            className="link-button"
            aria-label={`Delete ${entry.symptom_name}, ${formatDate(entry.occurred_on)}`}
            onClick={() => setMode('confirm-delete')}
          >
            Delete
          </button>
        </div>
      )}
    </li>
  );
}
