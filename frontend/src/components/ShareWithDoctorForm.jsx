import { useRef, useState } from 'react';
import { createGrant, lookUpDoctor } from '../api/sharing.js';
import FormField from './FormField.jsx';

export default function ShareWithDoctorForm({ onShared }) {
  const [email, setEmail] = useState('');
  const [doctor, setDoctor] = useState(null);
  const [error, setError] = useState('');
  const [isWorking, setIsWorking] = useState(false);
  const requestInFlight = useRef(false);

  async function run(action) {
    if (requestInFlight.current) {
      return;
    }
    requestInFlight.current = true;
    setIsWorking(true);
    setError('');
    try {
      await action();
    } catch (requestError) {
      setError(requestError.fieldErrors?.email ?? requestError.message);
    } finally {
      requestInFlight.current = false;
      setIsWorking(false);
    }
  }

  function handleLookup(event) {
    event.preventDefault();
    if (!email.trim()) {
      setError('Enter your doctor’s email');
      return;
    }
    run(async () => setDoctor(await lookUpDoctor(email.trim())));
  }

  function handleConfirm() {
    run(async () => {
      const grant = await createGrant(doctor.email);
      setDoctor(null);
      setEmail('');
      onShared(grant);
    });
  }

  if (doctor) {
    return (
      <div className="share-confirm" role="group" aria-label="Confirm sharing">
        <p>Is this your doctor?</p>
        <p className="share-confirm__doctor">
          {doctor.name} ({doctor.email})
        </p>
        <p className="muted-text">
          HealthTrack does not verify doctors. This name was entered by the account holder, so
          check that the email is the one your doctor gave you.
        </p>
        {error && (
          <p className="alert alert--error" role="alert">
            {error}
          </p>
        )}
        <div className="action-row">
          <button type="button" className="button" disabled={isWorking} onClick={handleConfirm}>
            {isWorking ? 'Sharing…' : 'Share my records'}
          </button>
          <button
            type="button"
            className="button button--secondary"
            disabled={isWorking}
            onClick={() => {
              setError('');
              setDoctor(null);
            }}
          >
            Cancel
          </button>
        </div>
      </div>
    );
  }

  return (
    <form className="auth-form" onSubmit={handleLookup} noValidate>
      <FormField
        label="Doctor’s email"
        type="email"
        name="doctorEmail"
        autoComplete="off"
        spellCheck={false}
        hint="Enter the exact email of your doctor’s HealthTrack account."
        value={email}
        onChange={(event) => setEmail(event.target.value)}
        error={error}
      />
      <button type="submit" className="button" disabled={isWorking}>
        {isWorking ? 'Checking…' : 'Find doctor'}
      </button>
    </form>
  );
}
