export default function LoadError({ message, onRetry }) {
  return (
    <div className="alert alert--error" role="alert">
      <p>{message}</p>
      <button type="button" className="link-button" onClick={onRetry}>
        Try again
      </button>
    </div>
  );
}
