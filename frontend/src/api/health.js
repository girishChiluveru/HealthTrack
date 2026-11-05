import { apiRequest } from './client.js';

// Starts a sleeping API while the page loads, so logging in does not wait as long.
export function wakeApi() {
  apiRequest('/api/health').catch(() => {});
}
