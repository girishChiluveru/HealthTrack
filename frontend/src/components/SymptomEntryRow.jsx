import { X } from 'lucide-react';
import IconButton from './IconButton.jsx';
import SymptomFields from './SymptomFields.jsx';

export default function SymptomEntryRow({ row, number, today, errors, canRemove, onChange, onRemove }) {
  return (
    <fieldset className="entry-row">
      <legend>Entry {number}</legend>
      {canRemove && (
        <div className="entry-row__remove">
          <IconButton
            label={`Remove entry ${number}`}
            icon={X}
            onClick={() => onRemove(row.id)}
          />
        </div>
      )}
      <SymptomFields
        values={row}
        errors={errors}
        today={today}
        onChange={(field, value) => onChange(row.id, field, value)}
      />
    </fieldset>
  );
}
