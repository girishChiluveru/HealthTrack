import FormField from './FormField.jsx';

export default function SymptomFilters({ filters, symptoms, rangeError, onChange, onClear }) {
  function handleChange(event) {
    onChange({ ...filters, [event.target.name]: event.target.value });
  }

  const hasFilters = filters.symptom || filters.startDate || filters.endDate;

  return (
    <section className="card filters" aria-label="Filter history and chart">
      <FormField
        as="select"
        label="Symptom"
        name="symptom"
        value={filters.symptom}
        onChange={handleChange}
      >
        <option value="">All symptoms</option>
        {symptoms.map(({ key, name }) => (
          <option key={key} value={key}>
            {name}
          </option>
        ))}
      </FormField>
      <FormField
        label="From"
        type="date"
        name="startDate"
        value={filters.startDate}
        onChange={handleChange}
      />
      <FormField
        label="To"
        type="date"
        name="endDate"
        value={filters.endDate}
        onChange={handleChange}
        error={rangeError}
      />
      <button
        type="button"
        className="button button--secondary filters__clear"
        disabled={!hasFilters}
        onClick={onClear}
      >
        Clear filters
      </button>
    </section>
  );
}
