import { useRef, useState } from "react";
import type { FormEvent } from "react";
import { ExternalLink, LoaderCircle } from "lucide-react";
import { api, downloadTraceExport, jsonBody } from "../api/client";
import type { Evidence, LinkCheck, TraceImport } from "../api/types";

const errorText = (error: unknown) =>
  error instanceof Error
    ? error.message
    : "The request could not be completed.";

const outcome: Record<string, string> = {
  valid_distribution_watermark: "Verified",
  valid_ownership_watermark: "Verified",
  authenticated_unresolved: "Authentic mark, no private record here",
  invalid_authenticated_payload: "Mark failed authenticity",
  exact_registered_hash: "Matches a recorded source file",
  possible_visual_match: "Looks similar, not verified",
  no_evidence: "No TraceMark identifier",
};

const searchEngines = [
  { name: "Google Lens", href: "https://lens.google.com/" },
  { name: "TinEye", href: "https://tineye.com/" },
  { name: "Bing Visual Search", href: "https://www.bing.com/visualsearch" },
];

export function FindCopies() {
  return (
    <section className="find-copies" aria-labelledby="find-copies-heading">
      <h3 id="find-copies-heading">Find copies online</h3>
      <p>
        TraceMark does not crawl the web. Upload your protected copy to a
        reverse image search, then paste any page or image link it finds into
        Check a link on the Verify page.
      </p>
      <ul>
        {searchEngines.map((engine) => (
          <li key={engine.name}>
            <a href={engine.href} target="_blank" rel="noopener noreferrer">
              {engine.name}
              <ExternalLink size={13} aria-hidden="true" />
            </a>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function LinkCheckPanel({
  disabled,
  onStart,
  onEvidence,
}: {
  disabled: boolean;
  onStart: () => void;
  onEvidence: (evidence: Evidence | null) => void;
}) {
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<LinkCheck | null>(null);
  const check = async (event: FormEvent) => {
    event.preventDefault();
    const value = url.trim();
    if (!/^https?:\/\/\S+$/i.test(value)) {
      setError("Enter a full http:// or https:// link.");
      return;
    }
    onStart();
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const checked = await api<LinkCheck>(
        "/verification/link",
        jsonBody({ url: value }),
      );
      setResult(checked);
      onEvidence(checked.evidence);
    } catch (e) {
      setError(errorText(e));
      onEvidence(null);
    } finally {
      setBusy(false);
    }
  };
  return (
    <section className="panel link-check" aria-labelledby="link-check-heading">
      <h2 id="link-check-heading">Check a link</h2>
      <p className="field-hint">
        Paste a direct image link, or a page where you found the image. Up to
        eight images on a page are checked. Only public addresses are fetched.
      </p>
      <form className="link-form" onSubmit={(event) => void check(event)}>
        <label className="visually-hidden" htmlFor="link-url">
          Image or page link
        </label>
        <input
          id="link-url"
          className="text-input"
          type="url"
          inputMode="url"
          placeholder="https://example.com/post/123"
          maxLength={2048}
          value={url}
          disabled={busy || disabled}
          onChange={(event) => setUrl(event.target.value)}
        />
        <button
          className="button secondary"
          type="submit"
          disabled={busy || disabled || !url.trim()}
        >
          {busy && <LoaderCircle className="spinner" size={16} />}
          {busy ? "Checking…" : "Check link"}
        </button>
      </form>
      {error && (
        <div className="error-notice" role="alert">
          <span>{error}</span>
        </div>
      )}
      {result && (
        <div className="link-results" role="status">
          <p className="link-summary">
            {result.kind === "image"
              ? "Checked 1 image."
              : `Checked ${result.images.length} image${result.images.length === 1 ? "" : "s"} on the page${result.truncated ? " (more were skipped)" : ""}.`}
          </p>
          <ul>
            {result.images.map((image) => (
              <li key={image.url}>
                <span className="link-url" title={image.url}>
                  {image.url}
                </span>
                <strong
                  className={
                    image.status === "verified" ? "positive" : undefined
                  }
                >
                  {image.status === "error"
                    ? `Not checked: ${image.message ?? "unavailable"}`
                    : `${outcome[image.classification ?? ""] ?? "Checked"}${image.reference_label ? ` · ${image.reference_label}` : ""}`}
                </strong>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

export function TraceBackup() {
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const run = async (action: "export" | "import", file?: File) => {
    setBusy(action);
    setError(null);
    setMessage(null);
    try {
      if (action === "export") {
        await downloadTraceExport();
        setMessage(
          "Trace records saved. Keep the file private: it can resolve your marks.",
        );
      } else if (file) {
        const body = new FormData();
        body.append("file", file);
        const result = await api<TraceImport>("/workspace/import", {
          method: "POST",
          body,
        });
        setMessage(
          `${result.imported} record${result.imported === 1 ? "" : "s"} restored to this browser${result.skipped ? `; ${result.skipped} already here` : ""}.`,
        );
      }
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy("");
    }
  };
  return (
    <div className="trace-backup">
      <h3>Back up your trace records</h3>
      <p>
        Private labels live in this browser for up to the retention period. Save
        a signed copy to keep them longer or move them to another browser.
        Restoring moves the records to the browser you restore them in.
      </p>
      <div className="inline-actions">
        <button
          className="button secondary small"
          disabled={Boolean(busy)}
          onClick={() => void run("export")}
        >
          {busy === "export" ? "Saving…" : "Save trace records"}
        </button>
        <label className="button secondary small file-button">
          {busy === "import" ? "Restoring…" : "Restore from file"}
          <input
            ref={input}
            aria-label="Restore trace records from file"
            type="file"
            accept="application/json,.json"
            disabled={Boolean(busy)}
            onChange={(event) => {
              const chosen = event.target.files?.[0];
              event.target.value = "";
              if (chosen) void run("import", chosen);
            }}
          />
        </label>
      </div>
      {message && (
        <p className="clear-success" role="status">
          {message}
        </p>
      )}
      {error && (
        <div className="error-notice" role="alert">
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}
