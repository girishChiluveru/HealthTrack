import {
  Chart as ChartJS,
  LinearScale,
  LineController,
  LineElement,
  PointElement,
  Tooltip,
} from 'chart.js';
import { useMemo, useState } from 'react';
import { Line } from 'react-chartjs-2';
import { chartDayRange, toChartPoints, toTableRows } from '../symptoms/chartData.js';
import { formatDate, formatEpochDay } from '../symptoms/dates.js';

ChartJS.register(LinearScale, LineController, LineElement, PointElement, Tooltip);

const DAYS_PER_YEAR = 365;
const UPDATE_MS = 200;
const TOOLTIP_MS = 100;

// Marks the date under the pointer, so readers can aim at a day and not at a thin line.
const CROSSHAIR = {
  id: 'crosshair',
  afterDatasetsDraw({ ctx, chartArea, scales, tooltip }) {
    const point = tooltip?.opacity ? tooltip.dataPoints?.[0] : null;
    if (!point) {
      return;
    }
    ctx.save();
    ctx.strokeStyle = scales.x.options.ticks.color;
    ctx.globalAlpha = 0.4;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(point.element.x, chartArea.top);
    ctx.lineTo(point.element.x, chartArea.bottom);
    ctx.stroke();
    ctx.restore();
  },
};
const PLUGINS = [CROSSHAIR];

function prefersReducedMotion() {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

// Canvas drawing cannot use CSS variables, so the values are read from the stylesheet.
function readChartTheme() {
  const styles = getComputedStyle(document.documentElement);
  const token = (name) => styles.getPropertyValue(name).trim();
  return {
    grid: token('--color-border'),
    muted: token('--color-muted'),
    surface: token('--color-surface'),
    text: token('--color-ink'),
  };
}

function tooltipLabel(item, isSingle) {
  const { entryCount } = item.raw;
  const detail = entryCount > 1 ? ` (highest of ${entryCount} entries)` : '';
  return isSingle
    ? `Severity ${item.parsed.y}${detail}`
    : `${item.parsed.y}  ${item.dataset.label}${detail}`;
}

function buildOptions(series, dateRange, theme) {
  const { min, max } = chartDayRange(
    series.flatMap(({ points }) => points),
    dateRange,
  );
  const includeYear = max - min > DAYS_PER_YEAR;
  const isSingle = series.length === 1;
  const reducedMotion = prefersReducedMotion();

  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: reducedMotion ? false : { duration: UPDATE_MS, easing: 'easeOutQuad' },
    interaction: { mode: 'nearest', axis: 'x', intersect: false },
    scales: {
      x: {
        type: 'linear',
        min,
        max,
        grid: { display: false },
        border: { color: theme.grid },
        ticks: {
          color: theme.muted,
          maxTicksLimit: 6,
          maxRotation: 0,
          precision: 0,
          callback: (day) => formatEpochDay(day, { includeYear }),
        },
      },
      y: {
        min: 1,
        max: 10,
        title: { display: true, text: 'Severity', color: theme.muted },
        grid: { color: theme.grid },
        border: { display: false },
        ticks: { color: theme.muted, stepSize: 1, precision: 0 },
      },
    },
    plugins: {
      tooltip: {
        animation: { duration: reducedMotion ? 0 : TOOLTIP_MS },
        backgroundColor: theme.text,
        titleColor: theme.surface,
        bodyColor: theme.surface,
        padding: 10,
        boxPadding: 4,
        displayColors: !isSingle,
        usePointStyle: true,
        filter: (item) => item.parsed.y !== null,
        itemSort: (a, b) => b.parsed.y - a.parsed.y,
        callbacks: {
          title: ([item]) => (item ? formatEpochDay(item.parsed.x, { includeYear: true }) : ''),
          label: (item) => tooltipLabel(item, isSingle),
        },
      },
    },
  };
}

function buildData(series, theme) {
  const isSingle = series.length === 1;
  return {
    datasets: series.map(({ key, name, points, style }) => ({
      key,
      label: name,
      data: toChartPoints(points),
      borderColor: style.color,
      backgroundColor: style.color,
      borderDash: style.dash,
      borderWidth: 2,
      borderCapStyle: 'round',
      borderJoinStyle: 'round',
      spanGaps: false,
      clip: false,
      pointStyle: style.pointStyle,
      pointRadius: isSingle ? 5 : 4,
      pointHoverRadius: isSingle ? 7 : 6,
      pointHitRadius: 16,
      pointBorderColor: theme.surface,
      pointBorderWidth: isSingle ? 2 : 1,
      pointHoverBorderColor: theme.surface,
      pointHoverBorderWidth: 2,
    })),
  };
}

function describe(series) {
  const dates = series.flatMap(({ points }) => points.map(({ date }) => date)).sort();
  const period = `from ${formatDate(dates[0])} to ${formatDate(dates.at(-1))}`;
  const ranges = series.map(({ name, points }) => {
    const severities = points.map((point) => point.max_severity);
    const lowest = Math.min(...severities);
    const days = points.length === 1 ? '1 day' : `${points.length} days`;
    return `${name} on ${days}, from ${lowest} to ${Math.max(...severities)}`;
  });
  return (
    `Line chart of the highest severity each day, ${period}. ${ranges.join('; ')}. ` +
    'The same data is in the table below.'
  );
}

function SingleTable({ points }) {
  return (
    <table>
      <thead>
        <tr>
          <th scope="col">Date</th>
          <th scope="col">Highest severity</th>
          <th scope="col">Entries</th>
        </tr>
      </thead>
      <tbody>
        {points.map((point) => (
          <tr key={point.date}>
            <td>{formatDate(point.date)}</td>
            <td>{point.max_severity}</td>
            <td>{point.entry_count}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function MultiTable({ series }) {
  return (
    <table>
      <caption className="visually-hidden">
        Highest severity each day. A dash means no entries that day.
      </caption>
      <thead>
        <tr>
          <th scope="col">Date</th>
          {series.map(({ key, name }) => (
            <th key={key} scope="col">
              {name}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {toTableRows(series).map(({ date, cells }) => (
          <tr key={date}>
            <th scope="row">{formatDate(date)}</th>
            {cells.map((point, index) => (
              <td key={series[index].key}>
                {point ? point.max_severity : '–'}
                {point?.entry_count > 1 && (
                  <span className="chart-table__count"> ({point.entry_count} entries)</span>
                )}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// `series` holds at least one symptom, and each symptom has at least one point.
export default function SeverityChart({ series, dateRange, isRefreshing }) {
  const [theme] = useState(readChartTheme);
  // Stable objects let the chart animate from its current state instead of restarting.
  const data = useMemo(() => buildData(series, theme), [series, theme]);
  const options = useMemo(() => buildOptions(series, dateRange, theme), [series, dateRange, theme]);

  return (
    <>
      <div className={isRefreshing ? 'chart chart--refreshing' : 'chart'}>
        <Line
          data={data}
          options={options}
          plugins={PLUGINS}
          datasetIdKey="key"
          role="img"
          aria-label={describe(series)}
        />
      </div>
      <details className="chart-table">
        <summary>View as a table</summary>
        <div className="chart-table__scroll" tabIndex={0} role="region" aria-label="Chart data">
          {series.length === 1 ? (
            <SingleTable points={series[0].points} />
          ) : (
            <MultiTable series={series} />
          )}
        </div>
      </details>
    </>
  );
}
