export default function Skeleton({ label, count = 1, className = '', groupClassName = '' }) {
  return (
    <div className={groupClassName} role="status">
      <span className="visually-hidden">{label}</span>
      {Array.from({ length: count }, (_, index) => (
        <div key={index} className={`skeleton ${className}`} aria-hidden="true" />
      ))}
    </div>
  );
}
