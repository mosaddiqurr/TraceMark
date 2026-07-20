import { AlertTriangle, FileSearch, LoaderCircle, RefreshCw } from "lucide-react";
import type { ReactNode } from "react";
import { ApiError } from "../api/client";

export function FullPageLoader({ label = "Loading" }: { label?: string }) {
  return <main className="full-state" aria-live="polite"><LoaderCircle className="spin" /><p>{label}…</p></main>;
}

export function LoadingState({ label = "Loading records" }: { label?: string }) {
  return <div className="state-card" aria-live="polite"><LoaderCircle className="spin" /><div><strong>{label}</strong><p>Securely retrieving the latest data.</p></div></div>;
}

export function EmptyState({ title, detail, action }: { title: string; detail: string; action?: ReactNode }) {
  return <div className="state-card empty-state"><FileSearch /><div><strong>{title}</strong><p>{detail}</p>{action}</div></div>;
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const detail = error instanceof ApiError ? error.message : "The service did not return a usable response.";
  const correlation = error instanceof ApiError ? error.body.correlation_id : undefined;
  return <div className="state-card error-state" role="alert"><AlertTriangle /><div><strong>Couldn’t load this view</strong><p>{detail}</p>{correlation && <small>Reference: {correlation}</small>}{onRetry && <button className="button subtle" onClick={onRetry}><RefreshCw size={15} /> Try again</button>}</div></div>;
}

export function StatusBadge({ value }: { value: string }) {
  const normalized = value.toLowerCase().replaceAll("_", "-");
  return <span className={`badge badge-${normalized}`}>{value.replaceAll("_", " ")}</span>;
}
