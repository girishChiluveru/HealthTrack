import { chartDayRange, toChartPoints } from './chartData.js';
import { formatEpochDay } from './dates.js';

const DAYS_PER_YEAR = 365;
const UPDATE_MS = 200;
const TOOLTIP_MS = 100;

// Reports are printed on white whatever the app's theme, so they have their own values.
// The series match --series-1 to --series-6 of the light theme.
export const PRINT_THEME = {
  grid: '#e7e4f3',
  muted: '#5e5b78',
  surface: '#ffffff',
  tooltip: '#17142e',
  tooltipText: '#ffffff',
  series: ['#5b3fe0', '#931a1a', '#7ca00d', '#0b8466', '#239ec7', '#931a93'],
};

function tooltipLabel(item, isSingle) {
  const { entryCount } = item.raw;
  const detail = entryCount > 1 ? ` (highest of ${entryCount} entries)` : '';
  return isSingle
    ? `Severity ${item.parsed.y}${detail}`
    : `${item.parsed.y}  ${item.dataset.label}${detail}`;
}

export function buildChartOptions(series, dateRange, theme, { animate, fontSize } = {}) {
  const { min, max } = chartDayRange(
    series.flatMap(({ points }) => points),
    dateRange,
  );
  const includeYear = max - min > DAYS_PER_YEAR;
  const isSingle = series.length === 1;
  const font = fontSize ? { size: fontSize } : undefined;

  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: animate ? { duration: UPDATE_MS, easing: 'easeOutQuad' } : false,
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
          font,
          maxTicksLimit: 6,
          maxRotation: 0,
          precision: 0,
          callback: (day) => formatEpochDay(day, { includeYear }),
        },
      },
      y: {
        min: 1,
        max: 10,
        title: { display: true, text: 'Severity', color: theme.muted, font },
        grid: { color: theme.grid },
        border: { display: false },
        ticks: { color: theme.muted, font, stepSize: 1, precision: 0 },
      },
    },
    plugins: {
      tooltip: {
        animation: { duration: animate ? TOOLTIP_MS : 0 },
        backgroundColor: theme.tooltip,
        titleColor: theme.tooltipText,
        bodyColor: theme.tooltipText,
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

// `scale` enlarges the marks for a chart that is drawn big and then shrunk to fit a page.
export function buildChartData(series, theme, scale = 1) {
  const isSingle = series.length === 1;
  return {
    datasets: series.map(({ key, name, points, style }) => {
      const color = theme.series[style.colorIndex];
      return {
        key,
        label: name,
        data: toChartPoints(points),
        borderColor: color,
        backgroundColor: color,
        borderDash: style.dash,
        borderWidth: 2 * scale,
        borderCapStyle: 'round',
        borderJoinStyle: 'round',
        spanGaps: false,
        clip: false,
        pointStyle: style.pointStyle,
        pointRadius: (isSingle ? 5 : 4) * scale,
        pointHoverRadius: isSingle ? 7 : 6,
        pointHitRadius: 16,
        pointBorderColor: theme.surface,
        pointBorderWidth: isSingle ? 2 : 1,
        pointHoverBorderColor: theme.surface,
        pointHoverBorderWidth: 2,
      };
    }),
  };
}
