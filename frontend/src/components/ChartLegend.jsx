import { useState } from 'react';
import { MAX_CHART_LINES } from '../symptoms/useChartSelection.js';

const PREVIEW_COUNT = 8;
const HIDDEN_KEY_COLOR = 'var(--color-input-border)';

const MARKERS = {
  circle: <circle cx="14" cy="6" r="3.5" />,
  rect: <rect x="10.75" y="2.75" width="6.5" height="6.5" />,
  triangle: <path d="M14 2l4 7.5h-8z" />,
  rectRot: <path d="M14 1.75L18.25 6 14 10.25 9.75 6z" />,
};

// A short sample of the line and its marker, so the key also works without color.
function LineKey({ style, isShown }) {
  const color = isShown ? style.color : HIDDEN_KEY_COLOR;
  return (
    <svg className="line-key" width="28" height="12" viewBox="0 0 28 12" aria-hidden="true">
      <line
        x1="1"
        y1="6"
        x2="27"
        y2="6"
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
        strokeDasharray={style.dash.join(' ')}
      />
      <g fill={color}>{MARKERS[style.pointStyle]}</g>
    </svg>
  );
}

// Checkboxes that show or hide each line. Long lists stay short until they are expanded.
export default function ChartLegend({ symptoms, styles, visibleKeys, emptyKeys, onToggle }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const isFull = visibleKeys.length >= MAX_CHART_LINES;
  const listed = isExpanded
    ? symptoms
    : symptoms.filter(({ key }, index) => index < PREVIEW_COUNT || visibleKeys.includes(key));
  const unlisted = symptoms.length - listed.length;

  return (
    <fieldset className="chart-legend">
      <legend className="visually-hidden">Symptoms shown on the chart</legend>
      <ul className="chart-legend__list">
        {listed.map(({ key, name }) => {
          const isShown = visibleKeys.includes(key);
          return (
            <li key={key}>
              <label className="legend-chip" title={name}>
                <input
                  type="checkbox"
                  checked={isShown}
                  disabled={!isShown && isFull}
                  onChange={() => onToggle(key)}
                />
                <LineKey style={styles.get(key)} isShown={isShown} />
                <span className="legend-chip__name">{name}</span>
                {isShown && emptyKeys.includes(key) && (
                  <span className="legend-chip__note">no entries</span>
                )}
              </label>
            </li>
          );
        })}
      </ul>
      {unlisted > 0 && (
        <button type="button" className="link-button" onClick={() => setIsExpanded(true)}>
          Show {unlisted} more
        </button>
      )}
      {isFull && symptoms.length > MAX_CHART_LINES && (
        <p className="field__hint">
          The chart shows up to {MAX_CHART_LINES} symptoms at a time. Hide one to show another.
        </p>
      )}
    </fieldset>
  );
}
