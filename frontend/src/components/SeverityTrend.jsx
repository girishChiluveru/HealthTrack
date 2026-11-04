import { ChartLine, ChartSpline } from 'lucide-react';
import { useMemo } from 'react';
import ChartLegend from './ChartLegend.jsx';
import FormField from './FormField.jsx';
import SegmentedControl from './SegmentedControl.jsx';
import SeverityChart from './SeverityChart.jsx';
import Skeleton from './Skeleton.jsx';

const MODE_OPTIONS = [
  { value: 'all', label: 'All symptoms', icon: ChartSpline },
  { value: 'single', label: 'One symptom', icon: ChartLine },
];

export default function SeverityTrend({
  symptoms,
  isLoadingSymptoms,
  styles,
  mode,
  isFiltered,
  selectedKey,
  chartKeys,
  trend,
  noTrendText,
  onModeChange,
  onSelect,
  onToggle,
  onRetry,
}) {
  const isAll = mode === 'all';
  const hasData = Boolean(trend.data);

  // Only symptoms still selected are drawn, so data from a previous selection never is.
  const loaded = useMemo(() => {
    const names = new Map(symptoms.map(({ key, name }) => [key, name]));
    return (trend.data?.series ?? [])
      .filter(({ key }) => chartKeys.includes(key) && names.has(key))
      .map((item) => ({ ...item, name: names.get(item.key), style: styles.get(item.key) }));
  }, [trend.data, chartKeys, symptoms, styles]);
  const series = useMemo(() => loaded.filter(({ points }) => points.length > 0), [loaded]);
  const emptyKeys = useMemo(
    () => loaded.filter(({ points }) => points.length === 0).map(({ key }) => key),
    [loaded],
  );

  function renderChart() {
    if (isAll && chartKeys.length === 0) {
      return <p className="chart-empty">Choose at least one symptom to chart.</p>;
    }
    if (series.length > 0) {
      return (
        <SeverityChart
          series={series}
          dateRange={trend.data.dateRange}
          isRefreshing={trend.isLoading}
        />
      );
    }
    if (trend.isLoading) {
      return <Skeleton label="Loading chart…" className="skeleton--chart" />;
    }
    if (hasData) {
      return (
        <p className="chart-empty">
          {isAll
            ? 'No entries for these symptoms in the selected dates.'
            : 'No entries for this symptom in the selected dates.'}
        </p>
      );
    }
    return null;
  }

  return (
    <section className="card" aria-labelledby="trend-heading" aria-busy={trend.isLoading}>
      <div className="card__header">
        <h2 id="trend-heading">Severity over time</h2>
        {symptoms.length > 1 && !isFiltered && (
          <SegmentedControl
            label="Chart view"
            options={MODE_OPTIONS}
            value={mode}
            onChange={onModeChange}
          />
        )}
      </div>

      {isLoadingSymptoms && <Skeleton label="Loading chart…" className="skeleton--chart" />}
      {!isLoadingSymptoms && symptoms.length === 0 && (
        <p className="muted-text">{noTrendText}</p>
      )}
      {symptoms.length > 0 && (
        <>
          {!isAll && !isFiltered && symptoms.length > 1 && (
            <FormField
              as="select"
              label="Chart symptom"
              name="chartSymptom"
              value={selectedKey}
              onChange={(event) => onSelect(event.target.value)}
            >
              {symptoms.map(({ key, name }) => (
                <option key={key} value={key}>
                  {name}
                </option>
              ))}
            </FormField>
          )}
          <p className="muted-text chart-note">
            {isFiltered && 'Showing the filtered symptom. Clear the filter to compare symptoms. '}
            The highest severity each day. Breaks in a line are days with no entries.
          </p>
          {isAll && (
            <ChartLegend
              symptoms={symptoms}
              styles={styles}
              visibleKeys={chartKeys}
              emptyKeys={emptyKeys}
              onToggle={onToggle}
            />
          )}
          {trend.error && (
            <div className="alert alert--error" role="alert">
              <p>We could not load the chart.</p>
              <button type="button" className="link-button" onClick={onRetry}>
                Try again
              </button>
            </div>
          )}
          {renderChart()}
        </>
      )}
    </section>
  );
}
