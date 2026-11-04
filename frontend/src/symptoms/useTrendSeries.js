import { useMemo, useRef } from 'react';
import { useResource } from './useResource.js';

// Loads the daily maximums of each symptom through the trend API. Results are kept for the
// current filters and revision, so showing or hiding a line needs no new requests. Any change
// to the records bumps `revision`, which discards them. `dateRange` is returned with the data,
// so the axis and the points always change together.
export function useTrendSeries(source, keys, { startDate, endDate }, revision) {
  const cache = useRef({ stamp: '', points: new Map() });
  const keyList = keys.join('\n');

  const load = useMemo(() => {
    if (!keyList) {
      return null;
    }
    const wanted = keyList.split('\n');
    return async (signal) => {
      const stamp = `${revision}|${startDate}|${endDate}`;
      if (cache.current.stamp !== stamp) {
        cache.current = { stamp, points: new Map() };
      }
      const { points } = cache.current;
      const missing = wanted.filter((key) => !points.has(key));
      const trends = await Promise.all(
        missing.map((symptom) => source.fetchTrend({ symptom, startDate, endDate }, signal)),
      );
      missing.forEach((key, index) => points.set(key, trends[index].points));
      return {
        series: wanted.map((key) => ({ key, points: points.get(key) })),
        dateRange: { startDate, endDate },
      };
    };
  }, [source, keyList, startDate, endDate, revision]);

  return useResource(load, revision);
}
