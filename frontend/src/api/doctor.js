import { apiRequest } from './client.js';
import { toFilterQuery } from './symptoms.js';

export function fetchSharedPatients(signal) {
  return apiRequest('/api/doctor/patients', { signal });
}

// The same shape as the patient's own record source, read through the doctor routes.
export function sharedPatientSource(patientId) {
  const base = `/api/doctor/patients/${patientId}/symptoms`;
  return {
    fetchHistory: (filters, signal) => apiRequest(`${base}${toFilterQuery(filters)}`, { signal }),
    fetchNames: (signal) => apiRequest(`${base}/names`, { signal }),
    fetchTrend: (filters, signal) =>
      apiRequest(`${base}/trends${toFilterQuery(filters)}`, { signal }),
  };
}
