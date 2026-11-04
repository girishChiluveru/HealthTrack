import { useSyncExternalStore } from 'react';

const TOKENS = ['--chart-line', '--color-border', '--color-muted', '--color-surface', '--color-text'];
const colorScheme = window.matchMedia('(prefers-color-scheme: dark)');

function subscribe(onChange) {
  colorScheme.addEventListener('change', onChange);
  return () => colorScheme.removeEventListener('change', onChange);
}

// Canvas drawing cannot use CSS variables, so the current values are read here. A string
// snapshot lets React detect a theme change by value.
function readTokens() {
  const styles = getComputedStyle(document.documentElement);
  return TOKENS.map((token) => styles.getPropertyValue(token).trim()).join('|');
}

export function useChartTheme() {
  const [line, grid, muted, surface, text] = useSyncExternalStore(subscribe, readTokens).split('|');
  return { line, grid, muted, surface, text };
}
