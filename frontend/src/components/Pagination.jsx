import { ChevronLeft, ChevronRight } from 'lucide-react';

export default function Pagination({ page, pageSize, total, isLoading, onChange }) {
  const pageCount = Math.max(Math.ceil(total / pageSize), 1);
  const first = (page - 1) * pageSize + 1;
  const last = Math.min(page * pageSize, total);

  return (
    <nav className="pagination" aria-label="History pages">
      <p className="pagination__status">
        Entries {first}–{last} of {total}
      </p>
      <div className="pagination__controls">
        <button
          type="button"
          className="button button--secondary"
          disabled={page <= 1 || isLoading}
          onClick={() => onChange(page - 1)}
        >
          <ChevronLeft size={16} aria-hidden="true" />
          Previous
        </button>
        <span className="pagination__page" aria-current="page">
          Page {page} of {pageCount}
        </span>
        <button
          type="button"
          className="button button--secondary"
          disabled={page >= pageCount || isLoading}
          onClick={() => onChange(page + 1)}
        >
          Next
          <ChevronRight size={16} aria-hidden="true" />
        </button>
      </div>
    </nav>
  );
}
