import { clearToken, getToken } from '../auth/tokenStorage.js';

const REQUEST_TIMEOUT_MS = 10000;

let handleUnauthorized = () => {};

export function setUnauthorizedHandler(handler) {
  handleUnauthorized = handler;
}

export class ApiError extends Error {
  constructor(message, { status = null, fieldErrors = {}, errors = [] } = {}) {
    super(message);
    this.status = status;
    this.fieldErrors = fieldErrors;
    this.errors = errors;
  }
}

function toFieldErrors(errors = []) {
  return Object.fromEntries(errors.map(({ field, message }) => [field, message]));
}

async function readJson(response) {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

export async function apiRequest(path, { method = 'GET', body, signal } = {}) {
  const baseUrl = import.meta.env.VITE_API_BASE_URL;
  if (!baseUrl) {
    throw new ApiError('The app is not configured: VITE_API_BASE_URL is not set.');
  }

  const token = getToken();
  const headers = {};
  if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
  }
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const timeout = AbortSignal.timeout(REQUEST_TIMEOUT_MS);
  let response;
  try {
    response = await fetch(`${baseUrl}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: signal ? AbortSignal.any([signal, timeout]) : timeout,
    });
  } catch (error) {
    if (signal?.aborted) {
      throw error;
    }
    throw new ApiError('Could not reach the server. Please try again.');
  }

  const data = await readJson(response);
  if (response.ok) {
    return data;
  }

  // A 401 without a token is a failed login, which the form reports itself.
  if (response.status === 401 && token) {
    clearToken();
    handleUnauthorized();
  }
  throw new ApiError(data?.detail ?? 'Something went wrong. Please try again.', {
    status: response.status,
    fieldErrors: toFieldErrors(data?.errors),
    errors: data?.errors ?? [],
  });
}
