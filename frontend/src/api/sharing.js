import { apiRequest } from './client.js';

export function lookUpDoctor(email) {
  return apiRequest('/api/sharing/lookup', { method: 'POST', body: { email } });
}

export function fetchGrants(signal) {
  return apiRequest('/api/sharing/grants', { signal });
}

export function createGrant(email) {
  return apiRequest('/api/sharing/grants', { method: 'POST', body: { email } });
}

export function revokeGrant(id) {
  return apiRequest(`/api/sharing/grants/${id}`, { method: 'DELETE' });
}
