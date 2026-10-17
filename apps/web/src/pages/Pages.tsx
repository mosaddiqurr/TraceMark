import { useCallback, useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  ArrowRight,
  Check,
  CheckCircle2,
  ChevronRight,
  Download,
  FileCheck2,
  Fingerprint,
  ImagePlus,
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
      {step && <span className="eyebrow">{step}</span>}
      <h1>{title}</h1>
      <p>{children}</p>
    </div>
  );
}

export function HomePage() {
  return (
    <div className="home">
      <section className="hero">
        <span className="eyebrow">
          <span className="gold-dot" /> Still-image provenance
        </span>
        <h1>
          Protect the image.
          <br />
          Keep the trace.
        </h1>
        <p>
          Protect images with traceable identifiers and verify their provenance
          later.
        </p>
        <div className="hero-actions">
          <Link className="button primary" to="/protect">
            <ImagePlus size={18} />
            Protect an image
            <ArrowRight size={17} />
          </Link>
          <Link className="button secondary" to="/verify">
            <ShieldCheck size={18} />
            Verify an image
          </Link>
        </div>
        <p className="hero-footnote">
          No account required. Invisible watermark. Verifiable evidence.
        </p>
      </section>
      <ol className="workflow" aria-label="How TraceMark works">
        {[
          {
            icon: ImagePlus,
            title: "Protect",
            text: "Embed a private identifier",
          },
          {
            icon: Upload,
            title: "Share",
            text: "Download your protected copy",
          },
          { icon: ShieldCheck, title: "Verify", text: "Check an image later" },
          { icon: Fingerprint, title: "Trace", text: "Review the evidence" },
        ].map(({ icon: Icon, title, text }, index) => (
          <li key={title}>
            <div>
              <span className="step-icon">
                <Icon size={20} />
              </span>
              <div>
                <strong>{title}</strong>
                <small>{text}</small>
              </div>
            </div>
            {index < 3 && (
              <ChevronRight
                className="workflow-arrow"
                size={17}
                aria-hidden="true"
              />
            )}
          </li>
        ))}
      </ol>
      <section className="sample-callout">
        <img
          src="/sample.png"
          alt="Included geometric sample image"
          width="160"
          height="112"
        />
        <div>
          <span className="eyebrow">A real working demo</span>
          <h2>Try it with a sample image</h2>
          <p>
            Protect the sample, download it, then verify the copy. Every check
            uses the real engine.
          </p>
          <Link to="/protect?sample=1" className="text-link">
            Use sample image
            <ArrowRight size={16} />
          </Link>
        </div>
      </section>
      <p className="home-note">
        <Info size={16} />A traceable identifier is evidence of a protected
        copy. It does not prove legal ownership or who shared it.
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
      <PageHeading step="01 / Protect" title="Protect an image">
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
          <span className="aside-icon">
            <Fingerprint size={24} />
          </span>
          <h2>A trace you can check later</h2>
          <p>
            TraceMark places an authenticated, opaque identifier in the image
            pixels.
          </p>
          <ul className="check-list">
            <li>
              <Check size={16} />
              Invisible watermark by default
            </li>
            <li>
              <Check size={16} />A separate identifier for each copy
            </li>
            <li>
              <Check size={16} />
              Lossless protected PNG download
            </li>
          </ul>
          <div className="aside-note">
            <Info size={17} />
            <p>
              Choose a detailed image at least 432 × 432 px. Keep its dimensions
              intact for the most reliable recovery.
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
          <strong>
            {evidence.watermark.authentic
              ? "Integrity verified"
              : evidence.watermark.integrity_state === "invalid"
                ? "Integrity failed"
                : "No valid mark recovered"}
          </strong>
        </li>
        <li>
          <span>Exact file hash</span>
          <strong>
            {evidence.exact_hash.matched
              ? evidence.exact_hash.kind === "protected_copy"
                ? "Protected copy matches"
                : "Source file matches"
              : "No exact match"}
          </strong>
        </li>
        <li>
          <span>Visual similarity</span>
          <strong>
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
      <PageHeading step="02 / Verify" title="Verify an image">
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
          {evidence && <EvidenceResult evidence={evidence} />}
        </div>
        <aside className="journey-aside">
          <span className="aside-icon">
            <ShieldCheck size={24} />
          </span>
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
          128-bit identifier in the image. Error correction helps recovery; an
          HMAC verifies authenticity. Recipient and reference labels stay in the
          private registry.
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
          Resizing, cropping, repainting, heavy compression and deliberate
          removal can break recovery. Keep the protected PNG and its dimensions
          intact. The project claims no universal robustness or aggregate
          confidence score.
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
          workflow. This application does not crawl or scan websites.
        </p>
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
