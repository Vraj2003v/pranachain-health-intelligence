// PranaPulse logo: custom image (public/logo.svg) plus a script wordmark.
export default function Logo({ size = 32, text = true }) {
  return (
    <span className="logo" aria-label="PranaPulse">
      <img src="/logo.svg" width={size} height={size} alt="" />
      {text && <span className="logotext">PranaPulse</span>}
    </span>
  );
}
