import { formatDate } from '../symptoms/dates.js';
import { severityBand, severityLabel } from '../symptoms/severity.js';

const LEGEND = [
  { label: 'Mild', color: 'var(--severity-mild)' },
  { label: 'Moderate', color: 'var(--severity-moderate)' },
  { label: 'Severe', color: 'var(--severity-severe)' },
];

export function PulseStrip({ days }) {
  return (
    <div className="pulse-strip">
      {days.map(({ key, severity, title }) => (
        <span
          key={key}
          title={title}
          className={`pulse-day pulse-day--${severity ? severityBand(severity) : 'none'}`}
        />
      ))}
    </div>
  );
}

function toDays(dates, points) {
  const severityByDate = new Map(points.map((point) => [point.date, point.max_severity]));
  return dates.map((date) => {
    const severity = severityByDate.get(date) ?? null;
    return {
      key: date,
      severity,
      title: `${formatDate(date)}: ${severity ? `severity ${severity}/10` : 'no entries'}`,
    };
  });
}

function describe(name, points, dayCount) {
  const logged = points.map((p) => `${formatDate(p.date)}: ${p.max_severity}`).join(', ');
  return `${name}, highest severity each day. Logged on ${points.length} of the last ${dayCount} days. ${logged}.`;
}

export default function SymptomPulse({ symptoms, dates }) {
  return (
    <section className="card" aria-labelledby="pulse-heading">
      <h2 id="pulse-heading">Symptom pulse</h2>
      <p className="card__intro">The highest severity each day, over the last 14 days.</p>
      <ul className="pulse-legend" aria-label="Severity colors">
        {LEGEND.map(({ label, color }) => (
          <li key={label}>
            <span className="pulse-legend__swatch" style={{ background: color }} />
            {label}
          </li>
        ))}
        <li>
          <span
            className="pulse-legend__swatch pulse-day--none"
            style={{ borderRadius: '50%' }}
          />
          No entries
        </li>
      </ul>
      {symptoms.slice(0, 3).map(({ key, name, points }) => {
        const latest = points.at(-1).max_severity;
        return (
          <div key={key} className="pulse-row">
            <div className="pulse-row__header">
              <h3 className="pulse-row__name">{name}</h3>
              <span className="pulse-row__latest">
                {severityLabel(latest)}, {latest}/10
              </span>
            </div>
            <div role="img" aria-label={describe(name, points, dates.length)}>
              <PulseStrip days={toDays(dates, points)} />
            </div>
            <div className="pulse-row__ends">
              <span>{formatDate(dates[0])}</span>
              <span>Today</span>
            </div>
          </div>
        );
      })}
    </section>
  );
}
