import { apiRequest } from './client.js';

function toQuery(params) {
  const present = Object.entries(params).filter(([, value]) => value);
  return present.length ? `?${new URLSearchParams(present)}` : '';
}

export function createSymptomBatch(entries) {
  return apiRequest('/api/symptoms/batch', { method: 'POST', body: { entries } });
}

export function fetchSymptomHistory({ symptom, startDate, endDate }, signal) {
  const query = toQuery({ symptom, start_date: startDate, end_date: endDate });
  return apiRequest(`/api/symptoms${query}`, { signal });
}

export function fetchSymptomNames(signal) {
  return apiRequest('/api/symptoms/names', { signal });
}

export function fetchSymptomTrend({ symptom, startDate, endDate }, signal) {
  const query = toQuery({ symptom, start_date: startDate, end_date: endDate });
  return apiRequest(`/api/symptoms/trends${query}`, { signal });
}

export function updateSymptomEntry(id, changes) {
  return apiRequest(`/api/symptoms/${id}`, { method: 'PATCH', body: changes });
}

export function deleteSymptomEntry(id) {
  return apiRequest(`/api/symptoms/${id}`, { method: 'DELETE' });
}
