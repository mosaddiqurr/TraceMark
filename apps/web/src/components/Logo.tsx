import { Link } from "react-router-dom";

export function Logo() {
  return (
    <Link className="logo" to="/" aria-label="TraceMark home">
      <img
        src="/brand/tracemark-logo.png"
        alt="TraceMark"
        width="190"
        height="48"
      />
    </Link>
  );
}
