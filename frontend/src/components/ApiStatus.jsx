import { useEffect, useState } from 'react';
import { fetchApiHealth } from '../api/health.js';

const MESSAGES = {
  loading: 'Checking API status…',
  success: 'API is running',
  failure: 'API is unavailable',
};

export default function ApiStatus() {
  const [status, setStatus] = useState('loading');
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();

    fetchApiHealth(controller.signal)
      .then(() => setStatus('success'))
      .catch(() => {
        // An abort here means the component unmounted or a newer check replaced this one.
        if (!controller.signal.aborted) {
          setStatus('failure');
        }
      });

    return () => controller.abort();
  }, [attempt]);

  function retry() {
    setStatus('loading');
    setAttempt((current) => current + 1);
  }

  return (
    <div className="api-status">
      <p className="api-status__message" role="status">
        <span className={`api-status__dot api-status__dot--${status}`} aria-hidden="true" />
        {MESSAGES[status]}
      </p>
      {status === 'failure' && (
        <button type="button" className="api-status__retry" onClick={retry}>
          Try again
        </button>
      )}
    </div>
  );
}
