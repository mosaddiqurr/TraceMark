import { useCallback, useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  ArrowRight,
  CheckCircle2,
  Download,
  FileCheck2,
  Info,
  LoaderCircle,
  LockKeyhole,
  ShieldCheck,
  Upload,
  X,
} from "lucide-react";
import {
  api,
  downloadImage,
  downloadReport,
  ensureWorkspace,
  loadImage,
  setCsrfToken,
} from "../api/client";
import type { Evidence, Protection, Workspace } from "../api/types";
import {
  FindCopies,
  LinkCheckPanel,
  TraceBackup,
} from "../components/Investigate";
import { TraceLens } from "../components/TraceLens";

const DEFAULT_LIMITS = {
  max_upload_bytes: 20 * 1024 * 1024,
  max_image_pixels: 4_000_000,
  max_image_dimension: 4096,
  output_ttl_seconds: 900,
  retention_seconds: 2592000,
};
const bytes = (value: number) =>
  value >= 1024 * 1024
    ? `${(value / 1024 / 1024).toFixed(1)} MB`
    : `${Math.ceil(value / 1024)} KB`;
const errorMessage = (error: unknown) =>
  error instanceof Error
    ? error.message
    : "The request could not be completed.";
const date = (value: string) =>
  new Date(value).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });

function usePreview(file: File | null) {
  const [url, setUrl] = useState<string>();
  useEffect(() => {
    if (!file) {
      setUrl(undefined);
      return;
    }
    const objectUrl = URL.createObjectURL(file);
    setUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [file]);
  return url;
}

function useLimits() {
  const [limits, setLimits] = useState<Workspace["limits"]>(DEFAULT_LIMITS);
  useEffect(() => {
    let active = true;
    void ensureWorkspace()
      .then((w) => {
        if (active) setLimits(w.limits);
      })
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, []);
  return limits;
}

function ErrorNotice({ message }: { message: string | null }) {
  return message ? (
    <div className="error-notice" role="alert">
      <Info size={18} />
      <span>{message}</span>
    </div>
  ) : null;
}

function UploadPicker({
  file,
  busy,
  limits,
  onFile,
  onError,
}: {
  file: File | null;
  busy: boolean;
  limits: Workspace["limits"];
  onFile: (file: File) => void;
  onError: (message: string) => void;
}) {
  const preview = usePreview(file);
  const [dimensions, setDimensions] = useState("");
  const choose = (chosen?: File) => {
    if (!chosen || busy) return;
    if (!chosen.size) {
      onError("This file is empty. Choose a JPEG, PNG or WebP image.");
      return;
    }
    if (chosen.size > limits.max_upload_bytes) {
      onError(
        `Choose an image smaller than ${bytes(limits.max_upload_bytes)}.`,
      );
      return;
    }
    if (!["image/jpeg", "image/png", "image/webp"].includes(chosen.type)) {
      onError("Choose a JPEG, PNG or WebP still image.");
      return;
    }
    setDimensions("");
    onFile(chosen);
  };
  return (
    <div
      className={`upload-zone ${file ? "has-file" : ""}`}
      onDragOver={(event) => event.preventDefault()}
      onDrop={(event) => {
        event.preventDefault();
        choose(event.dataTransfer.files[0]);
      }}
    >
      {file ? (
        <>
          <div className="image-preview">
            <img
              src={preview}
              alt="Selected image preview"
              onLoad={(event) => {
                const image = event.currentTarget;
                setDimensions(
                  `${image.naturalWidth} × ${image.naturalHeight} px`,
                );
              }}
              onError={() => setDimensions("Preview unavailable")}
            />
          </div>
          <div className="selected-file">
            <strong>{file.name}</strong>
            <span>
              {dimensions}
              {dimensions && " · "}
              {bytes(file.size)}
            </span>
          </div>
        </>
      ) : (
        <>
          <span className="upload-icon">
            <Upload size={24} />
          </span>
          <strong>Drop your image here</strong>
          <span>or choose a file from your device</span>
        </>
      )}
      <label className="button secondary file-button">
        {file ? "Choose another image" : "Choose image"}
        <input
          aria-label="Choose image"
          type="file"
          accept="image/jpeg,image/png,image/webp"
          disabled={busy}
          onChange={(event) => {
            choose(event.target.files?.[0]);
            event.target.value = "";
          }}
        />
      </label>
      {!file && (
        <small>
          JPEG, PNG or WebP · up to {bytes(limits.max_upload_bytes)}
        </small>
      )}
    </div>
  );
}

function PrivacyNote({ limits }: { limits: Workspace["limits"] }) {
  return (
    <p className="privacy-note">
      <LockKeyhole size={15} />
      <span>
        Uploaded pixels are discarded after processing. Private trace metadata
        is retained for up to {Math.round(limits.retention_seconds / 86400)}{" "}
        days in this browser workspace.{" "}
        <Link to="/about#privacy">Privacy details</Link>
      </span>
    </p>
  );
}

function PageHeading({
  step,
  title,
  children,
}: {
  step?: string;
  title: string;
  children: string;
}) {
  return (
    <div className="page-heading">
      <div>
        {step && <span className="eyebrow">{step}</span>}
        <h1>{title}</h1>
      </div>
      <p>{children}</p>
    </div>
  );
}

const workflowSteps = [
  {
    title: "Protect",
    text: "Choose a JPEG, PNG or WebP. A fresh identifier is embedded and checked before you get the file.",
    link: { to: "/protect", label: "Start protecting" },
  },
  {
    title: "Share",
    text: "Download the protected PNG and send it on. An optional private label, such as “Client review”, stays with you.",
    aside: "Your download",
  },
  {
    title: "Verify",
    text: "When a copy turns up, upload it. Blind extraction recovers the identifier without the original.",
    link: { to: "/verify", label: "Verify a copy" },
  },
  {
    title: "Trace",
    text: "See which protected copy it is, alongside exact hashes and visual similarity, then export a PDF or JSON report.",
    aside: "Evidence report",
  },
];

export function HomePage() {
  return (
    <div className="home">
      <section className="hero">
        <div className="hero-copy">
          <span className="eyebrow">Still-image provenance</span>
          <h1>
            Protect the image.
            <br />
            <em>Keep the trace.</em>
          </h1>
          <p className="hero-lead">
            Give every copy you share its own invisible identifier. If one
            leaks, upload it here to learn which copy it was, and what the
            evidence can and cannot prove.
          </p>
          <div className="hero-actions">
            <Link className="button primary" to="/protect">
              Protect an image
              <ArrowRight size={17} />
            </Link>
            <Link className="button secondary" to="/verify">
              Verify an image
            </Link>
          </div>
          <p className="hero-footnote">
            No account. Invisible watermark. Measured evidence.
          </p>
        </div>
        <TraceLens />
      </section>
      <section className="home-intro" aria-labelledby="how-heading">
        <div>
          <span className="eyebrow">How it works</span>
          <h2 id="how-heading">
            Four steps,
            <br />
            <em>one</em> trace.
          </h2>
        </div>
        <p>
          TraceMark hides a random identifier in the image itself, not in its
          metadata. Nothing about you or your recipient is written into the
          pixels; that link stays in your private browser workspace.
        </p>
      </section>
      <ol className="workflow" aria-label="How TraceMark works">
        {workflowSteps.map((step, index) => (
          <li key={step.title}>
            <span className="step-number" aria-hidden="true">
              {String(index + 1).padStart(2, "0")}
            </span>
            <h3>{step.title}</h3>
            <p>{step.text}</p>
            {step.link ? (
              <Link className="text-link" to={step.link.to}>
                {step.link.label}
                <ArrowRight size={15} />
              </Link>
            ) : (
              <span className="step-aside">{step.aside}</span>
            )}
          </li>
        ))}
      </ol>
      <section className="home-evidence" aria-labelledby="evidence-heading">
        <div>
          <span className="eyebrow">What a result means</span>
          <h2 id="evidence-heading">
            Three measurements, never blended into one score.
          </h2>
          <p>
            A result says verified only when an authenticated watermark is
            recovered and matches a trace in your workspace. Looking similar is
            not enough.
          </p>
          <dl className="measure-list">
            <div>
              <dt>Watermark</dt>
              <dd>128-bit identifier, error-corrected, HMAC-checked</dd>
            </div>
            <div>
              <dt>Exact hash</dt>
              <dd>SHA-256 against the protected copy or its source</dd>
            </div>
            <div>
              <dt>Visual similarity</dt>
              <dd>Perceptual hash and ORB/RANSAC feature matches</dd>
            </div>
          </dl>
        </div>
        <figure className="specimen" aria-label="Example report layout">
          <div className="specimen-head">
            <span>TRACEMARK / REPORT</span>
            <span>SPECIMEN</span>
          </div>
          <div className="specimen-verdict">Verified</div>
          <div className="specimen-sub">
            Watermark recovered and linked to this copy.
          </div>
          <dl>
            <div>
              <dt>identifier</dt>
              <dd>9b074ca7-9663-4ff9…</dd>
            </div>
            <div>
              <dt>reference</dt>
              <dd>Portfolio review</dd>
            </div>
            <div>
              <dt>watermark</dt>
              <dd>integrity verified</dd>
            </div>
            <div>
              <dt>sha-256</dt>
              <dd>protected copy matches</dd>
            </div>
            <div>
              <dt>phash distance</dt>
              <dd>4 / 64 bits</dd>
            </div>
          </dl>
          <span className="specimen-stamp">TRACE RESOLVED</span>
          <figcaption className="specimen-foot">
            Evidence of a protected copy. Not proof of legal ownership or of who
            shared the file.
          </figcaption>
        </figure>
      </section>
      <section className="sample-callout">
        <img
          src="/sample-thumb.webp"
          alt="Included geometric sample image"
          width="150"
          height="100"
          loading="lazy"
        />
        <div>
          <h2>Try it with the sample image</h2>
          <p>
            Protect it, download it, verify the copy. Same engine, nothing
            simulated.
          </p>
        </div>
        <Link to="/protect?sample=1" className="button secondary">
          Use sample image
          <ArrowRight size={16} />
        </Link>
      </section>
      <p className="home-note">
        <Info size={16} />A traceable identifier is evidence of a protected
        copy. It does not prove legal ownership or who shared it, and TraceMark
        does not search the web for copies.
      </p>
    </div>
  );
}

export function ProtectPage() {
  const limits = useLimits();
  const location = useLocation();
  const navigate = useNavigate();
  const sampleLoaded = useRef(false);
  const [file, setFile] = useState<File | null>(null);
  const [reference, setReference] = useState("");
  const [busy, setBusy] = useState(false);
  const [working, setWorking] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Protection | null>(null);
  const [protectedFile, setProtectedFile] = useState<File | null>(null);
  const preview = usePreview(protectedFile);
  useEffect(() => {
    if (!location.search.includes("sample=1") || sampleLoaded.current) return;
    sampleLoaded.current = true;
    void fetch("/sample.png")
      .then((r) => {
        if (!r.ok) throw new Error("The sample image is unavailable.");
        return r.blob();
      })
      .then((blob) =>
        setFile(
          new File([blob], "tracemark-sample.png", { type: "image/png" }),
        ),
      )
      .catch((e: unknown) => setError(errorMessage(e)));
  }, [location.search]);
  const protect = async (event: FormEvent) => {
    event.preventDefault();
    if (!file || busy) return;
    setBusy(true);
    setError(null);
    const body = new FormData();
    body.append("file", file);
    body.append("reference_label", reference);
    try {
      const protection = await api<Protection>("/protect", {
        method: "POST",
        body,
      });
      setResult(protection);
      const output = await loadImage(protection.download_url);
      setProtectedFile(
        new File([output.blob], output.filename, { type: output.mediaType }),
      );
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };
  const perform = async (action: "download" | "verify") => {
    if (!result) return;
    setWorking(action);
    setError(null);
    try {
      if (action === "download")
        await downloadImage(result.download_url, "protected");
      else {
        let copy = protectedFile;
        if (!copy) {
          const output = await loadImage(result.download_url);
          copy = new File([output.blob], output.filename, {
            type: output.mediaType,
          });
        }
        navigate("/verify", { state: { file: copy } });
      }
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setWorking("");
    }
  };
  return (
    <>
      <PageHeading step="01 — Protect" title="Protect an image">
        Embed an invisible identifier and download a traceable copy.
      </PageHeading>
      <div className="journey-grid">
        <section className="panel">
          {result ? (
            <>
              <div className="success-heading">
                <CheckCircle2 size={23} />
                <div>
                  <h2>Image protected</h2>
                  <p>The saved PNG passed watermark integrity verification.</p>
                </div>
              </div>
              {preview && (
                <div className="protected-preview">
                  <img src={preview} alt="Protected image preview" />
                </div>
              )}
              <dl className="metadata">
                <div>
                  <dt>Original filename</dt>
                  <dd>{result.file.filename}</dd>
                </div>
                <div>
                  <dt>Dimensions</dt>
                  <dd>
                    {result.file.width} × {result.file.height} px
                  </dd>
                </div>
                <div>
                  <dt>Reference / recipient</dt>
                  <dd>{result.reference_label || "None"}</dd>
                </div>
                <div>
                  <dt>Protection profile</dt>
                  <dd>{result.profile}</dd>
                </div>
              </dl>
              <div className="identifier">
                <span>Generated identifier</span>
                <code>{result.identifier}</code>
              </div>
              <div className="result-actions">
                <button
                  className="button primary"
                  disabled={Boolean(working) || busy}
                  onClick={() => void perform("download")}
                >
                  <Download size={17} />
                  {working === "download"
                    ? "Downloading…"
                    : "Download protected image"}
                </button>
                <button
                  className="button secondary"
                  disabled={Boolean(working) || busy}
                  onClick={() => void perform("verify")}
                >
                  <ShieldCheck size={17} />
                  Verify this image
                </button>
              </div>
              <p className="quiet">
                Download available until {date(result.download_expires_at)}.
                Save your copy now. The private trace expires{" "}
                {date(result.trace_expires_at)}.
              </p>
              <FindCopies />
              <button
                className="text-link"
                onClick={() => {
                  setResult(null);
                  setProtectedFile(null);
                  setFile(null);
                  setError(null);
                  setReference("");
                }}
              >
                Protect another image
                <ArrowRight size={15} />
              </button>
            </>
          ) : (
            <form onSubmit={(event) => void protect(event)}>
              <UploadPicker
                file={file}
                busy={busy}
                limits={limits}
                onFile={(chosen) => {
                  setFile(chosen);
                  setError(null);
                }}
                onError={setError}
              />
              <label className="field-label" htmlFor="reference">
                Recipient or reference <span>Optional</span>
              </label>
              <input
                className="text-input"
                id="reference"
                placeholder="e.g. Client review, October"
                maxLength={120}
                value={reference}
                disabled={busy}
                onChange={(event) => setReference(event.target.value)}
              />
              <p className="field-hint">
                Kept in your private trace record. Only a random identifier is
                embedded in the image.
              </p>
              <button
                className="button primary full-width"
                type="submit"
                disabled={!file || busy}
              >
                {busy ? (
                  <LoaderCircle className="spinner" size={18} />
                ) : (
                  <ShieldCheck size={18} />
                )}
                {busy ? "Protecting image…" : "Protect image"}
              </button>
            </form>
          )}
          <ErrorNotice message={error} />
        </section>
        <aside className="journey-aside">
          <h2>A trace you can check later</h2>
          <p>
            TraceMark places an authenticated, opaque identifier in the image
            pixels.
          </p>
          <ul className="check-list">
            <li>Invisible watermark by default</li>
            <li>A separate identifier for each copy</li>
            <li>Lossless protected PNG download</li>
          </ul>
          <div className="aside-note">
            <Info size={17} />
            <p>
              Choose a detailed image at least 256 px on each side. Resizing and
              everyday compression are tolerated; cropping is not.
            </p>
          </div>
          <Link className="text-link" to="/about">
            How protection works
            <ArrowRight size={15} />
          </Link>
        </aside>
      </div>
      <PrivacyNote limits={limits} />
    </>
  );
}

const findings: Record<string, string> = {
  valid_ownership_watermark:
    "Watermark recovered successfully and linked to your private trace record.",
  valid_distribution_watermark:
    "Watermark recovered successfully and linked to this reference-specific copy.",
  no_evidence: "No valid TraceMark identifier was recovered.",
  authenticated_unresolved:
    "An authentic watermark was recovered, but its private trace record is unavailable in this browser workspace.",
  invalid_authenticated_payload:
    "A recovered payload failed watermark authenticity verification.",
  exact_registered_hash:
    "The file matches a recorded source hash, but no valid watermark was recovered.",
  possible_visual_match:
    "A similar image exists in this private workspace. Similarity alone does not verify a watermark.",
};

function EvidenceResult({ evidence }: { evidence: Evidence }) {
  const [exporting, setExporting] = useState("");
  const [error, setError] = useState<string | null>(null);
  const exportReport = async (format: "pdf" | "json") => {
    setExporting(format);
    setError(null);
    try {
      await downloadReport(evidence.report.download_url, format);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setExporting("");
    }
  };
  return (
    <section className="panel evidence-panel" aria-label="Verification result">
      <div
        className={`verification-banner ${evidence.verified ? "verified" : "not-verified"}`}
        role="status"
      >
        {evidence.verified ? <CheckCircle2 size={29} /> : <Info size={29} />}
        <div>
          <h2>{evidence.verified ? "VERIFIED" : "NOT VERIFIED"}</h2>
          <p>
            {findings[evidence.classification] ??
              "Verification was inconclusive."}
          </p>
        </div>
      </div>
      {evidence.identifier && (
        <div className="identifier">
          <span>Recovered identifier</span>
          <code>{evidence.identifier}</code>
        </div>
      )}
      {evidence.reference_label && (
        <dl className="metadata">
          <div>
            <dt>Reference / recipient</dt>
            <dd>{evidence.reference_label}</dd>
          </div>
        </dl>
      )}
      <h3 className="section-label">Verification checks</h3>
      <ul className="evidence-checks">
        <li>
          <span>Watermark authenticity</span>
          <strong
            className={evidence.watermark.authentic ? "positive" : undefined}
          >
            {evidence.watermark.authentic
              ? "Integrity verified"
              : evidence.watermark.integrity_state === "invalid"
                ? "Integrity failed"
                : "No valid mark recovered"}
          </strong>
        </li>
        <li>
          <span>Exact file hash</span>
          <strong
            className={evidence.exact_hash.matched ? "positive" : undefined}
          >
            {evidence.exact_hash.matched
              ? evidence.exact_hash.kind === "protected_copy"
                ? "Protected copy matches"
                : "Source file matches"
              : "No exact match"}
          </strong>
        </li>
        <li>
          <span>Visual similarity</span>
          <strong className={evidence.visual?.similar ? "positive" : undefined}>
            {evidence.visual
              ? evidence.visual.similar
                ? "Similar private reference"
                : "No close match"
              : "No private reference"}
          </strong>
        </li>
      </ul>
      <p className="result-limitation">
        This result identifies evidence in a protected copy. It does not
        establish legal ownership, recipient intent, or survival of every
        transformation.
      </p>
      <details className="technical-evidence">
        <summary>View detailed evidence</summary>
        <dl className="metadata">
          <div>
            <dt>Submitted filename</dt>
            <dd>{evidence.file.filename}</dd>
          </div>
          {evidence.source_url && (
            <div>
              <dt>Found at</dt>
              <dd className="monospace">{evidence.source_url}</dd>
            </div>
          )}
          <div>
            <dt>Image details</dt>
            <dd>
              {evidence.file.width} × {evidence.file.height} px ·{" "}
              {bytes(evidence.file.size_bytes)} · {evidence.file.media_type}
            </dd>
          </div>
          <div>
            <dt>Source filename</dt>
            <dd>{evidence.source_filename || "No private source resolved"}</dd>
          </div>
          <div>
            <dt>SHA-256</dt>
            <dd className="monospace">{evidence.file.sha256}</dd>
          </div>
          <div>
            <dt>Verified at</dt>
            <dd>{date(evidence.created_at)}</dd>
          </div>
          <div>
            <dt>Payload type</dt>
            <dd>{evidence.watermark.type || "Not recovered"}</dd>
          </div>
          <div>
            <dt>Watermark algorithm</dt>
            <dd>
              {evidence.watermark.algorithm}{" "}
              {evidence.watermark.algorithm_version &&
                `v${evidence.watermark.algorithm_version}`}
            </dd>
          </div>
          <div>
            <dt>Recovered repetitions</dt>
            <dd>{evidence.watermark.repetitions_found}</dd>
          </div>
          <div>
            <dt>Corrected ECC symbols</dt>
            <dd>{evidence.watermark.corrected_symbols ?? "Unavailable"}</dd>
          </div>
          <div>
            <dt>C2PA provenance</dt>
            <dd>{evidence.provenance.state.replaceAll("_", " ")}</dd>
          </div>
          {evidence.visual && (
            <>
              <div>
                <dt>Perceptual hash distance</dt>
                <dd>{evidence.visual.phash_distance} / 64 bits</dd>
              </div>
              <div>
                <dt>ORB / RANSAC evidence</dt>
                <dd>
                  {evidence.visual.orb_available
                    ? `${evidence.visual.orb_match_count ?? 0} matches · ${evidence.visual.ransac_inliers ?? 0} inliers · ${evidence.visual.homography_valid ? "consistent geometry" : "geometry unconfirmed"}`
                    : "Unavailable"}
                </dd>
              </div>
            </>
          )}
        </dl>
        <ul className="limitations-list">
          {evidence.limitations.map((limit) => (
            <li key={limit}>{limit}</li>
          ))}
        </ul>
      </details>
      <div className="report-actions">
        <div>
          <FileCheck2 size={18} />
          <span>Verification report</span>
        </div>
        <div>
          <button
            className="button secondary small"
            disabled={Boolean(exporting)}
            onClick={() => void exportReport("pdf")}
          >
            <Download size={15} />
            {exporting === "pdf" ? "Exporting…" : "Export PDF"}
          </button>
          <button
            className="button secondary small"
            disabled={Boolean(exporting)}
            onClick={() => void exportReport("json")}
          >
            <Download size={15} />
            {exporting === "json" ? "Exporting…" : "Export JSON"}
          </button>
        </div>
      </div>
      <ErrorNotice message={error} />
    </section>
  );
}

export function VerifyPage() {
  const limits = useLimits();
  const location = useLocation();
  const initialFileUsed = useRef(false);
  const requestId = useRef(0);
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [evidence, setEvidence] = useState<Evidence | null>(null);
  const run = useCallback(async (chosen: File) => {
    const current = ++requestId.current;
    setFile(chosen);
    setEvidence(null);
    setError(null);
    setBusy(true);
    const body = new FormData();
    body.append("file", chosen);
    try {
      const result = await api<Evidence>("/verification", {
        method: "POST",
        body,
      });
      if (current === requestId.current) setEvidence(result);
    } catch (e) {
      if (current === requestId.current) setError(errorMessage(e));
    } finally {
      if (current === requestId.current) setBusy(false);
    }
  }, []);
  useEffect(() => {
    const chosen = (location.state as { file?: File } | null)?.file;
    if (chosen instanceof File && !initialFileUsed.current) {
      initialFileUsed.current = true;
      void run(chosen);
    }
  }, [location.state, run]);
  return (
    <>
      <PageHeading step="02 — Verify" title="Verify an image">
        Recover its identifier and review the evidence behind the result.
      </PageHeading>
      <div className="journey-grid">
        <div className="verify-main">
          <section className="panel">
            <UploadPicker
              file={file}
              busy={busy}
              limits={limits}
              onFile={(chosen) => void run(chosen)}
              onError={(message) => {
                setEvidence(null);
                setFile(null);
                setError(message);
              }}
            />
            {busy && (
              <div className="processing-status" role="status">
                <LoaderCircle className="spinner" size={18} />
                <span>Checking watermark, hashes and private references…</span>
              </div>
            )}
            <ErrorNotice message={error} />
            {error && file && (
              <button
                className="button secondary retry-button"
                disabled={busy}
                onClick={() => void run(file)}
              >
                Retry verification
              </button>
            )}
          </section>
          <LinkCheckPanel
            disabled={busy}
            onStart={() => {
              requestId.current += 1;
              setFile(null);
              setEvidence(null);
              setError(null);
            }}
            onEvidence={setEvidence}
          />
          {evidence && <EvidenceResult evidence={evidence} />}
        </div>
        <aside className="journey-aside">
          <h2>Evidence behind every result</h2>
          <p>Checks run automatically when you select an image.</p>
          <ol className="check-sequence">
            <li>
              <span>1</span>
              <div>
                <strong>Recover the watermark</strong>
                <p>Blind extraction needs no original image.</p>
              </div>
            </li>
            <li>
              <span>2</span>
              <div>
                <strong>Verify authenticity</strong>
                <p>Integrity must pass before an identifier is accepted.</p>
              </div>
            </li>
            <li>
              <span>3</span>
              <div>
                <strong>Resolve the trace</strong>
                <p>
                  Compare hashes and visual evidence in your private workspace.
                </p>
              </div>
            </li>
          </ol>
          <div className="aside-note">
            <Info size={17} />
            <p>
              Use the same browser that protected the image to recover its
              private reference label.
            </p>
          </div>
          <Link to="/protect" className="text-link">
            Protect an image first
            <ArrowRight size={15} />
          </Link>
          <FindCopies />
        </aside>
      </div>
      <PrivacyNote limits={limits} />
    </>
  );
}

export function AboutPage() {
  const [confirm, setConfirm] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [cleared, setCleared] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const clear = async () => {
    setClearing(true);
    setError(null);
    try {
      await ensureWorkspace();
      await api("/workspace", { method: "DELETE" });
      setCsrfToken(null);
      setCleared(true);
      setConfirm(false);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setClearing(false);
    }
  };
  return (
    <div className="about-page">
      <PageHeading title="About TraceMark">
        A focused tool for still-image watermarking and provenance evidence.
      </PageHeading>
      <section>
        <h2>Protect. Share. Verify. Trace.</h2>
        <p>
          Upload a JPEG, PNG or WebP image, embed an invisible identifier, and
          download the protected PNG. Later, upload a copy to recover the
          watermark and review its trace, hash and visual evidence.
        </p>
      </section>
      <section>
        <h2>How the protection works</h2>
        <p>
          A classical wavelet and cosine transform watermark places a random
          128-bit identifier in the image. It is embedded on a fixed internal
          grid, so a resized copy can still be read. Error correction helps
          recovery; an HMAC verifies authenticity. Recipient and reference
          labels stay in the private registry.
        </p>
        <p>
          Verification also checks exact SHA-256 hashes, perceptual fingerprints
          and ORB/RANSAC feature matches. These measurements remain separate. A
          visual match alone cannot produce a verified watermark result.
        </p>
      </section>
      <section>
        <h2>What a result can tell you</h2>
        <p>
          A verified trace links the recovered identifier to a protected copy in
          your private browser workspace. It does not prove authorship, legal
          ownership, who shared the file, or a recipient's intent.
        </p>
        <p>
          Resizing and everyday JPEG compression are tolerated within the tested
          bounds. Cropping, repainting, heavy compression and deliberate removal
          can still break recovery, and social platforms may apply all of them.
          The project claims no universal robustness or aggregate confidence
          score.
        </p>
      </section>
      <section id="privacy">
        <h2>Privacy and security</h2>
        <p>
          Uploaded images are processed in bounded, timed child processes and
          discarded. Protected downloads and reports stay in private memory for
          15 minutes by default. Optional provenance inspection uses a temporary
          file that is deleted after processing, including on timeout.
        </p>
        <p>
          Only identifiers, hashes, compact visual descriptors, private labels
          and timestamps persist. They are isolated by an opaque HttpOnly
          browser cookie and expire after 30 days by default. Losing the cookie,
          using another browser, or clearing traces makes those private mappings
          unavailable. A server restart ends temporary download links.
        </p>
        <p>
          Images are never served from public storage. Upload limits, exact CORS
          origins, CSRF checks, rate limits and private lookups protect the core
          workflow. TraceMark never crawls the web: a link check fetches only
          the link you submit and up to eight images on that page, from public
          addresses only.
        </p>
        <TraceBackup />
        <div className="clear-traces">
          {cleared ? (
            <p className="clear-success" role="status">
              <CheckCircle2 size={17} />
              This browser's private traces and temporary artifacts were
              cleared.
            </p>
          ) : confirm ? (
            <>
              <p>
                Clear all private traces in this browser? Existing copies will
                lose their reference mapping here.
              </p>
              <div className="inline-actions">
                <button
                  className="button danger small"
                  disabled={clearing}
                  onClick={() => void clear()}
                >
                  {clearing ? "Clearing…" : "Clear private traces"}
                </button>
                <button
                  className="button secondary small"
                  disabled={clearing}
                  onClick={() => setConfirm(false)}
                >
                  <X size={15} />
                  Cancel
                </button>
              </div>
            </>
          ) : (
            <button
              className="button secondary small"
              onClick={() => setConfirm(true)}
            >
              Clear this browser's traces
            </button>
          )}
          <ErrorNotice message={error} />
        </div>
      </section>
      <Link className="button primary" to="/protect">
        Protect an image
        <ArrowRight size={17} />
      </Link>
    </div>
  );
}

export function NotFoundPage() {
  return (
    <div className="not-found">
      <PageHeading title="Page not found">
        Choose Protect or Verify to continue your image workflow.
      </PageHeading>
      <Link className="button primary" to="/">
        Go to Home
        <ArrowRight size={17} />
      </Link>
    </div>
  );
}
