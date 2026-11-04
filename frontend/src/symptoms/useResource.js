import { useEffect, useState } from 'react';

// Loads data whenever `load` or `refreshKey` changes. The previous data stays available
// during a reload and after a failed one, so the page does not flash or lose content.
// Pass a null `load` to skip loading.
export function useResource(load, refreshKey) {
  const [settled, setSettled] = useState({ load: null, refreshKey: null, data: null, error: null });

  useEffect(() => {
    if (!load) {
      return undefined;
    }

    const controller = new AbortController();
    load(controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) {
          setSettled({ load, refreshKey, data, error: null });
        }
      })
      .catch((error) => {
        if (!controller.signal.aborted) {
          setSettled((current) => ({ load, refreshKey, data: current.data, error }));
        }
      });

    return () => controller.abort();
  }, [load, refreshKey]);

  const isLoading = Boolean(load) && (settled.load !== load || settled.refreshKey !== refreshKey);
  return { data: settled.data, error: settled.error, isLoading };
}
