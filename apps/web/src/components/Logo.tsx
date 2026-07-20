import { Link } from "react-router-dom";

export function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <Link className="logo" to="/" aria-label="TraceMark home">
      <span className="logo-mark" aria-hidden="true"><i /><i /><i /></span>
      {!compact && <span>Trace<span>Mark</span></span>}
    </Link>
  );
}
