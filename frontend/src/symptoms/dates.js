// Entries hold calendar dates, so all conversions use UTC to avoid shifting the day.
const MS_PER_DAY = 86400000;

export function toEpochDay(isoDate) {
  return Date.parse(`${isoDate}T00:00:00Z`) / MS_PER_DAY;
}

function format(date, options) {
  return new Intl.DateTimeFormat(undefined, { ...options, timeZone: 'UTC' }).format(date);
}

export function formatDate(isoDate) {
  return format(new Date(`${isoDate}T00:00:00Z`), { dateStyle: 'medium' });
}

export function formatEpochDay(epochDay, { includeYear }) {
  return format(new Date(epochDay * MS_PER_DAY), {
    month: 'short',
    day: 'numeric',
    ...(includeYear ? { year: 'numeric' } : {}),
  });
}
