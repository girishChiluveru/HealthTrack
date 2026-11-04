import SymptomFields from './SymptomFields.jsx';

export default function SymptomEntryRow({ row, number, today, errors, canRemove, onChange, onRemove }) {
  return (
    <fieldset className="entry-row">
      <legend>Entry {number}</legend>
      {canRemove && (
        <button
          type="button"
          className="link-button entry-row__remove"
          aria-label={`Remove entry ${number}`}
          onClick={() => onRemove(row.id)}
        >
          Remove
        </button>
      )}
      <SymptomFields
        values={row}
        errors={errors}
        today={today}
        onChange={(field, value) => onChange(row.id, field, value)}
      />
    </fieldset>
  );
}
