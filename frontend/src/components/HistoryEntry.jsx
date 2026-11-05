import { CalendarDays, Pencil, Trash2 } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { flushSync } from 'react-dom';
import { deleteSymptomEntry } from '../api/symptoms.js';
import { formatDate } from '../symptoms/dates.js';
import { severityBand } from '../symptoms/severity.js';
import ConfirmDialog from './ConfirmDialog.jsx';
import EntryEditForm from './EntryEditForm.jsx';
import IconButton from './IconButton.jsx';

export default function HistoryEntry({ entry, actions }) {
  const { timezone, onEdited, onDeleted, onMissing } = actions ?? {};
  const [mode, setMode] = useState('view');
  const [deleteError, setDeleteError] = useState('');
  const [isDeleting, setIsDeleting] = useState(false);
  const deleteInFlight = useRef(false);
  const editButton = useRef(null);
  const shouldRestoreFocus = useRef(false);
  const date = formatDate(entry.occurred_on);

  // Editing replaces the buttons, so focus has to be put back afterwards.
  useEffect(() => {
    if (mode === 'view' && shouldRestoreFocus.current) {
      editButton.current?.focus();
      shouldRestoreFocus.current = false;
    }
  }, [mode]);

  function leaveEditing() {
    shouldRestoreFocus.current = true;
    setMode('view');
  }

  function closeDialog() {
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
      // A modal dialog blocks focus elsewhere, so it must close before the parent moves focus.
      flushSync(closeDialog);
      onDeleted();
    } catch (error) {
      if (error.status === 404) {
        flushSync(closeDialog);
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
          onSaved={(updated) => {
            leaveEditing();
            onEdited(entry, updated);
          }}
          onMissing={onMissing}
          onCancel={leaveEditing}
        />
      </li>
    );
  }

  return (
    <li className="history-entry">
      <div className="history-entry__summary">
        <h3 className="history-entry__name">{entry.symptom_name}</h3>
        <span
          className={`history-entry__severity history-entry__severity--${severityBand(entry.severity)}`}
        >
          Severity {entry.severity}/10
        </span>
      </div>
      <div className="history-entry__meta">
        <p className="history-entry__date">
          <CalendarDays size={15} aria-hidden="true" />
          {date}
        </p>
        {actions && (
          <div className="history-entry__actions">
            <IconButton
              ref={editButton}
              label={`Edit ${entry.symptom_name}, ${date}`}
              icon={Pencil}
              onClick={() => setMode('edit')}
            />
            <IconButton
              label={`Delete ${entry.symptom_name}, ${date}`}
              icon={Trash2}
              danger
              onClick={() => setMode('confirm-delete')}
            />
          </div>
        )}
      </div>
      {entry.notes && <p className="history-entry__notes">{entry.notes}</p>}

      {mode === 'confirm-delete' && (
        <ConfirmDialog
          title="Delete this entry?"
          confirmLabel="Delete entry"
          busyLabel="Deleting…"
          cancelLabel="Keep entry"
          isBusy={isDeleting}
          error={deleteError}
          onConfirm={confirmDelete}
          onCancel={closeDialog}
        >
          <p>
            {entry.symptom_name}, severity {entry.severity}/10, on {date}. This cannot be undone.
          </p>
        </ConfirmDialog>
      )}
    </li>
  );
}
