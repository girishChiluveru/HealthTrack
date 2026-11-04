import { useMemo, useState } from 'react';

export const MAX_CHART_LINES = 6;

// Which symptoms the all-symptoms chart draws. Until the first toggle that is the most
// recently logged ones. After it, `known` tells a symptom that is new, such as a rename,
// from one that was hidden on purpose, so the new one appears without being asked for.
export function useChartSelection(symptoms) {
  const [selection, setSelection] = useState(null);
  const keys = useMemo(() => symptoms.map(({ key }) => key), [symptoms]);

  const visibleKeys = useMemo(() => {
    if (!selection) {
      return keys.slice(0, MAX_CHART_LINES);
    }
    const added = keys.filter((key) => !selection.known.includes(key));
    const kept = selection.shown.filter((key) => keys.includes(key));
    const shown = [...added, ...kept].slice(0, MAX_CHART_LINES);
    return keys.filter((key) => shown.includes(key));
  }, [keys, selection]);

  function toggle(key) {
    const shown = visibleKeys.includes(key)
      ? visibleKeys.filter((visible) => visible !== key)
      : [...visibleKeys, key];
    setSelection({ shown, known: keys });
  }

  return { visibleKeys, toggle };
}
