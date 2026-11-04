import { useCallback, useEffect, useMemo, useState } from 'react';
import { useResource } from '../symptoms/useResource.js';
import SeverityTrend from './SeverityTrend.jsx';
import SymptomFilters from './SymptomFilters.jsx';
import SymptomHistory from './SymptomHistory.jsx';

const NO_FILTERS = { symptom: '', startDate: '', endDate: '' };
const RANGE_ERROR = 'End date must be on or after the start date';
const NO_SYMPTOMS = [];

function hasInvalidRange({ startDate, endDate }) {
  return Boolean(startDate && endDate && endDate < startDate);
}

// Filters, chart, and history for one patient's records. `source` decides whose records
// these are, and leaving out `entryActions` makes the view read-only.
export default function SymptomRecords({
  source,
  revision,
  onRefresh,
  notice,
  noEntriesText,
  noTrendText,
  headingRef,
  entryActions,
  onFiltersChanged,
  onAccessLost,
}) {
  // What the inputs show, and the last valid version of it that queries use.
  const [draftFilters, setDraftFilters] = useState(NO_FILTERS);
  const [filters, setFilters] = useState(NO_FILTERS);
  const [chartSymptom, setChartSymptom] = useState('');

  const names = useResource(source.fetchNames, revision);
  const symptoms = names.data?.symptoms ?? NO_SYMPTOMS;

  // An edit or delete can remove the filtered symptom, which would leave an empty view
  // with nothing selected. Keep the date filters and fall back to all symptoms.
  const isKnown = (key) => symptoms.some((symptom) => symptom.key === key);
  const availableSymptom = (key) => (names.data && !isKnown(key) ? '' : key);
  const symptomFilter = availableSymptom(filters.symptom);
  const { startDate, endDate } = filters;

  const trendKey = symptomFilter || (isKnown(chartSymptom) ? chartSymptom : symptoms[0]?.key);

  const loadHistory = useCallback(
    (signal) => source.fetchHistory({ symptom: symptomFilter, startDate, endDate }, signal),
    [source, symptomFilter, startDate, endDate],
  );
  const loadTrend = useMemo(() => {
    if (!trendKey) {
      return null;
    }
    return (signal) => source.fetchTrend({ symptom: trendKey, startDate, endDate }, signal);
  }, [source, trendKey, startDate, endDate]);

  const history = useResource(loadHistory, revision);
  const trend = useResource(loadTrend, revision);

  // Resources keep their last data after an error. When access has ended, that data must
  // stop being displayed, so a 404 hides the whole view straight away.
  const accessLost =
    Boolean(onAccessLost) &&
    [names, history, trend].some((resource) => resource.error?.status === 404);

  useEffect(() => {
    if (accessLost) {
      onAccessLost();
    }
  }, [accessLost, onAccessLost]);

  if (accessLost) {
    return null;
  }

  function handleFilterChange(next) {
    setDraftFilters(next);
    onFiltersChanged?.();
    if (!hasInvalidRange(next)) {
      setFilters(next);
    }
  }

  return (
    <>
      <SymptomFilters
        filters={{ ...draftFilters, symptom: availableSymptom(draftFilters.symptom) }}
        symptoms={symptoms}
        rangeError={hasInvalidRange(draftFilters) ? RANGE_ERROR : undefined}
        onChange={handleFilterChange}
        onClear={() => handleFilterChange(NO_FILTERS)}
      />
      <div className="records-grid">
        <SeverityTrend
          symptoms={symptoms}
          selectedKey={trendKey}
          showSelector={!symptomFilter}
          trend={trend}
          dateRange={{ startDate, endDate }}
          noTrendText={noTrendText}
          onSelect={setChartSymptom}
          onRetry={onRefresh}
        />
        <SymptomHistory
          history={history}
          hasFilters={Boolean(symptomFilter || startDate || endDate)}
          noEntriesText={noEntriesText}
          notice={notice}
          headingRef={headingRef}
          entryActions={entryActions}
          onRetry={onRefresh}
        />
      </div>
    </>
  );
}
