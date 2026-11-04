import { ChartLine, CirclePlus, LayoutDashboard, Share2, UserRound } from 'lucide-react';
import { useCallback, useRef, useState } from 'react';
import { ownRecordSource } from '../api/symptoms.js';
import { useHashView } from '../useHashView.js';
import { useToast } from '../useToast.js';
import AccountPanel from './AccountPanel.jsx';
import AppShell from './AppShell.jsx';
import SharingPanel from './SharingPanel.jsx';
import SymptomEntryForm from './SymptomEntryForm.jsx';
import SymptomOverview from './SymptomOverview.jsx';
import SymptomRecords from './SymptomRecords.jsx';
import Toast from './Toast.jsx';

const NAV_ITEMS = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, subtitle: 'Your latest symptoms and how they have changed.' },
  { id: 'log', label: 'Log symptoms', icon: CirclePlus, subtitle: 'Add one or more symptoms in a single save.' },
  { id: 'records', label: 'History and trends', icon: ChartLine, subtitle: 'Review, correct, and chart your entries.' },
  { id: 'sharing', label: 'Sharing', icon: Share2, subtitle: 'Choose which doctors can see your records.' },
  { id: 'account', label: 'Account', icon: UserRound, subtitle: 'Your account details.' },
];

const VIEW_IDS = NAV_ITEMS.map(({ id }) => id);

export default function SymptomDashboard({ user, onLogout }) {
  const { timezone } = user;
  const view = useHashView(VIEW_IDS);
  // Every change bumps this one counter, and the records refetch from the server.
  const [revision, setRevision] = useState(0);
  const { toast, showToast, dismissToast } = useToast();
  const historyHeading = useRef(null);

  const refresh = useCallback(() => setRevision((current) => current + 1), []);

  function handleCreated(count) {
    showToast(count === 1 ? 'Saved 1 entry.' : `Saved ${count} entries.`);
    refresh();
  }

  function handleEdited() {
    showToast('Entry updated.');
    refresh();
  }

  function handleDeleted() {
    showToast('Entry deleted.');
    refresh();
    // The focused button is about to disappear with its entry.
    historyHeading.current?.focus();
  }

  function handleMissing() {
    showToast('That entry no longer exists, so the list has been refreshed.');
    refresh();
    historyHeading.current?.focus();
  }

  // Inactive views stay mounted, so filters and unsaved form input survive navigation.
  return (
    <AppShell user={user} navItems={NAV_ITEMS} activeView={view} onLogout={onLogout}>
      <div className="view" hidden={view !== 'dashboard'}>
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
      <div className="view" hidden={view !== 'log'}>
        <SymptomEntryForm timezone={timezone} onSaved={handleCreated} />
      </div>
      <div className="view" hidden={view !== 'records'}>
        <SymptomRecords
          source={ownRecordSource}
          revision={revision}
          onRefresh={refresh}
          noEntriesText="No entries yet. Log a symptom to get started."
          noTrendText="Log a symptom to see its trend here."
          headingRef={historyHeading}
          entryActions={{
            timezone,
            onEdited: handleEdited,
            onDeleted: handleDeleted,
            onMissing: handleMissing,
          }}
        />
      </div>
      <div className="view" hidden={view !== 'sharing'}>
        <SharingPanel onNotify={showToast} />
      </div>
      <div className="view" hidden={view !== 'account'}>
        <AccountPanel user={user} />
      </div>
      <Toast toast={toast} onDismiss={dismissToast} />
    </AppShell>
  );
}
