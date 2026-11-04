import { apiRequest } from './client.js';

export function toFilterQuery({ symptom, startDate, endDate }) {
  const params = { symptom, start_date: startDate, end_date: endDate };
  const present = Object.entries(params).filter(([, value]) => value);
  return present.length ? `?${new URLSearchParams(present)}` : '';
}

export function createSymptomBatch(entries) {
  return apiRequest('/api/symptoms/batch', { method: 'POST', body: { entries } });
}

export const ownRecordSource = {
  fetchHistory: (filters, signal) =>
    apiRequest(`/api/symptoms${toFilterQuery(filters)}`, { signal }),
  fetchNames: (signal) => apiRequest('/api/symptoms/names', { signal }),
  fetchTrend: (filters, signal) =>
    apiRequest(`/api/symptoms/trends${toFilterQuery(filters)}`, { signal }),
};

export function updateSymptomEntry(id, changes) {
  return apiRequest(`/api/symptoms/${id}`, { method: 'PATCH', body: changes });
}

export function deleteSymptomEntry(id) {
  return apiRequest(`/api/symptoms/${id}`, { method: 'DELETE' });
}
