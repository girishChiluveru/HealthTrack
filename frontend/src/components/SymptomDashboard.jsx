import { useCallback, useRef, useState } from 'react';
import { ownRecordSource } from '../api/symptoms.js';
import { useHashView } from '../useHashView.js';
import AccountPanel from './AccountPanel.jsx';
import AppShell from './AppShell.jsx';
import SharingPanel from './SharingPanel.jsx';
import SymptomEntryForm from './SymptomEntryForm.jsx';
import SymptomOverview from './SymptomOverview.jsx';
import SymptomRecords from './SymptomRecords.jsx';

const NAV_ITEMS = [
  { id: 'dashboard', label: 'Dashboard', icon: 'dashboard', subtitle: 'Your latest symptoms and how they have changed.' },
  { id: 'log', label: 'Log symptoms', icon: 'log', subtitle: 'Add one or more symptoms in a single save.' },
  { id: 'records', label: 'History and trends', icon: 'history', subtitle: 'Review, correct, and chart your entries.' },
  { id: 'sharing', label: 'Sharing', icon: 'sharing', subtitle: 'Choose which doctors can see your records.' },
  { id: 'account', label: 'Account', icon: 'account', subtitle: 'Your account details.' },
];

const VIEW_IDS = NAV_ITEMS.map(({ id }) => id);

export default function SymptomDashboard({ user, onLogout }) {
  const { timezone } = user;
  const view = useHashView(VIEW_IDS);
  // Every change bumps this one counter, and the records refetch from the server.
  const [revision, setRevision] = useState(0);
  const [notice, setNotice] = useState('');
  const historyHeading = useRef(null);

  const refresh = useCallback(() => setRevision((current) => current + 1), []);

  function handleCreated() {
    setNotice('');
    refresh();
  }

  function handleEdited() {
    setNotice('Entry updated.');
    refresh();
  }

  function handleDeleted() {
    setNotice('Entry deleted.');
    refresh();
    // The focused button is about to disappear with its entry.
    historyHeading.current?.focus();
  }

  function handleMissing() {
    setNotice('That entry no longer exists, so the list has been refreshed.');
    refresh();
  }

  // Inactive views stay mounted, so filters and unsaved form input survive navigation.
  return (
    <AppShell user={user} navItems={NAV_ITEMS} activeView={view} onLogout={onLogout}>
      <div hidden={view !== 'dashboard'}>
        <SymptomOverview
          source={ownRecordSource}
          revision={revision}
          timezone={timezone}
          onLogSymptoms={() => {
            window.location.hash = 'log';
          }}
          onRetry={refresh}
        />
      </div>
      <div hidden={view !== 'log'}>
        <SymptomEntryForm timezone={timezone} onSaved={handleCreated} />
      </div>
      <div hidden={view !== 'records'}>
        <SymptomRecords
          source={ownRecordSource}
          revision={revision}
          onRefresh={refresh}
          notice={notice}
          noEntriesText="No entries yet. Log a symptom to get started."
          noTrendText="Log a symptom to see its trend here."
          headingRef={historyHeading}
          entryActions={{
            timezone,
            onEdited: handleEdited,
            onDeleted: handleDeleted,
            onMissing: handleMissing,
          }}
          onFiltersChanged={() => setNotice('')}
        />
      </div>
      <div hidden={view !== 'sharing'}>
        <SharingPanel />
      </div>
      <div hidden={view !== 'account'}>
        <AccountPanel user={user} />
      </div>
    </AppShell>
  );
}
