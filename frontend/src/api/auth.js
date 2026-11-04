import { apiRequest } from './client.js';

export function registerUser(details) {
  return apiRequest('/api/auth/register', {
    method: 'POST',
    body: {
      ...details,
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    },
  });
}

export function loginUser(credentials) {
  return apiRequest('/api/auth/login', { method: 'POST', body: credentials });
}

export function fetchCurrentUser(signal) {
  return apiRequest('/api/auth/me', { signal });
}
