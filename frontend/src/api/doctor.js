import { apiRequest } from './client.js';
import { toFilterQuery } from './symptoms.js';

export function fetchSharedPatients(signal) {
  return apiRequest('/api/doctor/patients', { signal });
}

export function sharedPatientSource(patientId) {
  const base = `/api/doctor/patients/${patientId}/symptoms`;
  return {
    fetchHistory: (filters, signal) => apiRequest(`${base}${toFilterQuery(filters)}`, { signal }),
    fetchNames: (signal) => apiRequest(`${base}/names`, { signal }),
    fetchTrend: (filters, signal) =>
      apiRequest(`${base}/trends${toFilterQuery(filters)}`, { signal }),
  };
}
