import { RefreshCw, UserRound, Users } from 'lucide-react';
import { useCallback, useMemo, useState } from 'react';
import { fetchSharedPatients, sharedPatientSource } from '../api/doctor.js';
import { useResource } from '../symptoms/useResource.js';
import { useHashView } from '../useHashView.js';
import AccountPanel from './AccountPanel.jsx';
import AppShell from './AppShell.jsx';
import Skeleton from './Skeleton.jsx';
import SymptomOverview from './SymptomOverview.jsx';
import SymptomRecords from './SymptomRecords.jsx';

const NAV_ITEMS = [
  { id: 'patients', label: 'Patients', icon: Users, subtitle: 'Records patients have shared with you. These are read-only.' },
  { id: 'account', label: 'Account', icon: UserRound, subtitle: 'Your account details.' },
];

const VIEW_IDS = NAV_ITEMS.map(({ id }) => id);

export default function DoctorDashboard({ user, onLogout }) {
  const { email, timezone } = user;
  const view = useHashView(VIEW_IDS);
  const [revision, setRevision] = useState(0);
  const [selectedId, setSelectedId] = useState('');
  const patients = useResource(fetchSharedPatients, revision);
  const list = patients.data?.patients;
  // A patient who stops sharing drops out of the refreshed list, which ends the selection.
  const selected = list?.find(({ id }) => id === selectedId);
  const visibleId = selected?.id;
  const accessEnded = Boolean(selectedId && list && !selected);

  const source = useMemo(() => (visibleId ? sharedPatientSource(visibleId) : null), [visibleId]);

  // Also the response to losing access, because the refreshed list then shows who is left.
  const refresh = useCallback(() => setRevision((current) => current + 1), []);

  return (
    <AppShell user={user} navItems={NAV_ITEMS} activeView={view} onLogout={onLogout}>
      <div className="view" hidden={view !== 'account'}>
        <AccountPanel user={user} />
      </div>
      <div className="view" hidden={view !== 'patients'}>
        <section className="card" aria-labelledby="patients-heading" aria-busy={patients.isLoading}>
          <div className="record-header">
            <h2 id="patients-heading">Your patients</h2>
            <button type="button" className="button button--secondary" onClick={refresh}>
              <RefreshCw size={16} aria-hidden="true" />
              Refresh
            </button>
          </div>
          <div role="status">
            {accessEnded && <p className="alert">Access to that patient’s records has ended.</p>}
          </div>
          {patients.isLoading && !list && (
            <Skeleton label="Loading patients…" count={2} className="skeleton--row" />
          )}
          {patients.error && (
            <div className="alert alert--error" role="alert">
              <p>We could not load your patients.</p>
              <button type="button" className="link-button" onClick={refresh}>
                Try again
              </button>
            </div>
          )}
          {list?.length === 0 && !patients.isLoading && (
            <p className="muted-text">
              No patients are sharing their records with you yet. Patients can share using your
              account email, {email}.
            </p>
          )}
          {list?.length > 0 && (
            <ul className="people-list" aria-label="Patients sharing with you">
              {list.map(({ id, name, email: patientEmail }) => (
                <li key={id} className="people-list__item">
                  <div>
                    <p className="people-list__name">{name}</p>
                    <p className="people-list__detail">{patientEmail}</p>
                  </div>
                  <button
                    type="button"
                    className="link-button"
                    aria-label={`View records for ${name}`}
                    aria-current={id === selected?.id ? 'true' : undefined}
                    onClick={() => setSelectedId(id)}
                  >
                    {id === selected?.id ? 'Viewing' : 'View records'}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        {selected && (
          <>
            <p className="muted-text">
              Showing records for <strong>{selected.name}</strong>. These records are read-only.
            </p>
            <SymptomOverview
              key={`overview-${selected.id}`}
              source={source}
              revision={revision}
              timezone={timezone}
              onRetry={refresh}
            />
            <SymptomRecords
              key={selected.id}
              source={source}
              revision={revision}
              onRefresh={refresh}
              noEntriesText="This patient has no entries yet."
              noTrendText="This patient has no entries to chart yet."
              onAccessLost={refresh}
            />
          </>
        )}
      </div>
    </AppShell>
  );
}
