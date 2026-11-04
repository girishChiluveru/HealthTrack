export default function Brand() {
  return (
    <span className="brand">
      <svg className="brand__mark" viewBox="0 0 32 32" aria-hidden="true">
        <rect width="32" height="32" rx="10" fill="#5b3fe0" />
        <path
          d="M5 17h6l3-7 4 12 3-5h6"
          fill="none"
          stroke="#fff"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      HealthTrack
    </span>
  );
}
