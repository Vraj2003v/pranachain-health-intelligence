// PranaPulse mark: a heartbeat line inside a rounded glass tile, plus a two-weight wordmark.
export default function Logo({ size = 30, text = true }) {
  return (
    <span className="logo" aria-label="PranaPulse">
      <svg width={size} height={size} viewBox="0 0 40 40" aria-hidden="true">
        <defs>
          <linearGradient id="lgA" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#35c6d8" /><stop offset="1" stopColor="#3b6fe0" />
          </linearGradient>
        </defs>
        <rect x="1" y="1" width="38" height="38" rx="11" fill="url(#lgA)" />
        <path d="M6 21h7l3-8 5 16 4-11 2 3h7" fill="none" stroke="#fff" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      {text && <span className="logotext"><span>Prana</span><b>Pulse</b></span>}
    </span>
  );
}
