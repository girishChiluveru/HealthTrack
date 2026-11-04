import HistoryEntry from './HistoryEntry.jsx';

function emptyMessage(hasFilters) {
  return hasFilters
    ? 'No entries match these filters.'
    : 'No entries yet. Log a symptom above to get started.';
}

export default function SymptomHistory({
  history,
  hasFilters,
  notice,
  headingRef,
  timezone,
  onEdited,
  onDeleted,
  onMissing,
  onRetry,
}) {
  const entries = history.data?.entries;

  return (
    <section className="card" aria-labelledby="history-heading" aria-busy={history.isLoading}>
      <h2 id="history-heading" ref={headingRef} tabIndex={-1}>
        Symptom history
      </h2>
      <div role="status">
        {notice && <p className="alert alert--success">{notice}</p>}
        {history.isLoading && <p className="muted-text">Loading history…</p>}
      </div>
      {history.error && (
        <div className="alert alert--error" role="alert">
          <p>We could not load your history.</p>
          <button type="button" className="link-button" onClick={onRetry}>
            Try again
          </button>
        </div>
      )}
      {entries?.length === 0 && !history.isLoading && (
        <p className="muted-text">{emptyMessage(hasFilters)}</p>
      )}
      {entries?.length > 0 && (
        <ul className="history-list">
          {entries.map((entry) => (
            <HistoryEntry
              key={entry.id}
              entry={entry}
              timezone={timezone}
              onEdited={onEdited}
              onDeleted={onDeleted}
              onMissing={onMissing}
            />
          ))}
        </ul>
      )}
    </section>
  );
}
