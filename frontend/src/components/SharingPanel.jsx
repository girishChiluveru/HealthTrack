import { useCallback, useRef, useState } from 'react';
import { fetchGrants } from '../api/sharing.js';
import { useResource } from '../symptoms/useResource.js';
import LoadError from './LoadError.jsx';
import ShareWithDoctorForm from './ShareWithDoctorForm.jsx';
import SharedDoctorItem from './SharedDoctorItem.jsx';
import Skeleton from './Skeleton.jsx';

export default function SharingPanel({ onNotify }) {
  const [revision, setRevision] = useState(0);
  const heading = useRef(null);
  const grants = useResource(fetchGrants, revision);
  const list = grants.data?.grants;

  const refresh = useCallback(() => setRevision((current) => current + 1), []);

  function handleShared(grant) {
    const alreadyShared = list?.some(({ id }) => id === grant.id);
    onNotify(
      alreadyShared
        ? `${grant.doctor.name} already has access to your records.`
        : `Your records are now shared with ${grant.doctor.name}.`,
    );
    refresh();
  }

  function handleRevoked(grant) {
    onNotify(`${grant.doctor.name} can no longer see your records.`);
    refresh();
    heading.current?.focus();
  }

  function handleMissing() {
    onNotify('That access had already ended, so the list has been refreshed.');
    refresh();
    heading.current?.focus();
  }

  return (
    <section
      className="card narrow-panel"
      aria-labelledby="sharing-heading"
      aria-busy={grants.isLoading}
    >
      <h2 id="sharing-heading" ref={heading} tabIndex={-1}>
        Share with a doctor
      </h2>
      <p className="muted-text">
        A doctor you share with can see all of your entries, past and future, until you stop
        sharing. They cannot change anything.
      </p>
      {grants.isLoading && !list && (
        <Skeleton label="Loading doctors…" className="skeleton--row" />
      )}
      {grants.error && (
        <LoadError message="We could not load the doctors you share with." onRetry={refresh} />
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
      <ShareWithDoctorForm onShared={handleShared} />
    </section>
  );
}
