import { Sparkles } from 'lucide-react';
import { useState } from 'react';
import { createInsights } from '../api/symptoms.js';
import { formatDate } from '../symptoms/dates.js';

const DIRECTION_LABELS = {
  higher: 'Higher',
  lower: 'Lower',
  steady: 'About the same',
  'not enough data': 'Not enough data',
};

const STATUS_MESSAGES = {
  insufficient_data: 'There is not enough data yet. Log entries on at least 3 days in this period.',
  not_configured:
    'AI insights are not set up on this server, so no AI text is shown. The figures below come ' +
    'straight from your entries.',
  unavailable:
    'The AI service is unavailable right now, so no AI text is shown. The figures below come ' +
    'straight from your entries.',
};

function FiguresTable({ data }) {
  return (
    <div className="insights__figures">
      <h3>Recorded figures</h3>
      <p className="field__hint">
        Calculated from your entries for {formatDate(data.start_date)} to{' '}
        {formatDate(data.end_date)}, using each day’s highest severity. Not written by AI.
      </p>
      <div className="chart-table__scroll chart-table" tabIndex={0} role="region" aria-label="Recorded figures">
        <table>
          <thead>
            <tr>
              <th scope="col">Symptom</th>
              <th scope="col">Days</th>
              <th scope="col">Range</th>
              <th scope="col">Later half</th>
            </tr>
          </thead>
          <tbody>
            {data.symptoms.map((item) => (
              <tr key={item.name}>
                <th scope="row">{item.name}</th>
                <td>{item.days_logged}</td>
                <td>
                  {item.lowest}–{item.highest}
                </td>
                <td>{DIRECTION_LABELS[item.direction]}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {data.omitted_symptom_count > 0 && (
        <p className="field__hint">
          {data.omitted_symptom_count} less frequently logged symptoms are not included.
        </p>
      )}
    </div>
  );
}

export default function SymptomInsights({ filters, filterName, revision }) {
  const [result, setResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [failedScope, setFailedScope] = useState(null);

  const { symptom, startDate, endDate } = filters;
  const scope = `${revision}|${symptom}|${startDate}|${endDate}`;
  // A result describes the records it was made from, so it is dropped once they change.
  const data = result?.scope === scope ? result.data : null;
  const hasFailed = failedScope === scope;

  async function generate() {
    setIsLoading(true);
    setFailedScope(null);
    try {
      setResult({ scope, data: await createInsights(filters) });
    } catch {
      setFailedScope(scope);
    } finally {
      setIsLoading(false);
    }
  }

  let period = 'the last 30 days';
  if (startDate) {
    period = 'your selected dates';
  } else if (endDate) {
    period = 'the 30 days up to your end date';
  }

  return (
    <section className="card insights" aria-labelledby="insights-heading" aria-busy={isLoading}>
      <h2 id="insights-heading">AI insights</h2>
      <p className="muted-text">
        A summary of {filterName ?? 'your symptoms'} over {period}. This is information only, not
        a medical diagnosis. Please speak to a qualified healthcare professional about any
        medical concerns.
      </p>
      <p className="field__hint">
        When an AI provider is set up, generating sends your symptom names and calculated figures
        to it. Your notes, dates, name, and email are not sent.
      </p>
      <button type="button" className="button insights__action" disabled={isLoading} onClick={generate}>
        <Sparkles size={16} aria-hidden="true" />
        {isLoading ? 'Generating…' : data ? 'Generate again' : 'Generate insights'}
      </button>

      <div role="status">
        {hasFailed && (
          <p className="alert alert--error">
            Insights could not be generated. Everything else still works, and you can try again.
          </p>
        )}
        {data && data.status !== 'ok' && <p className="alert">{STATUS_MESSAGES[data.status]}</p>}
      </div>

      {data?.summary && (
        <>
          <div className="insights__block">
            <h3>Observed in your entries</h3>
            <ul>
              {data.summary.observations.map((text) => (
                <li key={text}>{text}</li>
              ))}
            </ul>
          </div>
          {data.summary.general_wellness.length > 0 && (
            <div className="insights__block insights__block--general">
              <h3>General wellness information</h3>
              <p className="field__hint">General tips, not based on your health or advice for you.</p>
              <ul>
                {data.summary.general_wellness.map((text) => (
                  <li key={text}>{text}</li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
      {data && data.symptoms.length > 0 && data.status !== 'insufficient_data' && (
        <FiguresTable data={data} />
      )}
    </section>
  );
}
