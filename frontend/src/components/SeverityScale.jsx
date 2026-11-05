import { useId } from 'react';
import { SEVERITY_LEVELS, severityBand, severityLabel } from '../symptoms/severity.js';

const GUIDANCE = '1 is the mildest and 10 is the most severe.';

export default function SeverityScale({ value, error, onChange }) {
  const id = useId();
  const legendId = `${id}-legend`;
  const hintId = `${id}-hint`;
  const errorId = `${id}-error`;
  const selected = Number(value);
  const describedBy = [hintId, error && errorId].filter(Boolean).join(' ');

  return (
    <fieldset
      className="severity"
      role="radiogroup"
      aria-labelledby={legendId}
      aria-describedby={describedBy}
      aria-required="true"
      aria-invalid={error ? 'true' : undefined}
    >
      <legend id={legendId} className="severity__legend">
        Severity
      </legend>
      <div className="severity__frame">
        <div className="severity__scale">
          {SEVERITY_LEVELS.map((level) => (
            <label
              key={level}
              className={`severity__option severity__option--${severityBand(level)}`}
            >
              <input
                type="radio"
                name={`${id}-severity`}
                value={level}
                checked={selected === level}
                aria-label={`${level} out of 10, ${severityLabel(level).toLowerCase()}`}
                onChange={() => onChange(String(level))}
              />
              <span className="severity__number" aria-hidden="true">
                {level}
              </span>
            </label>
          ))}
        </div>
        <div className="severity__bands" aria-hidden="true">
          <span>Mild</span>
          <span>Moderate</span>
          <span>Severe</span>
        </div>
      </div>
      <p id={hintId} className="field__hint">
        {selected
          ? `Selected ${selected} of 10, ${severityLabel(selected).toLowerCase()}.`
          : GUIDANCE}
      </p>
      {error && (
        <p id={errorId} className="field__error">
          {error}
        </p>
      )}
    </fieldset>
  );
}
