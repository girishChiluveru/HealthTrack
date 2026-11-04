import { useRef, useState } from 'react';
import { revokeGrant } from '../api/sharing.js';

export default function SharedDoctorItem({ grant, onRevoked, onMissing }) {
  const [isConfirming, setIsConfirming] = useState(false);
  const [isRevoking, setIsRevoking] = useState(false);
  const [error, setError] = useState('');
  const revokeInFlight = useRef(false);
  const { name, email } = grant.doctor;

  async function confirmRevoke() {
    if (revokeInFlight.current) {
      return;
    }
    revokeInFlight.current = true;
    setIsRevoking(true);
    setError('');
    try {
      await revokeGrant(grant.id);
      onRevoked(grant);
    } catch (revokeError) {
      if (revokeError.status === 404) {
        onMissing();
      } else {
        setError(revokeError.message);
      }
    } finally {
      revokeInFlight.current = false;
      setIsRevoking(false);
    }
  }

  return (
    <li className="people-list__item">
      <div>
        <p className="people-list__name">{name}</p>
        <p className="people-list__detail">{email}</p>
      </div>
      {isConfirming ? (
        <div className="people-list__confirm" role="group" aria-label={`Stop sharing with ${name}`}>
          <p>Stop sharing your records with {name}?</p>
          {error && (
            <p className="alert alert--error" role="alert">
              {error}
            </p>
          )}
          <div className="action-row">
            <button
              type="button"
              className="button button--danger"
              disabled={isRevoking}
              onClick={confirmRevoke}
            >
              {isRevoking ? 'Stopping…' : 'Stop sharing'}
            </button>
            <button
              type="button"
              className="button button--secondary"
              disabled={isRevoking}
              // Focus starts here, so pressing Enter by accident does not end access.
              autoFocus
              onClick={() => {
                setError('');
                setIsConfirming(false);
              }}
            >
              Keep sharing
            </button>
          </div>
        </div>
      ) : (
        <button
          type="button"
          className="link-button"
          aria-label={`Stop sharing with ${name}`}
          onClick={() => setIsConfirming(true)}
        >
          Stop sharing
        </button>
      )}
    </li>
  );
}
