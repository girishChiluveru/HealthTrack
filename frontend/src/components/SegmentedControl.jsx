import { useId } from 'react';

// Native radio buttons underneath, so arrow keys and screen readers work as expected.
export default function SegmentedControl({ label, options, value, onChange }) {
  const name = useId();

  return (
    <fieldset className="segmented" role="radiogroup" aria-label={label}>
      {options.map(({ value: optionValue, label: optionLabel, icon: Glyph }) => (
        <label key={optionValue} className="segmented__option">
          <input
            type="radio"
            name={name}
            value={optionValue}
            checked={value === optionValue}
            onChange={() => onChange(optionValue)}
          />
          <span className="segmented__face">
            {Glyph && <Glyph size={16} aria-hidden="true" />}
            {optionLabel}
          </span>
        </label>
      ))}
    </fieldset>
  );
}
