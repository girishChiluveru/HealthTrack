import HistoryEntry from './HistoryEntry.jsx';

export default function SymptomHistory({
  history,
  hasFilters,
  noEntriesText,
  notice,
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
      <div role="status">
        {notice && <p className="alert alert--success">{notice}</p>}
        {history.isLoading && <p className="muted-text">Loading history…</p>}
      </div>
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
