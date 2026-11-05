import { useSyncExternalStore } from 'react';

const STORAGE_KEY = 'healthtrack.theme';
const THEME_COLORS = { light: '#f6f5fc', dark: '#110f20' };

const systemDark = window.matchMedia('(prefers-color-scheme: dark)');
const listeners = new Set();

function readPreference() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored === 'light' || stored === 'dark' ? stored : null;
  } catch {
    return null;
  }
}

let preference = readPreference();

function currentTheme() {
  return preference ?? (systemDark.matches ? 'dark' : 'light');
}

// The attribute changes before subscribers run, so a chart re-reading its colors gets new ones.
function applyTheme() {
  const theme = currentTheme();
  document.documentElement.dataset.theme = theme;
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', THEME_COLORS[theme]);
  listeners.forEach((listener) => listener());
}

systemDark.addEventListener('change', () => {
  if (!preference) {
    applyTheme();
  }
});

function subscribe(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function toggleTheme() {
  preference = currentTheme() === 'dark' ? 'light' : 'dark';
  try {
    localStorage.setItem(STORAGE_KEY, preference);
  } catch {
    // Private windows can block storage. The choice then lasts until the page closes.
  }
  applyTheme();
}

export function useTheme() {
  return useSyncExternalStore(subscribe, currentTheme);
}
