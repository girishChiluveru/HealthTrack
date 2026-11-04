import { useCallback, useMemo } from 'react';
import { addDays, formatDate, listDays } from '../symptoms/dates.js';
import { symptomColor } from '../symptoms/severity.js';
import { useResource } from '../symptoms/useResource.js';
import { todayInTimezone } from '../symptoms/validation.js';
import SymptomPulse from './SymptomPulse.jsx';

const WINDOW_DAYS = 14;
const MAX_SYMPTOMS = 6;

function changeSummary(points) {
  if (points.length < 2) {
    return { text: 'Only entry in 14 days', tone: '' };
  }
  const change = points.at(-1).max_severity - points.at(-2).max_severity;
  const since = formatDate(points.at(-2).date);
  if (change === 0) {
    return { text: `No change since ${since}`, tone: '' };
  }
  return change > 0
    ? { text: `+${change} since ${since}`, tone: 'pill--worse' }
    : { text: `${change} since ${since}`, tone: 'pill--better' };
}

function SymptomTile({ symptom }) {
  const { key, name, points } = symptom;
  const color = symptomColor(key);
  const change = changeSummary(points);

  return (
    <article className="symptom-tile">
      <h3 className="symptom-tile__name">{name}</h3>
      <span className="symptom-tile__initial" style={{ color }} aria-hidden="true">
        {name[0].toUpperCase()}
      </span>
      <p className="symptom-tile__value" style={{ color }}>
        {points.at(-1).max_severity}
        <span className="symptom-tile__scale">/10</span>
      </p>
      <p className="symptom-tile__change">
        <span className={`pill ${change.tone}`}>{change.text}</span>
      </p>
    </article>
  );
}

// The latest severities and a 14-day view. Daily maximums come from the trend API.
export default function SymptomOverview({ source, revision, timezone, onLogSymptoms, onRetry }) {
  const today = todayInTimezone(timezone);
  const startDate = addDays(today, 1 - WINDOW_DAYS);
  const dates = useMemo(() => listDays(startDate, WINDOW_DAYS), [startDate]);

  const load = useCallback(
    async (signal) => {
      const { symptoms } = await source.fetchNames(signal);
      const recent = symptoms.slice(0, MAX_SYMPTOMS);
      const trends = await Promise.all(
        recent.map(({ key }) =>
          source.fetchTrend({ symptom: key, startDate, endDate: today }, signal),
        ),
      );
      return recent
        .map((symptom, index) => ({ ...symptom, points: trends[index].points }))
        .filter(({ points }) => points.length > 0);
    },
    [source, startDate, today],
  );

  const overview = useResource(load, revision);

  // A doctor who has lost access must not keep seeing the earlier data.
  if (overview.error?.status === 404) {
    return null;
  }

  const symptoms = overview.data;

  return (
    <div className="overview-grid">
      <section className="card" aria-labelledby="summary-heading" aria-busy={overview.isLoading}>
        <div className="card__header">
          <h2 id="summary-heading">Latest summary</h2>
          <span className="date-chip">{formatDate(today)}</span>
        </div>
        <p className="card__intro">Each symptom’s most recent daily severity.</p>
        {overview.error && (
          <div className="alert alert--error" role="alert">
            <p>The summary could not be loaded.</p>
            <button type="button" className="link-button" onClick={onRetry}>
              Try again
            </button>
          </div>
        )}
        {symptoms?.length === 0 && (
          <p className="muted-text">No symptoms logged in the last 14 days.</p>
        )}
        {symptoms?.length > 0 && (
          <div className="symptom-tiles">
            {symptoms.map((symptom) => (
              <SymptomTile key={symptom.key} symptom={symptom} />
            ))}
          </div>
        )}
        {onLogSymptoms && (
          <div className="callout">
            <div>
              <h3>Anything to add today?</h3>
              <p>Logging regularly makes your trends easier to read.</p>
            </div>
            <button type="button" className="button" onClick={onLogSymptoms}>
              Open symptom log
            </button>
          </div>
        )}
      </section>
      {symptoms?.length > 0 && <SymptomPulse symptoms={symptoms} dates={dates} />}
    </div>
  );
}
