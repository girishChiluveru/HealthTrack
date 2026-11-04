import { useCallback, useEffect, useMemo, useState } from 'react';
import { assignSymptomStyles } from '../symptoms/severity.js';
import { useChartSelection } from '../symptoms/useChartSelection.js';
import { useResource } from '../symptoms/useResource.js';
import { useTrendSeries } from '../symptoms/useTrendSeries.js';
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
  noEntriesText,
  noTrendText,
  headingRef,
  entryActions,
  onAccessLost,
}) {
  // What the inputs show, and the last valid version of it that queries use.
  const [draftFilters, setDraftFilters] = useState(NO_FILTERS);
  const [filters, setFilters] = useState(NO_FILTERS);
  const [chartMode, setChartMode] = useState('all');
  const [chartSymptom, setChartSymptom] = useState('');

  const names = useResource(source.fetchNames, revision);
  const symptoms = names.data?.symptoms ?? NO_SYMPTOMS;
  const styles = useMemo(() => assignSymptomStyles(symptoms.map(({ key }) => key)), [symptoms]);
  const { visibleKeys, toggle } = useChartSelection(symptoms);

  // An edit or delete can remove the filtered symptom, which would leave an empty view
  // with nothing selected. Keep the date filters and fall back to all symptoms.
  const isKnown = (key) => symptoms.some((symptom) => symptom.key === key);
  const availableSymptom = (key) => (names.data && !isKnown(key) ? '' : key);
  const symptomFilter = availableSymptom(filters.symptom);
  const { startDate, endDate } = filters;

  // Filtering to one symptom narrows the chart too. The chosen view returns when it is cleared.
  const singleKey = symptomFilter || (isKnown(chartSymptom) ? chartSymptom : symptoms[0]?.key);
  const showAll = chartMode === 'all' && !symptomFilter && symptoms.length > 1;
  const chartKeys = useMemo(() => {
    if (showAll) {
      return visibleKeys;
    }
    return singleKey ? [singleKey] : NO_SYMPTOMS;
  }, [showAll, visibleKeys, singleKey]);

  const loadHistory = useCallback(
    (signal) => source.fetchHistory({ symptom: symptomFilter, startDate, endDate }, signal),
    [source, symptomFilter, startDate, endDate],
  );

  const history = useResource(loadHistory, revision);
  const trend = useTrendSeries(source, chartKeys, filters, revision);

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
          isLoadingSymptoms={names.isLoading && !names.data}
          styles={styles}
          mode={showAll ? 'all' : 'single'}
          isFiltered={Boolean(symptomFilter)}
          selectedKey={singleKey}
          chartKeys={chartKeys}
          trend={trend}
          noTrendText={noTrendText}
          onModeChange={setChartMode}
          onSelect={setChartSymptom}
          onToggle={toggle}
          onRetry={onRefresh}
        />
        <SymptomHistory
          history={history}
          hasFilters={Boolean(symptomFilter || startDate || endDate)}
          noEntriesText={noEntriesText}
          headingRef={headingRef}
          entryActions={entryActions}
          onRetry={onRefresh}
        />
      </div>
    </>
  );
}
