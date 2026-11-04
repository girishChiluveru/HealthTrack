import { useCallback, useState } from 'react';
import { fetchGrants } from '../api/sharing.js';
import { useResource } from '../symptoms/useResource.js';
import ShareWithDoctorForm from './ShareWithDoctorForm.jsx';
import SharedDoctorItem from './SharedDoctorItem.jsx';

export default function SharingPanel() {
  const [revision, setRevision] = useState(0);
  const [notice, setNotice] = useState('');
  const grants = useResource(fetchGrants, revision);
  const list = grants.data?.grants;

  const refresh = useCallback(() => setRevision((current) => current + 1), []);

  function handleShared(grant) {
    const alreadyShared = list?.some(({ id }) => id === grant.id);
    setNotice(
      alreadyShared
        ? `${grant.doctor.name} already has access to your records.`
        : `Your records are now shared with ${grant.doctor.name}.`,
    );
    refresh();
  }

  function handleRevoked(grant) {
    setNotice(`${grant.doctor.name} can no longer see your records.`);
    refresh();
  }

  function handleMissing() {
    setNotice('That access had already ended, so the list has been refreshed.');
    refresh();
  }

  return (
    <section className="card narrow-panel" aria-labelledby="sharing-heading" aria-busy={grants.isLoading}>
      <h2 id="sharing-heading">Share with a doctor</h2>
      <p className="muted-text">
        A doctor you share with can see all of your entries, past and future, until you stop
        sharing. They cannot change anything.
      </p>
      <div role="status">{notice && <p className="alert alert--success">{notice}</p>}</div>
      {grants.error && (
        <div className="alert alert--error" role="alert">
          <p>We could not load the doctors you share with.</p>
          <button type="button" className="link-button" onClick={refresh}>
            Try again
          </button>
        </div>
      )}
      {list?.length === 0 && (
        <p className="muted-text">You are not sharing your records with anyone.</p>
      )}
      {list?.length > 0 && (
        <ul className="people-list" aria-label="Doctors with access">
          {list.map((grant) => (
            <SharedDoctorItem
              key={grant.id}
              grant={grant}
              onRevoked={handleRevoked}
              onMissing={handleMissing}
            />
          ))}
        </ul>
      )}
      <ShareWithDoctorForm onShared={handleShared} onStarted={() => setNotice('')} />
    </section>
  );
}
