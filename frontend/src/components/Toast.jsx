import { CircleCheck, X } from 'lucide-react';
import { useEffect } from 'react';
import IconButton from './IconButton.jsx';

const VISIBLE_MS = 5000;

// The status region stays mounted, because screen readers only announce changes to a region
// that already exists.
export default function Toast({ toast, onDismiss }) {
  const id = toast?.id;

  useEffect(() => {
    if (!id) {
      return undefined;
    }
    const timer = setTimeout(onDismiss, VISIBLE_MS);
    return () => clearTimeout(timer);
  }, [id, onDismiss]);

  return (
    <div className="toast-region" role="status">
      {toast && (
        <div key={toast.id} className="toast">
          <CircleCheck size={20} aria-hidden="true" />
          <p>{toast.message}</p>
          <IconButton label="Dismiss message" icon={X} tooltip={false} onClick={onDismiss} />
        </div>
      )}
    </div>
  );
}
