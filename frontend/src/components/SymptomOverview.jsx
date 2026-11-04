import { CalendarDays } from 'lucide-react';
import { useCallback, useMemo } from 'react';
import { addDays, formatDate, listDays } from '../symptoms/dates.js';
import { assignSymptomStyles } from '../symptoms/severity.js';
import { useResource } from '../symptoms/useResource.js';
import { todayInTimezone } from '../symptoms/validation.js';
import Skeleton from './Skeleton.jsx';
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
  const { name, points, color } = symptom;
  const change = changeSummary(points);

  return (
    <article className="symptom-tile" style={{ '--symptom': color }}>
      <h3 className="symptom-tile__name">{name}</h3>
      <span className="symptom-tile__initial" aria-hidden="true">
        {name[0].toUpperCase()}
      </span>
      <p className="symptom-tile__value">
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
      // Styled from the full list, so a symptom has the same color here and on the chart.
      const styles = assignSymptomStyles(symptoms.map(({ key }) => key));
      const recent = symptoms.slice(0, MAX_SYMPTOMS);
      const trends = await Promise.all(
        recent.map(({ key }) =>
          source.fetchTrend({ symptom: key, startDate, endDate: today }, signal),
        ),
      );
      return recent
        .map((symptom, index) => ({
          ...symptom,
          points: trends[index].points,
          color: styles.get(symptom.key).color,
        }))
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
          <span className="date-chip">
            <CalendarDays size={16} aria-hidden="true" />
            {formatDate(today)}
          </span>
        </div>
        <p className="card__intro">Each symptom’s most recent daily severity.</p>
        {overview.isLoading && !symptoms && (
          <Skeleton
            label="Loading summary…"
            count={4}
            className="skeleton--tile"
            groupClassName="symptom-tiles"
          />
        )}
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
      {overview.isLoading && !symptoms && (
        <section className="card" aria-hidden="true">
          <div className="skeleton skeleton--panel" />
        </section>
      )}
      {symptoms?.length > 0 && <SymptomPulse symptoms={symptoms} dates={dates} />}
    </div>
  );
}
