import FormField from './FormField.jsx';

const SEVERITIES = Array.from({ length: 10 }, (_, index) => index + 1);

// The fields of one entry, shared by the create and edit forms.
export default function SymptomFields({ values, errors, today, onChange }) {
  function handleChange(event) {
    onChange(event.target.name, event.target.value);
  }

  return (
    <>
      <FormField
        label="Symptom"
        name="symptom_name"
        autoComplete="off"
        value={values.symptom_name}
        onChange={handleChange}
        error={errors.symptom_name}
      />
      <div className="entry-row__pair">
        <FormField
          label="Date"
          type="date"
          name="occurred_on"
          max={today}
          value={values.occurred_on}
          onChange={handleChange}
          error={errors.occurred_on}
        />
        <FormField
          as="select"
          label="Severity (1–10)"
          name="severity"
          value={values.severity}
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
        value={values.notes}
        onChange={handleChange}
        error={errors.notes}
      />
    </>
  );
}
