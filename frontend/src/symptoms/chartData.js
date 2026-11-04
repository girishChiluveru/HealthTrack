import { toEpochDay } from './dates.js';

// The API returns only days that have entries. A null point after a skipped day makes
// Chart.js break the line there, so a gap is not drawn as a continuous trend.
export function toChartPoints(points) {
  const chartPoints = [];
  let previousDay = null;
  for (const point of points) {
    const day = toEpochDay(point.date);
    if (previousDay !== null && day - previousDay > 1) {
      chartPoints.push({ x: previousDay + 1, y: null });
    }
    chartPoints.push({ x: day, y: point.max_severity, entryCount: point.entry_count });
    previousDay = day;
  }
  return chartPoints;
}

export function chartDayRange(points, { startDate, endDate }) {
  const days = points.map((point) => toEpochDay(point.date));
  const min = startDate ? toEpochDay(startDate) : Math.min(...days);
  const max = endDate ? toEpochDay(endDate) : Math.max(...days);
  // A single day still needs a visible axis, and edge markers need room.
  return { min: min - 1, max: max + 1 };
}
