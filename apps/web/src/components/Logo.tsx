import { Link } from "react-router-dom";

export function Logo() {
  return (
    <Link className="logo" to="/" aria-label="TraceMark home">
      <svg viewBox="0 0 32 32" fill="none" aria-hidden="true">
        <path
          d="M5 26h5c3.5 0 4.2-3.6 1.6-5.2C9 19.2 9.8 14 14 14h5c3.6 0 5.4-2.6 5.4-7"
          stroke="#ecebe6"
          strokeWidth="2"
          strokeLinecap="round"
        />
        <circle
          cx="5"
          cy="26"
          r="2.6"
          fill="#070808"
          stroke="#ecebe6"
          strokeWidth="1.8"
        />
        <circle
          cx="15"
          cy="14"
          r="2.4"
          fill="#070808"
          stroke="#ecebe6"
          strokeWidth="1.8"
        />
        <circle cx="24.5" cy="6.2" r="2.8" fill="#5fe0d0" />
      </svg>
      <span>TraceMark</span>
    </Link>
  );
}
