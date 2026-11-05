import { apiRequest } from './client.js';

// Longer than the server's limit of 35 seconds, so the server reports a slow provider itself.
const INSIGHTS_TIMEOUT_MS = 40000;

export function toFilterQuery({ symptom, startDate, endDate, page, pageSize }) {
  const params = {
    symptom,
    start_date: startDate,
    end_date: endDate,
    page,
    page_size: pageSize,
  };
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

export function createInsights({ symptom, startDate, endDate }) {
  return apiRequest('/api/symptoms/insights', {
    method: 'POST',
    body: { symptom: symptom || null, start_date: startDate || null, end_date: endDate || null },
    timeoutMs: INSIGHTS_TIMEOUT_MS,
  });
}

export function deleteSymptomEntry(id) {
  return apiRequest(`/api/symptoms/${id}`, { method: 'DELETE' });
}
