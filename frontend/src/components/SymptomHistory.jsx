import HistoryEntry from './HistoryEntry.jsx';
import Skeleton from './Skeleton.jsx';

export default function SymptomHistory({
  history,
  hasFilters,
  noEntriesText,
  headingRef,
  entryActions,
  onRetry,
}) {
  const entries = history.data?.entries;

  return (
    <section className="card" aria-labelledby="history-heading" aria-busy={history.isLoading}>
      <h2 id="history-heading" ref={headingRef} tabIndex={-1}>
        Symptom history
      </h2>
      {history.isLoading && !entries && (
        <Skeleton label="Loading history…" count={4} className="skeleton--row" />
      )}
      {history.error && (
        <div className="alert alert--error" role="alert">
          <p>We could not load the history.</p>
          <button type="button" className="link-button" onClick={onRetry}>
            Try again
          </button>
        </div>
      )}
      {entries?.length === 0 && !history.isLoading && (
        <p className="muted-text">
          {hasFilters ? 'No entries match these filters.' : noEntriesText}
        </p>
      )}
      {entries?.length > 0 && (
        <ul className="history-list">
          {entries.map((entry) => (
            <HistoryEntry key={entry.id} entry={entry} actions={entryActions} />
          ))}
        </ul>
      )}
    </section>
  );
}
