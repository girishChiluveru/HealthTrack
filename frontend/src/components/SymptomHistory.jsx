import HistoryEntry from './HistoryEntry.jsx';
import LoadError from './LoadError.jsx';
import Pagination from './Pagination.jsx';
import Skeleton from './Skeleton.jsx';

export default function SymptomHistory({
  history,
  hasFilters,
  noEntriesText,
  headingRef,
  headerAction,
  entryActions,
  onPageChange,
  onRetry,
}) {
  const data = history.data;
  const entries = data?.entries;

  return (
    <section className="card" aria-labelledby="history-heading" aria-busy={history.isLoading}>
      <div className="card__header">
        <h2 id="history-heading" ref={headingRef} tabIndex={-1}>
          Symptom history
        </h2>
        {headerAction}
      </div>
      {history.isLoading && !entries && (
        <Skeleton label="Loading history…" count={4} className="skeleton--row" />
      )}
      {history.error && (
        <LoadError message="We could not load the history." onRetry={onRetry} />
      )}
      {entries?.length === 0 && !history.isLoading && (
        <p className="muted-text">
          {hasFilters ? 'No entries match these filters.' : noEntriesText}
        </p>
      )}
      {entries?.length > 0 && (
        <>
          <ul className={history.isLoading ? 'history-list history-list--loading' : 'history-list'}>
            {entries.map((entry) => (
              <HistoryEntry key={entry.id} entry={entry} actions={entryActions} />
            ))}
          </ul>
          {data.total > data.page_size && (
            <Pagination
              page={data.page}
              pageSize={data.page_size}
              total={data.total}
              isLoading={history.isLoading}
              onChange={onPageChange}
            />
          )}
        </>
      )}
    </section>
  );
}
