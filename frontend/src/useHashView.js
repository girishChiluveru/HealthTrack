import { useSyncExternalStore } from 'react';

function subscribe(onChange) {
  window.addEventListener('hashchange', onChange);
  return () => window.removeEventListener('hashchange', onChange);
}

function readHash() {
  return window.location.hash.slice(1);
}

// The active view lives in the URL, so reloading and the Back button work. Filters stay out
// of the URL on purpose: symptom names should not end up in browser history.
export function useHashView(viewIds) {
  const hash = useSyncExternalStore(subscribe, readHash);
  return viewIds.includes(hash) ? hash : viewIds[0];
}
