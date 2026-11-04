import FormField from './FormField.jsx';
import SeverityChart from './SeverityChart.jsx';

export default function SeverityTrend({
  symptoms,
  selectedKey,
  showSelector,
  trend,
  dateRange,
  onSelect,
  onRetry,
}) {
  const selected = symptoms.find(({ key }) => key === selectedKey);
  // Data from a previous selection must not be drawn under the new symptom's name.
  const points = selectedKey && trend.data?.symptom_key === selectedKey ? trend.data.points : null;

  return (
    <section className="card" aria-labelledby="trend-heading" aria-busy={trend.isLoading}>
      <h2 id="trend-heading">Severity over time</h2>
      {symptoms.length === 0 ? (
        <p className="muted-text">Log a symptom to see its trend here.</p>
      ) : (
        <>
          {showSelector && (
            <FormField
              as="select"
              label="Chart symptom"
              name="chartSymptom"
              value={selectedKey}
              onChange={(event) => onSelect(event.target.value)}
            >
              {symptoms.map(({ key, name }) => (
                <option key={key} value={key}>
                  {name}
                </option>
              ))}
            </FormField>
          )}
          <p className="muted-text">
            {selected?.name}: highest severity each day. Breaks in the line are days with no
            entries.
          </p>
          <div role="status">
            {trend.isLoading && <p className="muted-text">Loading chart…</p>}
          </div>
          {trend.error && (
            <div className="alert alert--error" role="alert">
              <p>We could not load the chart.</p>
              <button type="button" className="link-button" onClick={onRetry}>
                Try again
              </button>
            </div>
          )}
          {points?.length === 0 && !trend.isLoading && (
            <p className="muted-text">No entries for this symptom in the selected dates.</p>
          )}
          {points?.length > 0 && (
            <SeverityChart points={points} symptomName={selected?.name} dateRange={dateRange} />
          )}
        </>
      )}
    </section>
  );
}
