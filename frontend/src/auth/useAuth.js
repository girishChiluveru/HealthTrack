import { useCallback, useEffect, useState } from 'react';
import { fetchCurrentUser, loginUser, registerUser } from '../api/auth.js';
import { setUnauthorizedHandler } from '../api/client.js';
import { clearToken, getToken, setToken } from './tokenStorage.js';

const SESSION_EXPIRED = 'Your session has expired. Please log in again.';
const SESSION_UNVERIFIED = 'We could not check your session. Please reload or log in again.';

export function useAuth() {
  const [user, setUser] = useState(null);
  const [isCheckingSession, setIsCheckingSession] = useState(() => Boolean(getToken()));
  const [notice, setNotice] = useState('');

  useEffect(() => {
    setUnauthorizedHandler(() => {
      setUser(null);
      setNotice(SESSION_EXPIRED);
    });
    return () => setUnauthorizedHandler(() => {});
  }, []);

  useEffect(() => {
    if (!getToken()) {
      return undefined;
    }

    const controller = new AbortController();
    fetchCurrentUser(controller.signal)
      .then(setUser)
      .catch((error) => {
        // A 401 is already handled by the API client. Other failures keep the token,
        // because a temporary outage should not end a valid session.
        if (!controller.signal.aborted && error.status !== 401) {
          setNotice(SESSION_UNVERIFIED);
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setIsCheckingSession(false);
        }
      });

    return () => controller.abort();
  }, []);

  const login = useCallback(async (credentials) => {
    clearToken();
    const { access_token: token } = await loginUser(credentials);
    setToken(token);
    const currentUser = await fetchCurrentUser();
    setNotice('');
    setUser(currentUser);
  }, []);

  const register = useCallback(
    async (details) => {
      await registerUser(details);
      await login({ email: details.email, password: details.password });
    },
    [login],
  );

  const logout = useCallback(() => {
    clearToken();
    setUser(null);
    setNotice('You have been logged out.');
  }, []);

  return { user, isCheckingSession, notice, login, register, logout };
}
