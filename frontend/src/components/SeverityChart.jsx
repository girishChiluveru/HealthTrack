import {
  Chart as ChartJS,
  LinearScale,
  LineController,
  LineElement,
  PointElement,
  Tooltip,
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import { chartDayRange, toChartPoints } from '../symptoms/chartData.js';
import { formatDate, formatEpochDay } from '../symptoms/dates.js';
import { useChartTheme } from '../symptoms/useChartTheme.js';

ChartJS.register(LinearScale, LineController, LineElement, PointElement, Tooltip);

const DAYS_PER_YEAR = 365;

function buildOptions(points, dateRange, theme) {
  const { min, max } = chartDayRange(points, dateRange);
  const includeYear = max - min > DAYS_PER_YEAR;

  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
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
        backgroundColor: theme.text,
        titleColor: theme.surface,
        bodyColor: theme.surface,
        displayColors: false,
        filter: (item) => item.parsed.y !== null,
        callbacks: {
          title: ([item]) => (item ? formatEpochDay(item.parsed.x, { includeYear: true }) : ''),
          label: (item) => {
            const { entryCount } = item.raw;
            return entryCount > 1
              ? `Severity ${item.parsed.y} (highest of ${entryCount} entries)`
              : `Severity ${item.parsed.y}`;
          },
        },
      },
    },
  };
}

function buildData(points, symptomName, theme) {
  return {
    datasets: [
      {
        label: symptomName,
        data: toChartPoints(points),
        borderColor: theme.line,
        backgroundColor: theme.line,
        borderWidth: 2,
        borderCapStyle: 'round',
        borderJoinStyle: 'round',
        spanGaps: false,
        clip: false,
        pointRadius: 5,
        pointHoverRadius: 7,
        pointHitRadius: 16,
        pointBorderColor: theme.surface,
        pointBorderWidth: 2,
        pointHoverBorderColor: theme.surface,
        pointHoverBorderWidth: 2,
      },
    ],
  };
}

function describe(points, symptomName) {
  const severities = points.map((point) => point.max_severity);
  return (
    `Line chart of ${symptomName} severity on ${points.length} days, ` +
    `from ${formatDate(points[0].date)} to ${formatDate(points.at(-1).date)}. ` +
    `Daily highest severity ranges from ${Math.min(...severities)} to ` +
    `${Math.max(...severities)}. The same data is in the table below.`
  );
}

export default function SeverityChart({ points, symptomName, dateRange }) {
  const theme = useChartTheme();

  return (
    <>
      <div className="chart">
        <Line
          data={buildData(points, symptomName, theme)}
          options={buildOptions(points, dateRange, theme)}
          role="img"
          aria-label={describe(points, symptomName)}
        />
      </div>
      <details className="chart-table">
        <summary>View as a table</summary>
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
      </details>
    </>
  );
}
