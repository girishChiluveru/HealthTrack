import FormField from './FormField.jsx';
import SeverityScale from './SeverityScale.jsx';

export default function SymptomFields({ values, errors, today, onChange }) {
  function handleChange(event) {
    onChange(event.target.name, event.target.value);
  }

  return (
    <>
      <div className="entry-row__pair">
        <FormField
          label="Symptom"
          name="symptom_name"
          autoComplete="off"
          value={values.symptom_name}
          onChange={handleChange}
          error={errors.symptom_name}
        />
        <FormField
          label="Date"
          type="date"
          name="occurred_on"
          max={today}
          value={values.occurred_on}
          onChange={handleChange}
          error={errors.occurred_on}
        />
      </div>
      <SeverityScale
        value={values.severity}
        error={errors.severity}
        onChange={(severity) => onChange('severity', severity)}
      />
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
