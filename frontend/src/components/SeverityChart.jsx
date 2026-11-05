import {
  Chart as ChartJS,
  LinearScale,
  LineController,
  LineElement,
  PointElement,
  Tooltip,
} from 'chart.js';
import { useMemo } from 'react';
import { Line } from 'react-chartjs-2';
import { buildChartData, buildChartOptions } from '../symptoms/chartConfig.js';
import { toTableRows } from '../symptoms/chartData.js';
import { formatDate } from '../symptoms/dates.js';
import { useTheme } from '../theme.js';

ChartJS.register(LinearScale, LineController, LineElement, PointElement, Tooltip);

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
function readChartTheme(mode) {
  const styles = getComputedStyle(document.documentElement);
  const token = (name) => styles.getPropertyValue(name).trim();
  return {
    mode,
    grid: token('--color-border'),
    muted: token('--color-muted'),
    surface: token('--color-surface'),
    tooltip: token('--tooltip-bg'),
    tooltipText: token('--tooltip-text'),
    series: [1, 2, 3, 4, 5, 6].map((index) => token(`--series-${index}`)),
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

export default function SeverityChart({ series, dateRange, isRefreshing }) {
  const mode = useTheme();
  const theme = useMemo(() => readChartTheme(mode), [mode]);
  // Stable objects let the chart animate from its current state instead of restarting.
  const data = useMemo(() => buildChartData(series, theme), [series, theme]);
  const options = useMemo(
    () => buildChartOptions(series, dateRange, theme, { animate: !prefersReducedMotion() }),
    [series, dateRange, theme],
  );

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
