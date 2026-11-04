const REQUEST_TIMEOUT_MS = 5000;

export async function fetchApiHealth(signal) {
  const baseUrl = import.meta.env.VITE_API_BASE_URL;
  if (!baseUrl) {
    throw new Error('VITE_API_BASE_URL is not set');
  }

  const response = await fetch(`${baseUrl}/api/health`, {
    signal: AbortSignal.any([signal, AbortSignal.timeout(REQUEST_TIMEOUT_MS)]),
  });
  if (!response.ok) {
    throw new Error(`Health check failed with status ${response.status}`);
  }

  const body = await response.json();
  if (body.status !== 'ok') {
    throw new Error('Health check returned an unexpected response');
  }
}
