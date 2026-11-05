import { FileDown } from 'lucide-react';
import { useState } from 'react';
import { todayInTimezone } from '../symptoms/validation.js';

function describeResult(included, total) {
  if (included === 0) {
    return { tone: 'error', message: 'There are no entries to export.' };
  }
  return {
    tone: 'success',
    message:
      included < total
        ? `PDF downloaded with the newest ${included} of ${total} entries.`
        : 'PDF downloaded.',
  };
}

export default function ReportExport({ report, timezone, canExport, onAccessLost }) {
  const [isExporting, setIsExporting] = useState(false);
  const [result, setResult] = useState(null);

  async function handleExport() {
    setIsExporting(true);
    setResult(null);
    try {
      const { exportSymptomReport } = await import('../reports/symptomReport.js');
      const { included, total } = await exportSymptomReport({
        ...report,
        generatedOn: todayInTimezone(timezone),
      });
      setResult(describeResult(included, total));
    } catch (error) {
      if (error.status === 404) {
        onAccessLost?.();
      }
      setResult({ tone: 'error', message: 'The PDF could not be created. Please try again.' });
    } finally {
      setIsExporting(false);
    }
  }

  return (
    <div className="report-export">
      <button
        type="button"
        className="button button--secondary"
        disabled={isExporting || !canExport}
        onClick={handleExport}
      >
        <FileDown size={16} aria-hidden="true" />
        {isExporting ? 'Preparing PDF…' : 'Export PDF'}
      </button>
      <div role="status">
        {result && (
          <p className={`report-export__result report-export__result--${result.tone}`}>
            {result.message}
          </p>
        )}
      </div>
    </div>
  );
}
