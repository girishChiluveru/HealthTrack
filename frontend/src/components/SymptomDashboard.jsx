import { useCallback, useMemo, useRef, useState } from 'react';
import {
  fetchSymptomHistory,
  fetchSymptomNames,
  fetchSymptomTrend,
} from '../api/symptoms.js';
import { useResource } from '../symptoms/useResource.js';
import SeverityTrend from './SeverityTrend.jsx';
import SymptomEntryForm from './SymptomEntryForm.jsx';
import SymptomFilters from './SymptomFilters.jsx';
import SymptomHistory from './SymptomHistory.jsx';

const NO_FILTERS = { symptom: '', startDate: '', endDate: '' };
const RANGE_ERROR = 'End date must be on or after the start date';
const NO_SYMPTOMS = [];

function hasInvalidRange({ startDate, endDate }) {
  return Boolean(startDate && endDate && endDate < startDate);
}

export default function SymptomDashboard({ timezone }) {
  // Every change bumps this one counter, and all three resources refetch from the server.
  const [revision, setRevision] = useState(0);
  // What the inputs show, and the last valid version of it that queries use.
  const [draftFilters, setDraftFilters] = useState(NO_FILTERS);
  const [filters, setFilters] = useState(NO_FILTERS);
  const [chartSymptom, setChartSymptom] = useState('');
  const [notice, setNotice] = useState('');
  const historyHeading = useRef(null);

  const names = useResource(fetchSymptomNames, revision);
  const symptoms = names.data?.symptoms ?? NO_SYMPTOMS;

  // An edit or delete can remove the filtered symptom, which would leave an empty view
  // with nothing selected. Keep the date filters and fall back to all symptoms.
  const isKnown = (key) => symptoms.some((symptom) => symptom.key === key);
  const availableSymptom = (key) => (names.data && !isKnown(key) ? '' : key);
  const symptomFilter = availableSymptom(filters.symptom);
  const { startDate, endDate } = filters;

  const trendKey = symptomFilter || (isKnown(chartSymptom) ? chartSymptom : symptoms[0]?.key);

  const loadHistory = useCallback(
    (signal) => fetchSymptomHistory({ symptom: symptomFilter, startDate, endDate }, signal),
    [symptomFilter, startDate, endDate],
  );
  const loadTrend = useMemo(() => {
    if (!trendKey) {
      return null;
    }
    return (signal) => fetchSymptomTrend({ symptom: trendKey, startDate, endDate }, signal);
  }, [trendKey, startDate, endDate]);

  const history = useResource(loadHistory, revision);
  const trend = useResource(loadTrend, revision);

  const refresh = useCallback(() => setRevision((current) => current + 1), []);

  function handleFilterChange(next) {
    setDraftFilters(next);
    setNotice('');
    if (!hasInvalidRange(next)) {
      setFilters(next);
    }
  }

  function clearFilters() {
    handleFilterChange(NO_FILTERS);
  }

  function handleCreated() {
    setNotice('');
    refresh();
  }

  function handleEdited() {
    setNotice('Entry updated.');
    refresh();
  }

  function handleDeleted() {
    setNotice('Entry deleted.');
    refresh();
    // The focused button is about to disappear with its entry.
    historyHeading.current?.focus();
  }

  function handleMissing() {
    setNotice('That entry no longer exists, so the list has been refreshed.');
    refresh();
  }

  return (
    <>
      <SymptomEntryForm timezone={timezone} onSaved={handleCreated} />
      <SymptomFilters
        filters={{ ...draftFilters, symptom: availableSymptom(draftFilters.symptom) }}
        symptoms={symptoms}
        rangeError={hasInvalidRange(draftFilters) ? RANGE_ERROR : undefined}
        onChange={handleFilterChange}
        onClear={clearFilters}
      />
      <SeverityTrend
        symptoms={symptoms}
        selectedKey={trendKey}
        showSelector={!symptomFilter}
        trend={trend}
        dateRange={{ startDate, endDate }}
        onSelect={setChartSymptom}
        onRetry={refresh}
      />
      <SymptomHistory
        history={history}
        hasFilters={Boolean(symptomFilter || startDate || endDate)}
        notice={notice}
        headingRef={historyHeading}
        timezone={timezone}
        onEdited={handleEdited}
        onDeleted={handleDeleted}
        onMissing={handleMissing}
        onRetry={refresh}
      />
    </>
  );
}
