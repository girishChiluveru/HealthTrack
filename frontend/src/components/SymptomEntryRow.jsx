import FormField from './FormField.jsx';

const SEVERITIES = Array.from({ length: 10 }, (_, index) => index + 1);

export default function SymptomEntryRow({ row, number, today, errors, canRemove, onChange, onRemove }) {
  function handleChange(event) {
    onChange(row.id, event.target.name, event.target.value);
  }

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
      <FormField
        label="Symptom"
        name="symptom_name"
        autoComplete="off"
        value={row.symptom_name}
        onChange={handleChange}
        error={errors.symptom_name}
      />
      <div className="entry-row__pair">
        <FormField
          label="Date"
          type="date"
          name="occurred_on"
          max={today}
          value={row.occurred_on}
          onChange={handleChange}
          error={errors.occurred_on}
        />
        <FormField
          as="select"
          label="Severity (1–10)"
          name="severity"
          value={row.severity}
          onChange={handleChange}
          error={errors.severity}
        >
          <option value="">Select</option>
          {SEVERITIES.map((severity) => (
            <option key={severity} value={severity}>
              {severity}
            </option>
          ))}
        </FormField>
      </div>
      <FormField
        as="textarea"
        label="Notes (optional)"
        name="notes"
        rows={2}
        value={row.notes}
        onChange={handleChange}
        error={errors.notes}
      />
    </fieldset>
  );
}
