import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { assignSymptomStyles } from '../symptoms/severity.js';
import { useChartSelection } from '../symptoms/useChartSelection.js';
import { useResource } from '../symptoms/useResource.js';
import { useTrendSeries } from '../symptoms/useTrendSeries.js';
import ReportExport from './ReportExport.jsx';
import SeverityTrend from './SeverityTrend.jsx';
import SymptomFilters from './SymptomFilters.jsx';
import SymptomHistory from './SymptomHistory.jsx';
import SymptomInsights from './SymptomInsights.jsx';

const NO_FILTERS = { symptom: '', startDate: '', endDate: '' };
const RANGE_ERROR = 'End date must be on or after the start date';
const NO_SYMPTOMS = [];

const PAGE_SIZE = 25;

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
  patientName,
  timezone,
  showInsights = false,
  onAccessLost,
}) {
  const [draftFilters, setDraftFilters] = useState(NO_FILTERS);
  const [filters, setFilters] = useState(NO_FILTERS);
  const [chartMode, setChartMode] = useState('all');
  const [chartSymptom, setChartSymptom] = useState('');
  const [page, setPage] = useState(1);
  const [renames, setRenames] = useState({});
  const ownHeading = useRef(null);
  const historyHeading = headingRef ?? ownHeading;

  const names = useResource(source.fetchNames, revision);
  const symptoms = names.data?.symptoms ?? NO_SYMPTOMS;
  const styles = useMemo(() => assignSymptomStyles(symptoms.map(({ key }) => key)), [symptoms]);
  const { visibleKeys, toggle } = useChartSelection(symptoms);

  // An edit or delete can remove a selected symptom. A rename carries the selection over.
  // Otherwise it is cleared, which keeps the date filters and shows all symptoms.
  const isKnown = (key) => symptoms.some((symptom) => symptom.key === key);
  const availableSymptom = (key) => {
    if (!names.data || isKnown(key)) {
      return key;
    }
    const seen = new Set();
    let current = key;
    while (renames[current] && !seen.has(current)) {
      seen.add(current);
      current = renames[current];
      if (isKnown(current)) {
        return current;
      }
    }
    return '';
  };
  const symptomFilter = availableSymptom(filters.symptom);
  const { startDate, endDate } = filters;

  // Filtering to one symptom narrows the chart too. The chosen view returns when it is cleared.
  const singleKey = symptomFilter || availableSymptom(chartSymptom) || symptoms[0]?.key;
  const showAll = chartMode === 'all' && !symptomFilter && symptoms.length > 1;
  const chartKeys = useMemo(() => {
    if (showAll) {
      return visibleKeys;
    }
    return singleKey ? [singleKey] : NO_SYMPTOMS;
  }, [showAll, visibleKeys, singleKey]);

  const loadHistory = useCallback(
    async (signal) => {
      const query = { symptom: symptomFilter, startDate, endDate, pageSize: PAGE_SIZE };
      const result = await source.fetchHistory({ ...query, page }, signal);
      // Deleting the last entry on the last page leaves that page empty.
      if (result.entries.length === 0 && result.total > 0) {
        setPage(Math.ceil(result.total / PAGE_SIZE));
      }
      return result;
    },
    [source, symptomFilter, startDate, endDate, page],
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
      setPage(1);
    }
  }

  function handlePageChange(next) {
    setPage(next);
    historyHeading.current?.focus();
  }

  const actions = entryActions && {
    ...entryActions,
    onEdited: (previous, updated) => {
      if (previous.symptom_key !== updated.symptom_key) {
        setRenames((current) => ({
          ...current,
          [previous.symptom_key]: updated.symptom_key,
        }));
      }
      entryActions.onEdited();
    },
  };

  const recordFilters = { symptom: symptomFilter, startDate, endDate };
  const filterName = symptoms.find(({ key }) => key === symptomFilter)?.name;
  const rangeIsValid = !hasInvalidRange(draftFilters);

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
        <div>
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
        {showInsights && (
          <SymptomInsights
            filters={recordFilters}
            filterName={filterName}
            revision={revision}
          />
        )}
        </div>
        <SymptomHistory
          history={history}
          hasFilters={Boolean(symptomFilter || startDate || endDate)}
          noEntriesText={noEntriesText}
          headingRef={historyHeading}
          entryActions={actions}
          headerAction={
            <ReportExport
              report={{ source, filters: recordFilters, filterName, styles, patientName }}
              timezone={timezone}
              canExport={rangeIsValid && history.data?.total > 0}
              onAccessLost={onAccessLost}
            />
          }
          onPageChange={handlePageChange}
          onRetry={onRefresh}
        />
      </div>
    </>
  );
}
