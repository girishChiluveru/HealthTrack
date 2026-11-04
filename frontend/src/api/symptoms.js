import { apiRequest } from './client.js';

export function createSymptomBatch(entries) {
  return apiRequest('/api/symptoms/batch', { method: 'POST', body: { entries } });
}
