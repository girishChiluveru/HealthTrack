import { useRef, useState } from 'react';
import { flushSync } from 'react-dom';
import { revokeGrant } from '../api/sharing.js';
import ConfirmDialog from './ConfirmDialog.jsx';

export default function SharedDoctorItem({ grant, onRevoked, onMissing }) {
  const [isConfirming, setIsConfirming] = useState(false);
  const [isRevoking, setIsRevoking] = useState(false);
  const [error, setError] = useState('');
  const revokeInFlight = useRef(false);
  const { name, email } = grant.doctor;

  function closeDialog() {
    setError('');
    setIsConfirming(false);
  }

  async function confirmRevoke() {
    if (revokeInFlight.current) {
      return;
    }
    revokeInFlight.current = true;
    setIsRevoking(true);
    setError('');
    try {
      await revokeGrant(grant.id);
      // A modal dialog blocks focus elsewhere, so it must close before the parent moves focus.
      flushSync(closeDialog);
      onRevoked(grant);
    } catch (revokeError) {
      if (revokeError.status === 404) {
        flushSync(closeDialog);
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
      <button
        type="button"
        className="link-button"
        aria-label={`Stop sharing with ${name}`}
        onClick={() => setIsConfirming(true)}
      >
        Stop sharing
      </button>
      {isConfirming && (
        <ConfirmDialog
          title={`Stop sharing with ${name}?`}
          confirmLabel="Stop sharing"
          busyLabel="Stopping…"
          cancelLabel="Keep sharing"
          isBusy={isRevoking}
          error={error}
          onConfirm={confirmRevoke}
          onCancel={closeDialog}
        >
          <p>They will lose access to your records straight away.</p>
        </ConfirmDialog>
      )}
    </li>
  );
}
